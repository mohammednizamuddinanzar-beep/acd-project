from __future__ import annotations

from dataclasses import dataclass, field
import datetime
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


@dataclass
class AIRuntimeError(Exception):
    message: str
    line: int
    col: int = 1

    def __str__(self) -> str:
        return f"[RUNTIME ERROR] Line {self.line}: {self.message}"


# Alias for domain clarity
WorkflowRuntimeError = AIRuntimeError


@dataclass
class WorkflowExecutionContext:
    variables: Dict[str, Any] = field(default_factory=dict)
    database: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    notifications: List[Dict[str, Any]] = field(default_factory=list)
    event_payload: Dict[str, Any] = field(default_factory=dict)
    audit_logs: List[Dict[str, Any]] = field(default_factory=list)


class AIWorkflowRuntime:
    """Business Workflow Execution Engine.

    Executes compiled business workflow statements:
      - ON: Trigger event listener with mock incoming payloads
      - EXTRACT: Data extraction from incoming event records
      - SET: Variable and parameter assignment
      - IF / ELSE: Conditional branching logic
      - SAVE: In-memory document & entity database persistence
      - NOTIFY: In-memory notification dispatch & alerting
      - LOG: Process status reporting
    """

    def __init__(self, source: str, base_dir: Optional[str] = None, event_payload: Optional[Dict[str, Any]] = None):
        self.source = source
        self.lines = source.splitlines()
        self.base_dir = Path(base_dir or '.').resolve()
        self.workflow_name: Optional[str] = None
        self.output: List[str] = []
        self.warnings: List[str] = []

        # In-memory execution state
        self.variables: Dict[str, Any] = {}
        self.database: Dict[str, List[Dict[str, Any]]] = {}
        self.notifications: List[Dict[str, Any]] = []
        self.audit_logs: List[Dict[str, Any]] = []

        # Default mock event payload (e.g. for email.received)
        self.mock_events: Dict[str, Dict[str, Any]] = {
            'email': {
                'amount': 75000,
                'invoice_id': 'INV-2026-8891',
                'sender': 'billing@supplier-corp.com',
                'recipient': 'accounts-payable@company.com',
                'subject': 'Invoice for Q3 Enterprise Services',
            },
            'order': {
                'amount': 12000,
                'order_id': 'ORD-5542',
                'customer': 'enterprise_client_12',
            },
            'invoice': {
                'amount': 75000,
                'status': 'PENDING_APPROVAL',
                'vendor': 'Acme Supplies',
            }
        }
        if event_payload:
            self.mock_events['custom'] = event_payload

    def execute(self) -> Dict[str, Any]:
        """Execute the workflow AST/statements sequentially with block support."""
        self._execute_statements(self.lines)
        return {
            'output': '\n'.join(self.output),
            'warnings': self.warnings,
            'variables': dict(self.variables),
            'database': dict(self.database),
            'notifications': list(self.notifications),
            'audit_logs': list(self.audit_logs),
        }

    def _execute_statements(self, raw_lines: List[str]):
        i = 0
        while i < len(raw_lines):
            line_idx = i + 1
            raw = raw_lines[i]
            line = raw.strip()
            i += 1

            if not line or line.startswith('#') or line.startswith('//'):
                continue

            # WORKFLOW / PIPELINE root
            m_wf = re.match(r'^(?:WORKFLOW|PIPELINE)\s+(\w+)\s*\{?$', line, re.I)
            if m_wf:
                self.workflow_name = m_wf.group(1)
                self.output.append(f"Workflow Started: {self.workflow_name}")
                self._log_audit("WORKFLOW_START", f"Workflow {self.workflow_name} initialized")
                continue

            # ENDWORKFLOW / ENDPIPELINE / closing root brace
            if re.match(r'^(?:ENDWORKFLOW|ENDPIPELINE)$', line, re.I) or line == '}':
                if self.workflow_name:
                    self.output.append(f"Workflow Completed: {self.workflow_name}")
                    self._log_audit("WORKFLOW_END", f"Workflow {self.workflow_name} finished successfully")
                continue

            # ON event
            m_on = re.match(r"^ON\s+([A-Za-z0-9_.]+)", line, re.I)
            if m_on:
                event_name = m_on.group(1)
                self.output.append(f"Event Triggered: ON {event_name}")
                self._log_audit("EVENT_RECEIVED", f"Triggered on event: {event_name}")
                continue

            # EXTRACT <var> FROM <source>
            m_ext = re.match(r"^EXTRACT\s+(\w+)\s+FROM\s+(\w+)$", line, re.I)
            if m_ext:
                var_name, src_name = m_ext.groups()
                src_data = self.mock_events.get(src_name.lower(), self.mock_events.get('email', {}))
                extracted_val = src_data.get(var_name.lower(), 75000 if var_name.lower() == 'amount' else 1)
                self.variables[var_name.lower()] = extracted_val
                self.output.append(f"Data Extracted: {var_name} = {extracted_val} (from '{src_name}')")
                self._log_audit("DATA_EXTRACT", f"Extracted {var_name}={extracted_val} from {src_name}")
                continue

            # SET <var> = <expr>
            m_set = re.match(r'^SET\s+(\w+)\s*=\s*(-?\d+)$', line, re.I)
            if m_set:
                var_name, val = m_set.groups()
                self.variables[var_name.lower()] = int(val)
                self.output.append(f"Variable Set: {var_name} = {val}")
                self._log_audit("VARIABLE_SET", f"Set {var_name}={val}")
                continue

            # IF <condition> { ... } [ ELSE { ... } ]
            m_if = re.match(r"^IF\s+(.+?)\s*\{?$", line, re.I)
            if m_if:
                condition_str = m_if.group(1).rstrip('{').strip()
                then_lines, else_lines, new_i = self._parse_if_block(raw_lines, i)
                i = new_i
                cond_result = self._evaluate_condition(condition_str, line_idx)
                self.output.append(f"Condition Evaluated: ({condition_str}) -> {'TRUE' if cond_result else 'FALSE'}")
                if cond_result:
                    self._execute_statements(then_lines)
                elif else_lines:
                    self._execute_statements(else_lines)
                continue

            # NOTIFY <target>
            m_notif = re.match(r"^NOTIFY\s+([\w@.-]+|'[^']*')$", line, re.I)
            if m_notif:
                target = m_notif.group(1).strip("'")
                notif_record = {
                    'recipient': target,
                    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'context': dict(self.variables),
                }
                self.notifications.append(notif_record)
                self.output.append(f"Notification Sent: [Recipient: '{target}'] (Context: {self.variables})")
                self._log_audit("NOTIFICATION_SENT", f"Alert sent to {target}")
                continue

            # SAVE <entity> TO <target>
            m_save = re.match(r"^SAVE\s+(\w+)\s+TO\s+(\w+|'[^']+')$", line, re.I)
            if m_save:
                entity, dest = m_save.groups()
                dest_table = dest.strip("'")
                if dest_table not in self.database:
                    self.database[dest_table] = []
                record = {
                    'id': f"{entity}_{len(self.database[dest_table]) + 1}",
                    'entity': entity,
                    'saved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'attributes': dict(self.variables),
                }
                self.database[dest_table].append(record)
                self.output.append(f"Database Record Saved: '{entity}' stored into table '{dest_table}' (Total records: {len(self.database[dest_table])})")
                self._log_audit("DB_SAVE", f"Saved {entity} to table {dest_table}")
                continue

            # LOG '<message>'
            m_log = re.match(r"^LOG\s+'([^']*)'$", line, re.I)
            if m_log:
                msg = m_log.group(1)
                self.output.append(f"Log: {msg}")
                self._log_audit("LOG", msg)
                continue

    def _parse_if_block(self, lines: List[str], current_i: int) -> tuple[List[str], List[str], int]:
        """Collect lines belonging to THEN and optional ELSE blocks."""
        then_lines = []
        else_lines = []
        in_else = False
        depth = 1

        i = current_i
        while i < len(lines):
            raw = lines[i]
            trimmed = raw.strip()
            i += 1

            if not trimmed:
                continue

            # Check for '} ELSE {' or '} ELSE'
            if re.match(r'^\}\s*ELSE(?:\s*\{)?$', trimmed, re.I) and depth == 1:
                in_else = True
                continue

            # Check for standalone 'ELSE {' or 'ELSE'
            if re.match(r'^ELSE(?:\s*\{)?$', trimmed, re.I) and depth == 1:
                in_else = True
                continue

            if '{' in trimmed:
                depth += trimmed.count('{')
            if '}' in trimmed:
                depth -= trimmed.count('}')
                if depth == 0:
                    # Look ahead to see if next non-empty line is an ELSE
                    next_is_else = False
                    for peek_idx in range(i, len(lines)):
                        peek_line = lines[peek_idx].strip()
                        if not peek_line:
                            continue
                        if re.match(r'^ELSE(?:\s*\{)?$', peek_line, re.I):
                            next_is_else = True
                            i = peek_idx + 1
                            in_else = True
                            depth = 1
                        break
                    if not next_is_else:
                        break
                    continue

            if in_else:
                else_lines.append(raw)
            else:
                then_lines.append(raw)

        return then_lines, else_lines, i

    def _evaluate_condition(self, cond: str, line_idx: int) -> bool:
        """Evaluate a relational comparison condition in the workflow variable scope."""
        m_comp = re.match(r"^(\w+)\s*(>|<|>=|<=|==|!=)\s*(-?\d+|\w+)$", cond)
        if not m_comp:
            # Fallback simple truthiness
            val = self.variables.get(cond.lower(), 1)
            return bool(val)

        lhs_var, op, rhs_val = m_comp.groups()
        left = self.variables.get(lhs_var.lower(), 0)
        try:
            right = int(rhs_val)
        except ValueError:
            right = self.variables.get(rhs_val.lower(), 0)

        if op == '>':  return left > right
        if op == '<':  return left < right
        if op == '>=': return left >= right
        if op == '<=': return left <= right
        if op == '==': return left == right
        if op == '!=': return left != right
        return False

    def _log_audit(self, action: str, details: str):
        self.audit_logs.append({
            'action': action,
            'details': details,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })


# Backward compatibility alias
BusinessWorkflowRuntime = AIWorkflowRuntime
