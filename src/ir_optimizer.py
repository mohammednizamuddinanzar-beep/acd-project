"""
DSL Compiler - IR Optimization Pass
Operates on Three-Address Code (TAC) produced by ICG.

Passes (executed in order):
  1. Constant Folding
  2. Constant Condition Simplification
  3. Dead Code / Dead Action Elimination
  4. Duplicate Extraction / Copy Elimination

Pipeline position:  ICG -> [IR Optimizer] -> CodeGen

Usage:
    optimizer = IROptimizer(tac)
    opt_tac, report = optimizer.optimize()
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from icg import TACInstr


# ---------------------------------------------------------------------------
# Optimization report
# ---------------------------------------------------------------------------
@dataclass
class OptimizationReport:
    """Collects per-pass statistics and log messages."""
    constant_folds: int = 0
    condition_simplifies: int = 0
    dead_code_removed: int = 0
    duplicates_removed: int = 0
    log: List[str] = field(default_factory=list)

    @property
    def total_eliminated(self) -> int:
        return self.dead_code_removed + self.duplicates_removed

    def summary(self) -> str:
        W = 60
        lines = [
            "=" * W,
            "  IR OPTIMIZATION PASS REPORT",
            "=" * W,
            f"  Constant folds         : {self.constant_folds}",
            f"  Condition simplifies   : {self.condition_simplifies}",
            f"  Dead instr removed     : {self.dead_code_removed}",
            f"  Duplicate eliminations : {self.duplicates_removed}",
            f"  Total removed          : {self.total_eliminated}",
            "",
        ]
        if self.log:
            lines.append("  Transformation log:")
            for entry in self.log:
                lines.append(f"    {entry}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
ARITH_OPS = {"+", "-", "*", "/"}
REL_OPS   = {"<", ">", "<=", ">=", "==", "!="}


def _is_int(s: Optional[str]) -> bool:
    if s is None:
        return False
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


def _vi(s: str) -> int:
    return int(s)


def _bi(v: bool) -> str:
    return "1" if v else "0"


# ---------------------------------------------------------------------------
# Main optimizer class
# ---------------------------------------------------------------------------
class IROptimizer:
    """
    Four-pass optimizer over the TAC list.
    Each pass returns a new list; the original is never mutated.
    """

    def __init__(self, tac: List[TACInstr]):
        self._original: List[TACInstr] = tac
        self.report = OptimizationReport()

    def optimize(self) -> Tuple[List[TACInstr], OptimizationReport]:
        code = deepcopy(self._original)
        code = self._pass1_constant_folding(code)
        code = self._pass2_constant_conditions(code)
        code = self._pass3_dead_code(code)
        code = self._pass4_duplicates(code)
        return code, self.report

    # =======================================================================
    # PASS 1 - Constant Folding
    # =======================================================================
    def _pass1_constant_folding(self, code: List[TACInstr]) -> List[TACInstr]:
        """
        Evaluate instructions where both operands are integer literals.
        Propagates constant copies so downstream instructions also benefit.

        Examples:
          t0 = 3 + 5        ->  t0 = 8
          t1 = 10 > 2       ->  t1 = 1
          t2 = NEG 4        ->  t2 = -4
          t3 = NOT 0        ->  t3 = 1
        """
        const_map: Dict[str, str] = {}   # name -> known integer string
        out: List[TACInstr] = []

        for instr in code:
            # Substitute any known constants into operands
            a1 = const_map.get(instr.arg1, instr.arg1) if instr.arg1 else instr.arg1
            a2 = const_map.get(instr.arg2, instr.arg2) if instr.arg2 else instr.arg2

            # --- arithmetic on two constants ---
            if instr.op in ARITH_OPS and _is_int(a1) and _is_int(a2):
                v1, v2 = _vi(a1), _vi(a2)
                res = None
                if   instr.op == "+": res = str(v1 + v2)
                elif instr.op == "-": res = str(v1 - v2)
                elif instr.op == "*": res = str(v1 * v2)
                elif instr.op == "/" and v2 != 0: res = str(v1 // v2)
                if res is not None:
                    self.report.constant_folds += 1
                    self.report.log.append(
                        f"[CF] {instr.result} = {a1} {instr.op} {a2}  =>  {instr.result} = {res}"
                    )
                    const_map[instr.result] = res
                    out.append(TACInstr(op="COPY", result=instr.result, arg1=res))
                    continue

            # --- relational on two constants ---
            if instr.op in REL_OPS and _is_int(a1) and _is_int(a2):
                v1, v2 = _vi(a1), _vi(a2)
                if   instr.op == "<":  res = _bi(v1 <  v2)
                elif instr.op == ">":  res = _bi(v1 >  v2)
                elif instr.op == "<=": res = _bi(v1 <= v2)
                elif instr.op == ">=": res = _bi(v1 >= v2)
                elif instr.op == "==": res = _bi(v1 == v2)
                elif instr.op == "!=": res = _bi(v1 != v2)
                else: res = None
                if res is not None:
                    self.report.constant_folds += 1
                    self.report.log.append(
                        f"[CF] {instr.result} = {a1} {instr.op} {a2}  =>  {instr.result} = {res}"
                    )
                    const_map[instr.result] = res
                    out.append(TACInstr(op="COPY", result=instr.result, arg1=res))
                    continue

            # --- unary NEG on constant ---
            if instr.op == "NEG" and _is_int(a1):
                res = str(-_vi(a1))
                self.report.constant_folds += 1
                self.report.log.append(
                    f"[CF] {instr.result} = NEG {a1}  =>  {instr.result} = {res}"
                )
                const_map[instr.result] = res
                out.append(TACInstr(op="COPY", result=instr.result, arg1=res))
                continue

            # --- unary NOT on constant ---
            if instr.op == "NOT" and _is_int(a1):
                res = _bi(_vi(a1) == 0)
                self.report.constant_folds += 1
                self.report.log.append(
                    f"[CF] {instr.result} = NOT {a1}  =>  {instr.result} = {res}"
                )
                const_map[instr.result] = res
                out.append(TACInstr(op="COPY", result=instr.result, arg1=res))
                continue

            # --- track constant propagation ---
            if instr.op == "COPY" and instr.result and _is_int(a1):
                const_map[instr.result] = a1
            elif (instr.result
                  and instr.op not in ("LABEL", "GOTO", "IF_FALSE", "IF_TRUE",
                                       "WRITE", "WRITE_STR", "READ", "PARAM",
                                       "CALL", "HALT", "RETURN")):
                if instr.result in const_map:
                    del const_map[instr.result]

            out.append(TACInstr(op=instr.op, result=instr.result, arg1=a1, arg2=a2))
        return out

    # =======================================================================
    # PASS 2 - Constant Condition Simplification
    # =======================================================================
    def _pass2_constant_conditions(self, code: List[TACInstr]) -> List[TACInstr]:
        """
        Replace IF_FALSE/IF_TRUE with constant guards:

          IF_FALSE 0 GOTO L  ->  GOTO L       (0=false, always branches)
          IF_FALSE 1 GOTO L  ->  (removed)    (1=true, never branches)
          IF_TRUE  1 GOTO L  ->  GOTO L
          IF_TRUE  0 GOTO L  ->  (removed)
        """
        out: List[TACInstr] = []
        for instr in code:
            if instr.op == "IF_FALSE" and _is_int(instr.arg1):
                val = _vi(instr.arg1)
                self.report.condition_simplifies += 1
                if val == 0:
                    self.report.log.append(
                        f"[CS] IF_FALSE 0 GOTO {instr.result}  =>  GOTO {instr.result}"
                    )
                    out.append(TACInstr(op="GOTO", result=instr.result))
                else:
                    self.report.log.append(
                        f"[CS] IF_FALSE 1 GOTO {instr.result}  =>  removed (never branches)"
                    )
                continue

            if instr.op == "IF_TRUE" and _is_int(instr.arg1):
                val = _vi(instr.arg1)
                self.report.condition_simplifies += 1
                if val != 0:
                    self.report.log.append(
                        f"[CS] IF_TRUE 1 GOTO {instr.result}  =>  GOTO {instr.result}"
                    )
                    out.append(TACInstr(op="GOTO", result=instr.result))
                else:
                    self.report.log.append(
                        f"[CS] IF_TRUE 0 GOTO {instr.result}  =>  removed (never branches)"
                    )
                continue

            out.append(instr)
        return out

    # =======================================================================
    # PASS 3 - Dead Code / Dead Action Elimination
    # =======================================================================
    def _pass3_dead_code(self, code: List[TACInstr]) -> List[TACInstr]:
        code = self._elim_unreachable(code)
        code = self._elim_dead_temps(code)
        return code

    def _elim_unreachable(self, code: List[TACInstr]) -> List[TACInstr]:
        """Remove instructions between an unconditional GOTO/HALT and the next LABEL."""
        out: List[TACInstr] = []
        skip = False
        for instr in code:
            if instr.op == "LABEL":
                skip = False           # label restores reachability
            if skip:
                self.report.dead_code_removed += 1
                self.report.log.append(
                    f"[DC] Unreachable: {str(instr).strip()}"
                )
                continue
            out.append(instr)
            if instr.op in ("GOTO", "HALT"):
                skip = True
        return out

    def _elim_dead_temps(self, code: List[TACInstr]) -> List[TACInstr]:
        """
        Remove assignments to temporaries (tN) whose value is never read.
        A temporary is dead when:
          - no later instruction reads it in arg1 or arg2, and
          - it is not used as an IF guard.
        """
        def is_temp(name: Optional[str]) -> bool:
            return bool(name) and name[0] == "t" and name[1:].isdigit()

        reads: Set[str] = set()
        for instr in code:
            for a in (instr.arg1, instr.arg2):
                if a and not _is_int(a):
                    reads.add(a)

        out: List[TACInstr] = []
        for instr in code:
            if (is_temp(instr.result)
                    and instr.result not in reads
                    and instr.op not in ("LABEL", "GOTO", "IF_FALSE", "IF_TRUE",
                                         "WRITE", "WRITE_STR", "READ", "HALT", "RETURN")):
                self.report.dead_code_removed += 1
                self.report.log.append(
                    f"[DC] Dead temp: {str(instr).strip()}"
                )
                continue
            out.append(instr)
        return out

    # =======================================================================
    # PASS 4 - Duplicate Extraction / Copy Elimination
    # =======================================================================
    def _pass4_duplicates(self, code: List[TACInstr]) -> List[TACInstr]:
        code = self._elim_dup_copies(code)
        code = self._elim_dup_write_str(code)
        code = self._elim_dup_exprs(code)
        return code

    def _elim_dup_copies(self, code: List[TACInstr]) -> List[TACInstr]:
        """Remove redundant COPY instructions within a basic block."""
        copy_state: Dict[str, str] = {}
        out: List[TACInstr] = []
        for instr in code:
            if instr.op in ("LABEL", "GOTO", "CALL", "RETURN", "HALT"):
                copy_state.clear()
                out.append(instr)
                continue

            if instr.op == "COPY" and instr.result and instr.arg1:
                if copy_state.get(instr.result) == instr.arg1:
                    self.report.duplicates_removed += 1
                    self.report.log.append(
                        f"[DE] Dup copy removed: {instr.result} = {instr.arg1}  (already live)"
                    )
                    continue
                copy_state[instr.result] = instr.arg1
                stale = [k for k, v in copy_state.items()
                         if v == instr.result and k != instr.result]
                for k in stale:
                    del copy_state[k]
            elif instr.result and instr.result in copy_state:
                del copy_state[instr.result]

            out.append(instr)
        return out

    def _elim_dup_write_str(self, code: List[TACInstr]) -> List[TACInstr]:
        """Collapse consecutive identical WRITE_STR instructions."""
        out: List[TACInstr] = []
        prev: Optional[str] = None
        for instr in code:
            if instr.op == "WRITE_STR":
                if instr.arg1 == prev:
                    self.report.duplicates_removed += 1
                    self.report.log.append(
                        f"[DE] Dup WRITE_STR: {instr.arg1}"
                    )
                    continue
                prev = instr.arg1
            else:
                prev = None
            out.append(instr)
        return out

    def _elim_dup_exprs(self, code: List[TACInstr]) -> List[TACInstr]:
        """
        Common Sub-expression Elimination (CSE) within a basic block.
        If t2 = a OP b and t1 = a OP b was already computed (and a,b unchanged),
        replace t2 = a OP b with t2 = t1.
        """
        expr_map: Dict[Tuple[str, str, str], str] = {}
        out: List[TACInstr] = []

        for instr in code:
            if instr.op in ("LABEL", "GOTO", "CALL", "RETURN", "HALT"):
                expr_map.clear()
                out.append(instr)
                continue

            if instr.op in ARITH_OPS | REL_OPS and instr.arg1 and instr.arg2 and instr.result:
                key = (instr.arg1, instr.op, instr.arg2)
                if key in expr_map:
                    existing = expr_map[key]
                    self.report.duplicates_removed += 1
                    self.report.log.append(
                        f"[DE] CSE: {instr.result} = {instr.arg1} {instr.op} {instr.arg2}"
                        f"  =>  {instr.result} = {existing}"
                    )
                    out.append(TACInstr(op="COPY", result=instr.result, arg1=existing))
                    continue
                else:
                    expr_map[key] = instr.result

            if instr.result:
                stale = [k for k in expr_map
                         if k[0] == instr.result or k[2] == instr.result]
                for k in stale:
                    del expr_map[k]

            out.append(instr)
        return out


# ---------------------------------------------------------------------------
# Pretty-print helper (called from main.py)
# ---------------------------------------------------------------------------
def print_tac_comparison(
    original: List[TACInstr],
    optimized: List[TACInstr],
    report: OptimizationReport,
) -> None:
    W = 60
    print("\n" + "=" * W)
    print("  IR BEFORE OPTIMIZATION  (TAC from ICG)")
    print("=" * W)
    for i, instr in enumerate(original):
        print(f"  {i:3d}  {instr}")
    print(f"  --- {len(original)} instructions ---")

    print("\n" + "=" * W)
    print("  IR AFTER OPTIMIZATION")
    print("=" * W)
    for i, instr in enumerate(optimized):
        print(f"  {i:3d}  {instr}")
    removed = len(original) - len(optimized)
    print(f"  --- {len(optimized)} instructions  ({removed} removed) ---")

    print()
    print(report.summary())
