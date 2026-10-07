"""
Agentic Debugger for the Business Workflow DSL Compiler.

This module intentionally sits OUTSIDE the deterministic compiler stages.
It does not change lexer/parser/semantic/codegen behavior or mutate compiler state.
Instead, it acts as an agentic diagnostic reviewer around compiler artifacts:

1. Observe source + compiler artifacts (AST, TAC, tokens, semantic errors, IR optimization report)
2. Diagnose issues across 7 core dimensions:
   - Undefined variables
   - Invalid workflow actions
   - Invalid event dependencies
   - Type errors
   - Invalid execution order
   - Unreachable actions
   - Missing required workflow steps
3. Explain root causes in developer-friendly language
4. Recommend safe, actionable fixes
5. Produce a structured validation report for CLI / Web IDE

Deterministic debugging is the default (zero API key required).
LLM-based explanation is kept completely optional.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


# Categories required by the Business Workflow Debugger
CAT_UNDEFINED_VARS       = "Undefined variables"
CAT_INVALID_ACTIONS      = "Invalid workflow actions"
CAT_INVALID_EVENT_DEPS   = "Invalid event dependencies"
CAT_TYPE_ERRORS          = "Type errors"
CAT_INVALID_EXEC_ORDER   = "Invalid execution order"
CAT_UNREACHABLE_ACTIONS  = "Unreachable actions"
CAT_MISSING_STEPS        = "Missing required workflow steps"


BUSINESS_STATEMENT_PATTERNS = {
    "WORKFLOW": r"^WORKFLOW\s+(\w+)\s*\{?$",
    "ON": r"^ON\s+([A-Za-z0-9_.]+)",
    "EXTRACT": r"^EXTRACT\s+(\w+)\s+FROM\s+(\w+)$",
    "SET": r"^SET\s+(\w+)\s*=\s*(.+)$",
    "IF": r"^IF\s+(.+?)\s*\{?$",
    "ELSE": r"^(?:\}\s*)?ELSE(?:\s*\{)?$",
    "NOTIFY": r"^NOTIFY\s+([\w@.-]+|'[^']*')$",
    "SAVE": r"^SAVE\s+(\w+)\s+TO\s+(\w+|'[^']+')$",
    "LOG": r"^LOG\s+'([^']*)'$",
    "RBRACE": r"^\}$",
    "ENDWORKFLOW": r"^ENDWORKFLOW$",
}

ML_STATEMENT_PATTERNS = {
    "PIPELINE": r"^PIPELINE\s+(\w+)\s*\{?$",
    "DATASET": r"^DATASET\s+(\w+)\s+FROM\s+'([^']+)'$",
    "MODEL": r"^MODEL\s+(\w+)\s+TASK\s+'([^']+)'$",
    "TRAIN": r"^TRAIN\s+(\w+)\s+ON\s+(\w+)\s+EPOCHS\s+(\d+)$",
    "EVALUATE": r"^EVALUATE\s+(\w+)$",
    "PREDICT": r"^PREDICT\s+(\w+)\s+INPUT\s*(-?\d+)(?:\s+INTO\s+(\w+))?$",
    "DEPLOY": r"^DEPLOY\s+(\w+)\s+TO\s+'([^']+)'$",
    "MONITOR": r"^MONITOR\s+(\w+)$",
    "ENDPIPELINE": r"^ENDPIPELINE$",
}


def is_business_dsl(source: str) -> bool:
    for raw in source.splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        upper = line.upper()
        if upper.startswith('WORKFLOW') or upper.startswith('ON ') or upper.startswith('EXTRACT') or upper.startswith('SAVE') or upper.startswith('NOTIFY'):
            return True
        if upper.startswith('PIPELINE') or upper.startswith('DATASET') or upper.startswith('MODEL'):
            return False
    return False


@dataclass
class AgentFinding:
    severity: str
    category: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class AgentReport:
    role: str
    status: str
    validation_score: int
    summary: str
    architecture_trace: List[str]
    findings: List[AgentFinding]
    suggested_fixes: List[str]
    workflow_graph: List[str]
    cv_evidence: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_text(self) -> str:
        lines = [
            f"Agent Role: {self.role}",
            f"Status: {self.status}",
            f"Validation Score: {self.validation_score}/100",
            "",
            "Summary:",
            f"  {self.summary}",
            "",
            "Architecture Trace:",
        ]
        lines.extend(f"  - {item}" for item in self.architecture_trace)
        lines.append("")
        lines.append("Workflow Graph:")
        if self.workflow_graph:
            lines.extend(f"  - {edge}" for edge in self.workflow_graph)
        else:
            lines.append("  - No workflow transition graph detected.")
        lines.append("")
        lines.append("Findings:")
        if self.findings:
            for f in self.findings:
                loc = f"Line {f.line}: " if f.line else ""
                lines.append(f"  [{f.severity.upper()}] {f.category}: {loc}{f.message}")
                if f.suggestion:
                    lines.append(f"      Fix: {f.suggestion}")
        else:
            lines.append("  - No issues found by the agent.")
        lines.append("")
        lines.append("Suggested Fixes:")
        if self.suggested_fixes:
            lines.extend(f"  - {fix}" for fix in self.suggested_fixes)
        else:
            lines.append("  - No fixes required.")
        lines.append("")
        lines.append("CV Evidence:")
        lines.extend(f"  - {item}" for item in self.cv_evidence)
        return "\n".join(lines)


class CompilerAgent:
    """Deterministic AI-agent diagnostic layer analyzing compiler artifacts."""

    def analyze(
        self,
        source: str,
        compile_results: Dict[str, Any],
        runtime_result: Optional[Dict[str, Any]] = None,
        runtime_error: Optional[Dict[str, Any]] = None,
    ) -> AgentReport:
        source_language = compile_results.get("source_language", "pascal_like_core_dsl")
        findings: List[AgentFinding] = []
        workflow_graph: List[str] = []

        # 1. Map lower-level compiler errors from artifacts
        findings.extend(self._explain_compiler_errors(compile_results))

        # 2. Perform deep artifact and structural analysis
        if is_business_dsl(source) or source_language == "business_workflow_dsl":
            biz_findings, workflow_graph = self._inspect_business_workflow(source, compile_results)
            findings.extend(biz_findings)
        elif source_language == "ai_workflow_dsl" or "PIPELINE" in source.upper():
            ml_findings, workflow_graph = self._inspect_ml_workflow(source)
            findings.extend(ml_findings)
        else:
            findings.extend(self._inspect_core_program(source))

        # 3. Incorporate runtime error or warnings without mutating compiler state
        if runtime_error:
            findings.append(
                AgentFinding(
                    severity="error",
                    category="Runtime execution",
                    line=runtime_error.get("line"),
                    message=runtime_error.get("message", "Runtime execution failed."),
                    suggestion="Verify runtime inputs, database records, and event handlers.",
                )
            )

        runtime_warnings = []
        if runtime_result:
            runtime_warnings = runtime_result.get("warnings", []) or []
        runtime_warnings.extend(compile_results.get("runtime_warnings", []) or [])
        for warning in runtime_warnings:
            findings.append(
                AgentFinding(
                    severity="warning",
                    category="Runtime warning",
                    message=str(warning),
                    suggestion="Review workflow logic and make conditions or handlers explicit.",
                )
            )

        # 4. Deduplicate findings: collapse same category on same line into single clearest finding
        deduped: List[AgentFinding] = []
        seen = set()
        for f in findings:
            key = (f.category, f.line) if f.line is not None else (f.category, f.message)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        status, score = self._score(compile_results, deduped, runtime_error)
        architecture_trace = self._architecture_trace(compile_results)
        suggested_fixes = self._suggested_fixes(deduped, source_language)
        summary = self._summary(status, source_language, compile_results, deduped)
        cv_evidence = self._cv_evidence(source_language)

        return AgentReport(
            role="Business Workflow Validation + Debugging Agent",
            status=status,
            validation_score=score,
            summary=summary,
            architecture_trace=architecture_trace,
            findings=deduped,
            suggested_fixes=suggested_fixes,
            workflow_graph=workflow_graph,
            cv_evidence=cv_evidence,
        )

    # ──────────────────────────────────────────────────────────
    # Architecture trace
    # ──────────────────────────────────────────────────────────
    def _architecture_trace(self, results: Dict[str, Any]) -> List[str]:
        trace = []
        lang = results.get("source_language", "pascal_like_core_dsl")
        if lang in ("business_workflow_dsl", "ai_workflow_dsl"):
            trace.append("Business Workflow DSL detected and validated through formal semantic analyzer.")
        else:
            trace.append("Core Pascal-like DSL compiled directly.")
        trace.append(f"Lexer produced {len(results.get('tokens', []) or [])} tokens.")
        trace.append("Parser produced an AST." if results.get("ast") else "Parser did not produce a valid AST.")
        trace.append(f"ICG produced {len(results.get('tac', []) or [])} Three-Address Code instructions.")
        if results.get("opt_report"):
            opt_rep = results["opt_report"]
            trace.append(f"IR Optimizer eliminated {opt_rep.total_eliminated} dead/duplicate instructions.")
        trace.append(f"CodeGen produced {len(results.get('asm', []) or [])} pseudo-assembly instructions.")
        return trace

    # ──────────────────────────────────────────────────────────
    # Compiler error explanation (Semantic / Lexical / Parser)
    # ──────────────────────────────────────────────────────────
    def _explain_compiler_errors(self, results: Dict[str, Any]) -> List[AgentFinding]:
        findings: List[AgentFinding] = []
        sem_errors = results.get("sem_error_objects") or results.get("sem_errors", []) or []

        for error in sem_errors:
            msg = getattr(error, "message", None) or str(error)
            line = getattr(error, "line", None)
            if line is None:
                m_line = re.search(r"Line\s+(\d+)", msg, re.I)
                if m_line:
                    line = int(m_line.group(1))
            clean_msg = re.sub(r"^\[SEMANTIC ERROR:[^\]]+\]\s*(?:Line\s+\d+:\s*)?", "", msg).strip()
            err_type = getattr(error, "error_type", None)

            # Classify into standard diagnostic categories
            if err_type == "UNDEFINED_VARIABLE" or "UNDEFINED_VARIABLE" in msg.upper() or "UNDECLARED" in msg.upper():
                cat = CAT_UNDEFINED_VARS
                sug = "Define variable with EXTRACT or SET before referencing it."
            elif err_type in ("INVALID_ACTION_NAME", "INVALID_ACTION") or "INVALID ACTION" in msg.upper() or "UNRECOGNIZED ACTION" in msg.upper() or "INVALID_ACTION" in msg.upper():
                cat = CAT_INVALID_ACTIONS
                sug = "Use supported actions: ON, EXTRACT, SET, IF, ELSE, NOTIFY, SAVE, or LOG."
            elif err_type == "INVALID_EVENT_NAME" or "INVALID EVENT" in msg.upper():
                cat = CAT_INVALID_EVENT_DEPS
                sug = "Declare trigger event as 'domain.event' (e.g. 'email.received')."
            elif err_type == "TYPE_MISMATCH" or "TYPE MISMATCH" in msg.upper():
                cat = CAT_TYPE_ERRORS
                sug = "Ensure condition operands and assignments use compatible integer types."
            elif err_type == "USE_BEFORE_DEF" or "BEFORE IT IS DEFINED" in msg.upper():
                cat = CAT_INVALID_EXEC_ORDER
                sug = "Move variable extraction or initialization before its first usage."
            elif err_type == "INVALID_WORKFLOW_STRUCTURE" or "STRUCTURE" in msg.upper():
                cat = CAT_MISSING_STEPS
                sug = "Wrap workflow in WORKFLOW Name { ... } with an initial ON trigger."
            else:
                cat = "Semantic analysis"
                sug = "Review line syntax and symbol declarations."

            findings.append(AgentFinding(severity="error", category=cat, message=clean_msg, line=line, suggestion=sug))

        for err in results.get("parse_errors", []) or []:
            msg = getattr(err, "message", None) or str(err)
            line = getattr(err, "line", None)
            findings.append(AgentFinding(severity="error", category="Parsing", message=msg, line=line, suggestion="Check syntax and statement structure."))

        for err in results.get("lex_errors", []) or []:
            msg = getattr(err, "message", None) or str(err)
            line = getattr(err, "line", None)
            findings.append(AgentFinding(severity="error", category="Lexical analysis", message=msg, line=line, suggestion="Check for unsupported tokens or unclosed delimiters."))

        return findings

    # ──────────────────────────────────────────────────────────
    # Deep Business Workflow Artifact Inspection
    # ──────────────────────────────────────────────────────────
    def _inspect_business_workflow(
        self, source: str, compile_results: Dict[str, Any]
    ) -> Tuple[List[AgentFinding], List[str]]:
        findings: List[AgentFinding] = []
        workflow_steps: List[str] = []

        lines = source.splitlines()
        defined_vars: Dict[str, int] = {}       # var_name -> line defined
        all_definitions: Dict[str, int] = {}    # var_name -> line anywhere
        extracted_vars: Set[str] = set()
        trigger_domain: Optional[str] = None
        trigger_event: Optional[str] = None
        trigger_line: Optional[int] = None
        workflow_name: Optional[str] = None
        seen_workflow = False
        seen_close = False
        actions_count = 0
        has_outcome = False
        inside_workflow = False
        block_depth = 0

        # Pre-scan definitions for use-before-def vs true undefined distinction
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            m_on = re.match(r"^ON\s+([A-Za-z0-9_.]+)", line, re.I)
            if m_on:
                ev_str = m_on.group(1).strip()
                if "." in ev_str:
                    dom = ev_str.split(".")[0].lower()
                    all_definitions[dom] = idx
            m_ext = re.match(r"^EXTRACT\s+(\w+)\s+FROM\s+(\w+)", line, re.I)
            if m_ext:
                all_definitions[m_ext.group(1).lower()] = idx
            m_set = re.match(r"^SET\s+(\w+)\s*=", line, re.I)
            if m_set:
                all_definitions[m_set.group(1).lower()] = idx

        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # WORKFLOW header
            m_wf = re.match(r"^WORKFLOW\s+(\w+)\s*(\{)?$", line, re.I)
            if m_wf:
                if seen_workflow:
                    findings.append(AgentFinding(
                        severity="warning",
                        category=CAT_MISSING_STEPS,
                        line=idx,
                        message="Multiple WORKFLOW declarations detected.",
                        suggestion="Define only one workflow per source file."
                    ))
                seen_workflow = True
                inside_workflow = True
                workflow_name = m_wf.group(1)
                workflow_steps.append(f"WORKFLOW:{workflow_name}")
                if m_wf.group(2) or "{" in line:
                    block_depth += 1
                continue

            # Closing brace
            if line == "}":
                if block_depth > 1:
                    block_depth -= 1
                elif block_depth == 1:
                    block_depth = 0
                    inside_workflow = False
                    seen_close = True
                    workflow_steps.append("ENDWORKFLOW")
                else:
                    findings.append(AgentFinding(
                        severity="error",
                        category=CAT_MISSING_STEPS,
                        line=idx,
                        message="Unmatched closing brace '}'.",
                        suggestion="Remove extraneous closing brace."
                    ))
                continue

            if not inside_workflow and seen_close:
                findings.append(AgentFinding(
                    severity="error",
                    category=CAT_INVALID_EXEC_ORDER,
                    line=idx,
                    message="Statement appears after workflow block has ended.",
                    suggestion="Move statement inside WORKFLOW block or remove it."
                ))
                continue
            elif not inside_workflow and not seen_workflow:
                findings.append(AgentFinding(
                    severity="error",
                    category=CAT_MISSING_STEPS,
                    line=idx,
                    message="Statement appears before WORKFLOW declaration.",
                    suggestion="Start workflow with: WORKFLOW <Name> {"
                ))
                continue

            # ----------------------------------------------------
            # 2. Check: Invalid workflow actions
            # ----------------------------------------------------
            first_word = line.split()[0].upper() if line.split() else ""
            valid_action_words = {"ON", "EXTRACT", "SET", "IF", "ELSE", "NOTIFY", "SAVE", "LOG", "}"}
            if first_word not in valid_action_words:
                findings.append(AgentFinding(
                    severity="error",
                    category=CAT_INVALID_ACTIONS,
                    line=idx,
                    message=f"Action '{line.split()[0]}' is not a recognized Business Workflow action.",
                    suggestion="Supported actions are: ON, EXTRACT, SET, IF, ELSE, NOTIFY, SAVE, LOG."
                ))
                continue

            # ----------------------------------------------------
            # 3. Check: Invalid event dependencies & execution order
            # ----------------------------------------------------
            if first_word == "ON":
                if trigger_line is not None:
                    findings.append(AgentFinding(
                        severity="error",
                        category=CAT_INVALID_EVENT_DEPS,
                        line=idx,
                        message="Duplicate trigger event. A workflow must contain exactly one 'ON' trigger.",
                        suggestion="Remove redundant 'ON' declaration."
                    ))
                else:
                    trigger_line = idx
                    if actions_count > 0:
                        findings.append(AgentFinding(
                            severity="error",
                            category=CAT_INVALID_EXEC_ORDER,
                            line=idx,
                            message="Invalid execution order: Action executed before trigger event 'ON'.",
                            suggestion="Place 'ON <domain>.<event>' as the first action inside WORKFLOW."
                        ))

                    m_on = re.match(r"^ON(?:\s+([A-Za-z0-9_.]+))?", line, re.I)
                    ev_str = m_on.group(1) if m_on else None
                    if not ev_str:
                        findings.append(AgentFinding(
                            severity="error",
                            category=CAT_INVALID_EVENT_DEPS,
                            line=idx,
                            message="Missing event name after ON.",
                            suggestion="Use format: ON <domain>.<event> (e.g. 'email.received')."
                        ))
                    elif "." not in ev_str or ev_str.startswith(".") or ev_str.endswith("."):
                        findings.append(AgentFinding(
                            severity="error",
                            category=CAT_INVALID_EVENT_DEPS,
                            line=idx,
                            message=f"Invalid event name '{ev_str}'. Event name must follow '<domain>.<event>' format.",
                            suggestion="Specify event as '<domain>.<event>', e.g. 'email.received'."
                        ))
                    else:
                        parts = ev_str.split(".")
                        trigger_domain = parts[0].lower()
                        trigger_event = parts[1].lower()
                        defined_vars[trigger_domain] = idx
                        workflow_steps.append(f"ON:{ev_str}")
                continue

            actions_count += 1

            if trigger_line is None:
                findings.append(AgentFinding(
                    severity="error",
                    category=CAT_INVALID_EVENT_DEPS,
                    line=idx,
                    message="Workflow action cannot execute before trigger event 'ON' is declared.",
                    suggestion="Add 'ON <domain>.<event>' before any workflow actions."
                ))

            # ----------------------------------------------------
            # EXTRACT action
            # ----------------------------------------------------
            if first_word == "EXTRACT":
                m_ext = re.match(r"^EXTRACT(?:\s+(\w+))?(?:\s+FROM\s+(\w+))?$", line, re.I)
                if not m_ext or not m_ext.group(1) or not m_ext.group(2):
                    findings.append(AgentFinding(
                        severity="error",
                        category=CAT_INVALID_ACTIONS,
                        line=idx,
                        message="Malformed EXTRACT statement. Expected: EXTRACT <var> FROM <source>",
                        suggestion="Syntax: EXTRACT <var> FROM <source>"
                    ))
                else:
                    var_name = m_ext.group(1).lower()
                    src_name = m_ext.group(2).lower()
                    if trigger_domain and src_name != trigger_domain and src_name not in defined_vars:
                        findings.append(AgentFinding(
                            severity="error",
                            category=CAT_INVALID_EVENT_DEPS,
                            line=idx,
                            message=f"Invalid event dependency: Cannot extract from '{src_name}'; trigger event is 'ON {trigger_domain}.{trigger_event}'.",
                            suggestion=f"Extract from trigger domain '{trigger_domain}' or ensure '{src_name}' was initialized."
                        ))
                    defined_vars[var_name] = idx
                    extracted_vars.add(var_name)
                    workflow_steps.append(f"EXTRACT:{var_name}->{src_name}")
                continue

            # ----------------------------------------------------
            # SET action
            # ----------------------------------------------------
            if first_word == "SET":
                m_set = re.match(r"^SET\s+(\w+)\s*=\s*(.+)$", line, re.I)
                if not m_set:
                    findings.append(AgentFinding(
                        severity="error",
                        category=CAT_INVALID_ACTIONS,
                        line=idx,
                        message="Malformed SET statement. Expected: SET <var> = <int>",
                        suggestion="Syntax: SET <var> = <integer_value>"
                    ))
                else:
                    var_name = m_set.group(1).lower()
                    val_str = m_set.group(2).strip()
                    if not re.match(r"^-?\d+$", val_str):
                        findings.append(AgentFinding(
                            severity="error",
                            category=CAT_TYPE_ERRORS,
                            line=idx,
                            message=f"Type mismatch: '{val_str}' is not an integer literal.",
                            suggestion="Variables in Business Workflow DSL must be assigned integer values."
                        ))
                    defined_vars[var_name] = idx
                    workflow_steps.append(f"SET:{var_name}={val_str}")
                continue

            # ----------------------------------------------------
            # IF / ELSE action
            # ----------------------------------------------------
            if first_word == "IF":
                if "{" in line:
                    block_depth += 1
                cond_part = re.sub(r"^IF\s+", "", line, flags=re.I).rstrip("{").strip()
                workflow_steps.append(f"IF:{cond_part}")

                m_cond = re.match(r"^([A-Za-z_]\w*)\s*([><!=]=?|==)\s*(.+)$", cond_part)
                if m_cond:
                    lhs = m_cond.group(1).lower()
                    op = m_cond.group(2)
                    rhs = m_cond.group(3).strip()

                    # Undefined variable / Use-before-def check on LHS
                    if lhs not in defined_vars:
                        if lhs in all_definitions:
                            findings.append(AgentFinding(
                                severity="error",
                                category=CAT_INVALID_EXEC_ORDER,
                                line=idx,
                                message=f"Variable '{lhs}' is used at line {idx} before its definition at line {all_definitions[lhs]}.",
                                suggestion=f"Move definition of '{lhs}' before this condition."
                            ))
                        else:
                            findings.append(AgentFinding(
                                severity="error",
                                category=CAT_UNDEFINED_VARS,
                                line=idx,
                                message=f"Variable '{lhs}' used in condition is not defined.",
                                suggestion=f"Define '{lhs}' using EXTRACT or SET before this IF statement."
                            ))

                    # If RHS is also an identifier, check its definition
                    if re.match(r"^[A-Za-z_]\w*$", rhs):
                        rhs_id = rhs.lower()
                        if rhs_id not in defined_vars:
                            if rhs_id in all_definitions:
                                findings.append(AgentFinding(
                                    severity="error",
                                    category=CAT_INVALID_EXEC_ORDER,
                                    line=idx,
                                    message=f"Variable '{rhs_id}' is used at line {idx} before its definition at line {all_definitions[rhs_id]}.",
                                    suggestion=f"Move definition of '{rhs_id}' before this condition."
                                ))
                            else:
                                findings.append(AgentFinding(
                                    severity="error",
                                    category=CAT_UNDEFINED_VARS,
                                    line=idx,
                                    message=f"Variable '{rhs_id}' used in condition is not defined.",
                                    suggestion=f"Define '{rhs_id}' using EXTRACT or SET before this condition."
                                ))
                    elif rhs.startswith("'") or rhs.startswith('"') or not re.match(r"^-?\d+$", rhs):
                        # Type error check
                        findings.append(AgentFinding(
                            severity="error",
                            category=CAT_TYPE_ERRORS,
                            line=idx,
                            message=f"Type mismatch in condition: cannot compare variable '{lhs}' with non-integer '{rhs}'.",
                            suggestion="Ensure comparison operand is an integer literal or integer variable."
                        ))

                # Unreachable actions check (static constant conditions)
                m_const_cond = re.match(r"^(-?\d+)\s*(>|<|>=|<=|==|!=)\s*(-?\d+)$", cond_part)
                if m_const_cond:
                    c_lhs = int(m_const_cond.group(1))
                    c_op = m_const_cond.group(2)
                    c_rhs = int(m_const_cond.group(3))
                    eval_res = False
                    if c_op == '>': eval_res = (c_lhs > c_rhs)
                    elif c_op == '<': eval_res = (c_lhs < c_rhs)
                    elif c_op == '>=': eval_res = (c_lhs >= c_rhs)
                    elif c_op == '<=': eval_res = (c_lhs <= c_rhs)
                    elif c_op == '==': eval_res = (c_lhs == c_rhs)
                    elif c_op == '!=': eval_res = (c_lhs != c_rhs)

                    if not eval_res:
                        findings.append(AgentFinding(
                            severity="warning",
                            category=CAT_UNREACHABLE_ACTIONS,
                            line=idx,
                            message=f"Condition '{cond_part}' statically evaluates to FALSE; actions inside this block will never execute.",
                            suggestion="Modify condition to use dynamic variables or remove unreachable block."
                        ))
                continue

            if first_word == "ELSE":
                workflow_steps.append("ELSE")
                continue

            # ----------------------------------------------------
            # NOTIFY action
            # ----------------------------------------------------
            if first_word == "NOTIFY":
                has_outcome = True
                m_notif = re.match(r"^NOTIFY\s+(\S+)$", line, re.I)
                if not m_notif:
                    findings.append(AgentFinding(
                        severity="error",
                        category=CAT_INVALID_ACTIONS,
                        line=idx,
                        message="Malformed NOTIFY statement. Expected: NOTIFY <recipient>",
                        suggestion="Syntax: NOTIFY <recipient_name>"
                    ))
                else:
                    recip = m_notif.group(1).strip("'\"")
                    workflow_steps.append(f"NOTIFY:{recip}")
                continue

            # ----------------------------------------------------
            # SAVE action
            # ----------------------------------------------------
            if first_word == "SAVE":
                has_outcome = True
                m_save = re.match(r"^SAVE(?:\s+(\w+))?(?:\s+TO\s+(\w+))?$", line, re.I)
                if not m_save or not m_save.group(1) or not m_save.group(2):
                    findings.append(AgentFinding(
                        severity="error",
                        category=CAT_INVALID_ACTIONS,
                        line=idx,
                        message="Malformed SAVE statement. Expected: SAVE <entity> TO <destination>",
                        suggestion="Syntax: SAVE <entity> TO <destination>"
                    ))
                else:
                    entity = m_save.group(1).lower()
                    dest = m_save.group(2).lower()
                    if not extracted_vars:
                        findings.append(AgentFinding(
                            severity="warning",
                            category=CAT_INVALID_EXEC_ORDER,
                            line=idx,
                            message="Entity saved before any fields have been extracted from event payload.",
                            suggestion="Extract payload data before saving entity to destination."
                        ))
                    is_wf_entity = bool(workflow_name and entity in workflow_name.lower())
                    if trigger_domain and entity != trigger_domain and entity not in defined_vars and not is_wf_entity:
                        if entity in all_definitions:
                            findings.append(AgentFinding(
                                severity="error",
                                category=CAT_INVALID_EXEC_ORDER,
                                line=idx,
                                message=f"Entity '{entity}' is saved at line {idx} before its definition at line {all_definitions[entity]}.",
                                suggestion=f"Move extraction or definition of '{entity}' before line {idx}."
                            ))
                        else:
                            findings.append(AgentFinding(
                                severity="error",
                                category=CAT_UNDEFINED_VARS,
                                line=idx,
                                message=f"Entity '{entity}' to save has not been extracted or defined.",
                                suggestion=f"Define or extract '{entity}' before saving it to '{dest}'."
                            ))
                    workflow_steps.append(f"SAVE:{entity}->{dest}")
                continue

            # ----------------------------------------------------
            # LOG action
            # ----------------------------------------------------
            if first_word == "LOG":
                has_outcome = True
                workflow_steps.append("LOG")
                continue

        # --------------------------------------------------------
        # Post-loop checks: Missing steps & Unreachable instructions
        # --------------------------------------------------------
        if not seen_workflow:
            findings.append(AgentFinding(
                severity="error",
                category=CAT_MISSING_STEPS,
                line=1,
                message="Missing WORKFLOW declaration.",
                suggestion="Start workflow with: WORKFLOW <Name> {"
            ))

        if trigger_line is None:
            findings.append(AgentFinding(
                severity="error",
                category=CAT_MISSING_STEPS,
                line=None,
                message="Missing required trigger event 'ON <domain>.<event>'.",
                suggestion="Declare a trigger event, e.g.: ON email.received"
            ))

        if actions_count == 0:
            findings.append(AgentFinding(
                severity="error",
                category=CAT_MISSING_STEPS,
                line=None,
                message="Workflow contains no executable actions.",
                suggestion="Add workflow actions such as EXTRACT, IF, NOTIFY, or SAVE."
            ))
        elif not has_outcome:
            findings.append(AgentFinding(
                severity="warning",
                category=CAT_MISSING_STEPS,
                line=None,
                message="Workflow has no outcome actions (missing NOTIFY, SAVE, or LOG).",
                suggestion="Add an outcome action such as 'NOTIFY <team>' or 'SAVE <entity> TO database'."
            ))

        if block_depth > 0 or not seen_close:
            findings.append(AgentFinding(
                severity="error",
                category=CAT_MISSING_STEPS,
                line=len(lines),
                message="Workflow block is not closed (missing '}').",
                suggestion="Close workflow block with '}'."
            ))

        # Check compiler artifacts: IR Optimizer report for eliminated dead instructions
        opt_report = compile_results.get("opt_report")
        if opt_report:
            if getattr(opt_report, "condition_simplifies", 0) > 0 or getattr(opt_report, "dead_code_removed", 0) > 0:
                for entry in getattr(opt_report, "log", []):
                    if "[CS]" in entry and ("always branches" in entry or "IF_FALSE 0" in entry):
                        findings.append(AgentFinding(
                            severity="warning",
                            category=CAT_UNREACHABLE_ACTIONS,
                            line=None,
                            message=f"IR Optimization Pass simplified unreachable branch: {entry}",
                            suggestion="Review condition to ensure dynamic branching is preserved."
                        ))
                    elif "[DC]" in entry and "dead" in entry.lower():
                        findings.append(AgentFinding(
                            severity="info",
                            category=CAT_UNREACHABLE_ACTIONS,
                            line=None,
                            message=f"IR Optimization Pass removed dead instruction: {entry}",
                            suggestion="Clean up unused or dead code."
                        ))

        graph = self._build_graph(workflow_steps)
        return findings, graph

    # ──────────────────────────────────────────────────────────
    # ML Workflow Inspection (Backward Compatibility)
    # ──────────────────────────────────────────────────────────
    def _inspect_ml_workflow(self, source: str) -> Tuple[List[AgentFinding], List[str]]:
        findings: List[AgentFinding] = []
        datasets: Set[str] = set()
        models: Dict[str, Dict[str, Any]] = {}
        active = False
        seen_pipeline = False
        seen_end = False
        workflow_steps: List[str] = []

        for idx, raw in enumerate(source.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            matched = False
            for kind, pattern in ML_STATEMENT_PATTERNS.items():
                m = re.match(pattern, line, re.I)
                if not m:
                    continue
                matched = True

                if kind == "PIPELINE":
                    seen_pipeline = True
                    active = True
                    workflow_steps.append(f"PIPELINE:{m.group(1)}")
                elif kind == "ENDPIPELINE":
                    active = False
                    seen_end = True
                    workflow_steps.append("ENDPIPELINE")
                elif not active:
                    findings.append(AgentFinding("error", "Workflow structure", "Statement appears outside PIPELINE block.", idx, "Move inside PIPELINE."))
                elif kind == "DATASET":
                    datasets.add(m.group(1).lower())
                    workflow_steps.append(f"DATASET:{m.group(1)}")
                elif kind == "MODEL":
                    models[m.group(1).lower()] = {"trained": False, "evaluated": False, "deployed": False}
                    workflow_steps.append(f"MODEL:{m.group(1)}")
                elif kind == "TRAIN":
                    model, dataset = m.group(1).lower(), m.group(2).lower()
                    if dataset not in datasets:
                        findings.append(AgentFinding("error", "Data dependency", f"Dataset '{dataset}' used before ingestion.", idx, "Declare DATASET first."))
                    if model in models:
                        models[model]["trained"] = True
                    workflow_steps.append(f"TRAIN:{model}->{dataset}")
                elif kind == "EVALUATE":
                    model = m.group(1).lower()
                    if model in models:
                        models[model]["evaluated"] = True
                    workflow_steps.append(f"EVALUATE:{model}")
                elif kind == "DEPLOY":
                    model = m.group(1).lower()
                    if model in models:
                        models[model]["deployed"] = True
                    workflow_steps.append(f"DEPLOY:{model}")
                elif kind == "MONITOR":
                    model = m.group(1).lower()
                    if model in models and not models[model]["deployed"]:
                        findings.append(AgentFinding("warning", "Model lifecycle", f"Monitoring model '{model}' before DEPLOY.", idx, "Add DEPLOY before MONITOR."))
                    workflow_steps.append(f"MONITOR:{model}")
                break

            if not matched:
                findings.append(AgentFinding("error", "DSL syntax", f"Unsupported ML DSL statement: '{line}'", idx, "Check ML DSL syntax."))

        if not seen_pipeline:
            findings.append(AgentFinding("error", "Workflow structure", "Missing PIPELINE declaration.", None, "Start with: PIPELINE Name"))
        if not seen_end:
            findings.append(AgentFinding("error", "Workflow structure", "Missing ENDPIPELINE.", None, "End with: ENDPIPELINE"))

        graph = self._build_graph(workflow_steps)
        return findings, graph

    # ──────────────────────────────────────────────────────────
    # Core Pascal Program Inspection
    # ──────────────────────────────────────────────────────────
    def _inspect_core_program(self, source: str) -> List[AgentFinding]:
        findings: List[AgentFinding] = []
        if "program" not in source.lower():
            findings.append(AgentFinding("warning", "Core DSL structure", "Program header not detected.", None, "Start with: program Name;"))
        if "begin" not in source.lower() or "end." not in source.lower():
            findings.append(AgentFinding("warning", "Core DSL structure", "Program should include begin ... end. block.", None, "Wrap statements in begin ... end."))
        return findings

    def _build_graph(self, steps: Iterable[str]) -> List[str]:
        clean = [s for s in steps if s]
        return [f"{a} -> {b}" for a, b in zip(clean, clean[1:])]

    def _score(self, results: Dict[str, Any], findings: List[AgentFinding], runtime_error: Optional[Dict[str, Any]]) -> Tuple[str, int]:
        score = 100
        if not results.get("success"):
            score -= 25
        if runtime_error:
            score -= 20
        for f in findings:
            if f.severity == "error":
                score -= 15
            elif f.severity == "warning":
                score -= 7
            elif f.severity == "info":
                score -= 2
        score = max(0, min(100, score))
        has_blocking = (not results.get("success")) or (runtime_error is not None) or any(f.severity == "error" for f in findings)
        if has_blocking:
            return "blocked", score
        if score >= 85:
            return "production-ready", score
        return "needs-review", score

    def _suggested_fixes(self, findings: List[AgentFinding], source_language: str) -> List[str]:
        seen = set()
        fixes = []
        for f in findings:
            if f.suggestion and f.suggestion not in seen:
                fixes.append(f.suggestion)
                seen.add(f.suggestion)
        if not fixes and source_language in ("business_workflow_dsl", "ai_workflow_dsl"):
            fixes.append("Workflow is structurally valid and passed all agentic verification checks.")
        return fixes[:8]

    def _summary(self, status: str, source_language: str, results: Dict[str, Any], findings: List[AgentFinding]) -> str:
        errors = sum(1 for f in findings if f.severity == "error")
        warnings = sum(1 for f in findings if f.severity == "warning")
        lang = "Business Workflow DSL" if source_language in ("business_workflow_dsl", "ai_workflow_dsl") else "core Pascal-like DSL"
        categories = sorted(list({f.category for f in findings}))
        cat_str = f" Diagnosed categories: {', '.join(categories)}." if categories else ""
        if status == "production-ready":
            return f"The {lang} program compiled successfully and passed all agentic verification checks with no blocking issues."
        if status == "needs-review":
            return f"The {lang} program is valid, but the agent diagnosed {errors} error(s) and {warnings} warning(s).{cat_str}"
        return f"The {lang} program is blocked by validation issues. The agent diagnosed {errors} error(s) and {warnings} warning(s).{cat_str}"

    def _cv_evidence(self, source_language: str) -> List[str]:
        if source_language in ("business_workflow_dsl", "ai_workflow_dsl"):
            return [
                "Agent analyzes Business Workflow DSL compiler artifacts across all 7 verification categories without mutating compiler state.",
                "Diagnostic checks: Undefined variables, Invalid actions, Event dependencies, Type errors, Execution order, Unreachable actions, and Missing steps.",
                "Deterministic heuristic analysis runs by default with zero external dependencies; optional LLM explanation available via OpenAI/Gemini.",
            ]
        return [
            "Agent layer reviews compiler artifacts without changing deterministic compiler behavior.",
            "Compiler artifacts include tokens, AST, TAC, pseudo-assembly, listing output, and diagnostic report.",
        ]
