"""
============================================================
  Business Workflow DSL – Semantic Analyzer
  Performs robust semantic validation for Business Workflows:
    1. Undefined variables
    2. Duplicate variables
    3. Invalid event names
    4. Invalid action names
    5. Type mismatches
    6. Using a variable before it is defined
    7. Invalid workflow structure

  Every error provides:
    - error_type: str (e.g., 'UNDEFINED_VARIABLE', 'DUPLICATE_VARIABLE')
    - line: int (1-based line number)
    - col: int (1-based column number)
    - message: str (meaningful human-readable explanation)
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Set, Tuple
from symbol_table import SymbolTable, Symbol, TypeDesc


@dataclass
class WorkflowSemanticError:
    error_type: str
    line: int
    col: int
    message: str

    def __str__(self) -> str:
        return f"[SEMANTIC ERROR: {self.error_type}] Line {self.line}: {self.message}"


VALID_ACTIONS = {
    'WORKFLOW', 'ON', 'EXTRACT', 'SET', 'VALIDATE', 'IF', 'ELSE', 'CALL',
    'SAVE', 'NOTIFY', 'RETRY', 'WAIT', 'PARALLEL', 'LOG', 'END',
    'ENDWORKFLOW', 'PIPELINE', 'ENDPIPELINE', '}'
}


class WorkflowSemanticAnalyzer:
    """Semantic Analyzer dedicated to validating Business Workflow DSL rules."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.splitlines()
        self.errors: List[WorkflowSemanticError] = []
        self.sym_tab = SymbolTable()

        # Scope and symbol tracking
        self.defined_vars: Dict[str, int] = {}       # var_name -> line first defined
        self.var_types: Dict[str, str] = {}          # var_name -> 'NUMBER' | 'STRING' | 'BOOLEAN' | 'OBJECT' | 'LIST'
        self.extracted_vars: Dict[str, int] = {}     # var_name -> line extracted
        self.all_definitions: Dict[str, int] = {}    # all definitions across whole file
        self.workflow_name: Optional[str] = None
        self.workflow_line: Optional[int] = None
        self.event_name: Optional[str] = None
        self.event_line: Optional[int] = None

    def analyze(self) -> List[WorkflowSemanticError]:
        self.errors.clear()
        self.defined_vars.clear()
        self.var_types.clear()
        self.extracted_vars.clear()
        self.all_definitions.clear()
        self.workflow_name = None
        self.event_name = None
        self.sym_tab = SymbolTable()

        self._pre_scan_definitions()
        self._check_workflow_structure_and_statements()
        return self.errors


    def _add_error(self, error_type: str, line: int, col: int, message: str):
        self.errors.append(WorkflowSemanticError(error_type=error_type, line=line, col=col, message=message))

    def _pre_scan_definitions(self):
        """First pass to discover all variable definitions for use-before-def detection."""
        for idx, raw in enumerate(self.lines, start=1):
            line = raw.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue

            # ON <domain>.<action>
            m_on = re.match(r"^ON(?:\s+([A-Za-z0-9_.]+))?", line, re.I)
            if m_on and m_on.group(1):
                ev = m_on.group(1).strip()
                if '.' in ev:
                    dom = ev.split('.')[0].lower()
                    if dom not in self.all_definitions:
                        self.all_definitions[dom] = idx

            # EXTRACT <var> FROM <src>
            m_ext = re.match(r"^EXTRACT\s+(\w+)\s+FROM\s+(\w+)$", line, re.I)
            if m_ext:
                var_name = m_ext.group(1).lower()
                if var_name not in self.all_definitions:
                    self.all_definitions[var_name] = idx
                continue

            # SET <var> [: TYPE] = <val>
            m_set = re.match(r"^SET\s+(\w+)(?:\s*:\s*\w+)?\s*=", line, re.I)
            if m_set:
                var_name = m_set.group(1).lower()
                if var_name not in self.all_definitions:
                    self.all_definitions[var_name] = idx
                continue


    def _check_workflow_structure_and_statements(self):
        active_workflow = False
        seen_workflow = False
        seen_event = False
        brace_depth = 0
        block_stack: List[Tuple[str, int]] = []  # (block_type, start_line)
        last_closed_block: Optional[Tuple[str, int]] = None

        for idx, raw in enumerate(self.lines, start=1):
            line = raw.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue

            # Handle Block Closure '}'
            if line == '}':
                if brace_depth <= 0 or not active_workflow:
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "Mismatched closing brace '}'. No open block to close."
                    )
                else:
                    brace_depth -= 1
                    if block_stack:
                        closed_kind, closed_line = block_stack.pop()
                        last_closed_block = (closed_kind, idx)
                        if closed_kind != 'WORKFLOW':
                            try:
                                self.sym_tab.exit_scope()
                            except RuntimeError:
                                pass
                        else:
                            active_workflow = False
                continue

            # Extract first token
            first_token = line.split()[0].upper().rstrip('{')

            # 4. Check for Invalid Action Names
            if first_token not in VALID_ACTIONS and not line.startswith('}'):
                if not re.match(r"^\}\s*ELSE", line, re.I):
                    self._add_error(
                        "INVALID_ACTION",
                        idx,
                        1,
                        f"Unrecognized action '{first_token}'. Allowed actions are: ON, EXTRACT, SET, VALIDATE, IF, ELSE, CALL, SAVE, NOTIFY, RETRY, WAIT, PARALLEL, LOG."
                    )
                    continue

            # 7. Check Structure: WORKFLOW Header
            m_wf = re.match(r"^(?:WORKFLOW|PIPELINE)(?:\s+(\w+))?\s*(\{)?$", line, re.I)
            if m_wf:
                wf_name = m_wf.group(1)
                has_brace = bool(m_wf.group(2))
                if not wf_name:
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "WORKFLOW statement requires a valid workflow identifier (e.g., 'WORKFLOW InvoiceProcessing {')."
                    )
                elif seen_workflow:
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        f"Multiple WORKFLOW declarations detected ('{wf_name}'). Only one workflow is allowed per file."
                    )
                else:
                    self.workflow_name = wf_name
                    self.workflow_line = idx
                    seen_workflow = True
                    active_workflow = True
                    self.sym_tab.enter_scope(f"workflow_{wf_name}")
                    if has_brace:
                        brace_depth += 1
                        block_stack.append(('WORKFLOW', idx))
                continue

            # Check if statements appear before WORKFLOW declaration
            if not seen_workflow:
                self._add_error(
                    "INVALID_STRUCTURE",
                    idx,
                    1,
                    f"Statement '{line}' appears before WORKFLOW header declaration."
                )
                continue

            # Check if statements appear after workflow was closed
            if not active_workflow:
                self._add_error(
                    "INVALID_STRUCTURE",
                    idx,
                    1,
                    f"Statement '{line}' appears outside of active WORKFLOW scope."
                )
                continue

            # Handle '} ELSE {' or 'ELSE {' or 'ELSE'
            m_else = re.match(r"^(?:\}\s*)?ELSE(?:\s*\{)?$", line, re.I)
            if m_else:
                has_brace = bool(re.search(r"\{", line))
                is_prev_if = (
                    (block_stack and block_stack[-1][0] == 'IF') or
                    (last_closed_block and last_closed_block[0] == 'IF')
                )
                if not is_prev_if:
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "'ELSE' block must follow a corresponding 'IF' block."
                    )
                else:
                    if block_stack and block_stack[-1][0] == 'IF':
                        block_stack.pop()
                        try:
                            self.sym_tab.exit_scope()
                        except RuntimeError:
                            pass
                    if has_brace:
                        brace_depth += 1
                        block_stack.append(('ELSE', idx))
                        self.sym_tab.enter_scope("else")
                    last_closed_block = None
                continue

            # Check RETRY count {
            m_retry = re.match(r"^RETRY(?:\s+(\d+))?\s*(\{)?$", line, re.I)
            if m_retry and line.upper().startswith('RETRY'):
                has_brace = bool(m_retry.group(2)) or line.endswith('{')
                if has_brace:
                    brace_depth += 1
                    block_stack.append(('RETRY', idx))
                    self.sym_tab.enter_scope("retry")
                continue

            # Check PARALLEL {
            m_par = re.match(r"^PARALLEL\s*(\{)?$", line, re.I)
            if m_par and line.upper().startswith('PARALLEL'):
                has_brace = bool(m_par.group(1)) or line.endswith('{')
                if has_brace:
                    brace_depth += 1
                    block_stack.append(('PARALLEL', idx))
                    self.sym_tab.enter_scope("parallel")
                continue

            # Check WAIT duration
            if line.upper().startswith('WAIT'):
                m_wait = re.match(r"^WAIT(?:\s+(\d+))?(?:\s+([a-zA-Z]+))?$", line, re.I)
                if not m_wait or not m_wait.group(1):
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "WAIT requires a numeric duration (e.g., 'WAIT 5 seconds')."
                    )
                continue

            # 3. Check Event Name (ON <event>)
            m_on = re.match(r"^ON(?:\s+(.*))?$", line, re.I)
            if m_on:
                raw_event = (m_on.group(1) or '').strip().strip("'\"")
                if not raw_event:
                    self._add_error(
                        "INVALID_EVENT",
                        idx,
                        1,
                        "ON trigger requires an event name (e.g., 'ON email.received')."
                    )
                elif not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$", raw_event):
                    self._add_error(
                        "INVALID_EVENT",
                        idx,
                        1,
                        f"Invalid event name '{raw_event}'. Event names must follow the '<domain>.<action>' pattern (e.g., 'email.received', 'order.placed')."
                    )
                else:
                    seen_event = True
                    self.event_name = raw_event
                    self.event_line = idx
                    # Register default payload source identifier and entity types
                    source_domain = raw_event.split('.')[0].lower()
                    self.defined_vars[source_domain] = idx
                    self.var_types[source_domain] = 'OBJECT'
                    self.sym_tab.declare(source_domain, TypeDesc('OBJECT'), line=idx)
                    # Register document entity if workflow name matches (e.g., 'invoice' for InvoiceProcessing)
                    if self.workflow_name:
                        wf_base = self.workflow_name.lower().replace('processing', '').replace('support', '').replace('workflow', '')
                        if wf_base and not self.sym_tab.lookup(wf_base):
                            self.defined_vars[wf_base] = idx
                            self.sym_tab.declare(wf_base, TypeDesc('OBJECT'), line=idx)
                continue

            # Require ON event before logic statements
            if not seen_event:
                self._add_error(
                    "INVALID_STRUCTURE",
                    idx,
                    1,
                    f"Workflow must declare an event trigger ('ON <event>') before statement '{line}'."
                )

            # 2. Check EXTRACT <var> FROM <src>
            if line.upper().startswith('EXTRACT'):
                m_ext = re.match(r"^EXTRACT(?:\s+([a-zA-Z0-9_]+))?(?:\s+FROM\s+([a-zA-Z0-9_]+))?$", line, re.I)
                if not m_ext or not m_ext.group(1) or not m_ext.group(2):
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        f"Malformed EXTRACT statement '{line}'. Expected syntax: 'EXTRACT <variable> FROM <source>'."
                    )
                else:
                    var_name = m_ext.group(1)
                    src_name = m_ext.group(2)
                    var_lower = var_name.lower()
                    src_lower = src_name.lower()

                    # Duplicate variable check in current scope
                    if self.sym_tab.lookup_current_scope(var_lower):
                        # Use all_definitions for the original declaration line (pre-scan tracks first occurrence)
                        orig_line = self.all_definitions.get(var_lower, self.defined_vars.get(var_lower, idx))
                        self._add_error(
                            "DUPLICATE_VARIABLE",
                            idx,
                            1,
                            f"Duplicate variable '{var_name}'. It was already declared on line {orig_line}."
                        )
                    else:
                        if var_lower in ('priority', 'status', 'vendor', 'type', 'category', 'name', 'subject'):
                            extracted_type = 'STRING'
                        elif var_lower in ('amount', 'total', 'subtotal', 'tax', 'discount', 'count', 'price', 'quantity', 'cost', 'balance', 'limit', 'ticket_count', 'retries'):
                            extracted_type = 'NUMBER'
                        else:
                            extracted_type = 'ANY'
                        self.var_types[var_lower] = extracted_type
                        self.defined_vars[var_lower] = idx
                        self.sym_tab.declare(var_lower, TypeDesc(extracted_type), line=idx)

                    # Check source definition
                    self._check_variable_defined(src_lower, src_name, idx)
                continue

            # Check SET <var> [ : <type> ] = <val>
            if line.upper().startswith('SET'):
                m_set = re.match(r"^SET(?:\s+([a-zA-Z0-9_]+))?(?:\s*:\s*([a-zA-Z0-9_]+))?(?:\s*=\s*(.+))?$", line, re.I)
                if not m_set or not m_set.group(1) or m_set.group(3) is None:
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        f"Malformed SET statement '{line}'. Expected syntax: 'SET <variable> [: TYPE] = <value>'."
                    )
                else:
                    var_name = m_set.group(1)
                    type_annotation = (m_set.group(2) or '').upper()
                    val_expr = m_set.group(3).strip()
                    var_lower = var_name.lower()

                    target_type = type_annotation if type_annotation in ('NUMBER', 'STRING', 'BOOLEAN', 'OBJECT', 'LIST') else 'NUMBER'

                    # Check duplicate variable definition in current scope
                    if self.sym_tab.lookup_current_scope(var_lower):
                        orig_line = self.defined_vars.get(var_lower, idx)
                        self._add_error(
                            "DUPLICATE_VARIABLE",
                            idx,
                            1,
                            f"Duplicate variable '{var_name}'. It was already declared on line {orig_line}."
                        )
                    else:
                        self.defined_vars[var_lower] = idx
                        self.var_types[var_lower] = target_type
                        self.sym_tab.declare(var_lower, TypeDesc(target_type), line=idx)

                    # Determine RHS type
                    rhs_type = None
                    if re.match(r"^-?\d+$", val_expr):
                        rhs_type = 'NUMBER'
                    elif val_expr.startswith("'") or val_expr.startswith('"'):
                        rhs_type = 'STRING'
                    elif val_expr.lower() in ('true', 'false'):
                        rhs_type = 'BOOLEAN'
                    elif val_expr.isidentifier():
                        rhs_sym = self.sym_tab.lookup(val_expr.lower())
                        if rhs_sym is None:
                            self._check_variable_defined(val_expr.lower(), val_expr, idx)
                        else:
                            rhs_type = str(rhs_sym.sym_type).upper()

                    # Perform compile-time static type check
                    if rhs_type and type_annotation and rhs_type != target_type:
                        self._add_error(
                            "TYPE_MISMATCH",
                            idx,
                            1,
                            f"Type Error: Expected {target_type} but found {rhs_type}."
                        )
                    elif (val_expr.startswith('"') or val_expr.startswith("'")) and target_type == 'NUMBER':
                        self._add_error(
                            "TYPE_MISMATCH",
                            idx,
                            1,
                            f"Type Error: Expected NUMBER but found STRING. Cannot assign string literal {val_expr} to numeric variable '{var_name}'."
                        )
                continue

            # Check VALIDATE <entity>
            if line.upper().startswith('VALIDATE'):
                m_val = re.match(r"^VALIDATE(?:\s+([a-zA-Z0-9_]+))?$", line, re.I)
                if not m_val or not m_val.group(1):
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "VALIDATE requires an entity identifier (e.g., 'VALIDATE order')."
                    )
                else:
                    ent_name = m_val.group(1)
                    if not self.sym_tab.lookup(ent_name.lower()):
                        self.sym_tab.declare(ent_name.lower(), TypeDesc('OBJECT'), line=idx)
                continue

            # Check CALL <service>(<args>)
            if line.upper().startswith('CALL'):
                m_call = re.match(r"^CALL(?:\s+([a-zA-Z0-9_]+))?(?:\s*\((.*?)\))?$", line, re.I)
                if not m_call or not m_call.group(1):
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "CALL requires a service function name (e.g., 'CALL processPayment(order)')."
                    )
                continue

            # 5 & 6. Check IF <condition> {
            if line.upper().startswith('IF'):
                m_if = re.match(r"^IF(?:\s+(.+?))?\s*(\{)?$", line, re.I)
                if not m_if or not m_if.group(1):
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "Malformed IF statement. Expected syntax: 'IF <condition> {'."
                    )
                else:
                    condition_str = m_if.group(1).rstrip('{').strip()
                    has_brace = bool(m_if.group(2)) or line.endswith('{')
                    if has_brace:
                        brace_depth += 1
                        block_stack.append(('IF', idx))
                        self.sym_tab.enter_scope("if")

                    self._validate_condition(condition_str, idx)
                continue

            # Check NOTIFY <target>
            if line.upper().startswith('NOTIFY'):
                m_notif = re.match(r"^NOTIFY(?:\s+(.+))?$", line, re.I)
                if not m_notif or not m_notif.group(1):
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "NOTIFY requires a recipient identifier or channel (e.g., 'NOTIFY finance')."
                    )
                else:
                    target = m_notif.group(1).strip()
                    if target.isidentifier():
                        sym = self.sym_tab.lookup(target.lower())
                        if sym is None:
                            if target.lower() in self.all_definitions:
                                self._check_variable_defined(target.lower(), target, idx)
                            else:
                                self.defined_vars[target.lower()] = idx
                                self.sym_tab.declare(target.lower(), TypeDesc('STRING'), line=idx)
                continue


            # Check SAVE <entity> TO <target>
            if line.upper().startswith('SAVE'):
                m_save = re.match(r"^SAVE(?:\s+([a-zA-Z0-9_]+))?(?:\s+TO\s+([a-zA-Z0-9_]+|'[^']+'))?$", line, re.I)
                if not m_save or not m_save.group(1) or not m_save.group(2):
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "SAVE requires 'SAVE <entity> TO <destination>' syntax."
                    )
                else:
                    entity = m_save.group(1)
                    dest = m_save.group(2)
                    if not self.sym_tab.lookup(entity.lower()):
                        self.sym_tab.declare(entity.lower(), TypeDesc('OBJECT'), line=idx)
                continue

            # Check LOG '<msg>'
            if line.upper().startswith('LOG'):
                m_log = re.match(r"^LOG\s+'([^']*)'$", line, re.I)
                if not m_log:
                    self._add_error(
                        "INVALID_STRUCTURE",
                        idx,
                        1,
                        "LOG requires string literal message syntax (e.g., LOG 'Processing completed')."
                    )
                continue

        # Check for unclosed workflow block
        if active_workflow and brace_depth > 0:
            self._add_error(
                "INVALID_STRUCTURE",
                len(self.lines),
                1,
                f"Workflow '{self.workflow_name}' is unclosed. Missing closing brace '}}' at end of file."
            )

        if not seen_workflow:
            self._add_error(
                "INVALID_STRUCTURE",
                1,
                1,
                "No WORKFLOW definition found in source file."
            )

    def _validate_condition(self, condition_str: str, line_idx: int):
        """Validate condition variables, definitions, operator types, and static type checking."""
        # Match binary comparison: <lhs> <op> <rhs>
        m_comp = re.match(r"^([a-zA-Z0-9_'\"]+)\s*(>|<|>=|<=|==|!=)\s*([a-zA-Z0-9_'\"]+)$", condition_str)
        if not m_comp:
            if condition_str.isidentifier():
                var_lower = condition_str.lower()
                self._check_variable_defined(var_lower, condition_str, line_idx)
            else:
                self._add_error(
                    "INVALID_STRUCTURE",
                    line_idx,
                    1,
                    f"Malformed condition '{condition_str}'. Expected comparison format: '<variable> <op> <value>'."
                )
            return

        lhs, op, rhs = m_comp.groups()

        lhs_is_str = lhs.startswith("'") or lhs.startswith('"')
        rhs_is_str = rhs.startswith("'") or rhs.startswith('"')

        lhs_type = 'STRING' if lhs_is_str else ('NUMBER' if lhs.isdigit() else None)
        rhs_type = 'STRING' if rhs_is_str else ('NUMBER' if rhs.isdigit() else None)

        # Check LHS variable if identifier
        if lhs.isidentifier() and not lhs.isdigit() and not lhs_is_str:
            self._check_variable_defined(lhs.lower(), lhs, line_idx)
            sym = self.sym_tab.lookup(lhs.lower())
            if sym:
                lhs_type = str(sym.sym_type).upper()

        # Check RHS variable if identifier
        if rhs.isidentifier() and not rhs.isdigit() and not rhs_is_str:
            self._check_variable_defined(rhs.lower(), rhs, line_idx)
            sym = self.sym_tab.lookup(rhs.lower())
            if sym:
                rhs_type = str(sym.sym_type).upper()

        # Static Type Mismatch Check for Relational Operators
        is_relational = op in ('>', '<', '>=', '<=')
        if is_relational:
            # Flag when either operand is a string literal, OR if a resolved var type is STRING
            lhs_string = lhs_is_str or lhs_type == 'STRING'
            rhs_string = rhs_is_str or rhs_type == 'STRING'
            if lhs_string or rhs_string:
                bad = lhs if lhs_string else rhs
                self._add_error(
                    "TYPE_MISMATCH",
                    line_idx,
                    1,
                    f"Type Error: Relational operator '{op}' cannot be applied to a STRING operand '{bad}'. Only NUMBER comparisons are valid."
                )
        else:
            if (lhs_type and rhs_type) and (lhs_type != rhs_type) and (lhs_type != 'ANY' and rhs_type != 'ANY'):
                self._add_error(
                    "TYPE_MISMATCH",
                    line_idx,
                    1,
                    f"Type Error: Cannot compare {lhs_type} with {rhs_type}."
                )



    def _check_variable_defined(self, var_lower: str, original_name: str, line_idx: int):
        """Check if variable is defined in scope stack or reported as undefined."""
        sym = self.sym_tab.lookup(var_lower)
        if sym is None:
            if var_lower in self.all_definitions:
                def_line = self.all_definitions[var_lower]
                if def_line > line_idx:
                    self._add_error(
                        "USE_BEFORE_DEF",
                        line_idx,
                        1,
                        f"Variable '{original_name}' is used on line {line_idx} before being defined on line {def_line}."
                    )
                else:
                    self._add_error(
                        "UNDEFINED_VARIABLE",
                        line_idx,
                        1,
                        f"Variable '{original_name}' is unavailable outside its block scope."
                    )
            else:
                self._add_error(
                    "UNDEFINED_VARIABLE",
                    line_idx,
                    1,
                    f"Variable '{original_name}' is undefined. Extract it from an event or assign it using SET."
                )

