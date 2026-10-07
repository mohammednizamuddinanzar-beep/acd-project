"""
============================================================
  Business Workflow DSL Compiler — Stage 9: AI Assistant
  ai_assistant.py
============================================================

Provides AI-assisted features around the deterministic compiler:

  1. Natural Language → Workflow DSL  (delegates to nl_to_dsl.py)
  2. AI Error Assistant                (explain + suggest fix)
  3. Workflow Explanation              (explain what a workflow does)
  4. Execution Trace Explanation       (explain why trace steps happened)

ARCHITECTURAL RULES
-------------------
  AI is an assistant ONLY. It NEVER:
    - Executes workflows directly
    - Bypasses the Lexer, Parser, Semantic Analyzer, IR, or VM
    - Makes real network/system calls (MockAIProvider ensures this)

  Every AI-generated DSL must pass through compile_any_source() before
  any execution can occur.

  Provider Abstraction
  --------------------
  AIProvider (abstract base)
    ├── MockAIProvider  — deterministic, offline, no API key needed
    └── LLMAIProvider   — optional real LLM (OpenAI / Gemini) via env vars

  Environment variables (same as llm_layer.py):
    AI_COMPILER_LLM_PROVIDER = openai | gemini | none
    OPENAI_API_KEY            = sk-...
    GOOGLE_API_KEY            = AI...

  The project MUST remain runnable without any API key.
  No secrets are committed to the repository.

Security Boundary
-----------------
  AI cannot call VM services directly.
  AI cannot execute commands or bypass compiler validation.
  AI output is always DSL text → compiler pipeline → VM.
============================================================
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# ─────────────────────────────────────────────────────────────────────────────
#  Result dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AIErrorExplanation:
    """Result of asking the AI assistant to explain a compiler error."""
    error_type: str
    error_message: str
    what_it_means: str
    likely_cause: str
    suggested_fix: str
    suggested_dsl: str = ""   # Non-empty only when AI proposes corrected DSL
    provider: str = "mock"
    confidence: str = "high"

    def to_text(self) -> str:
        lines = [
            f"Error Type     : {self.error_type}",
            f"Error Message  : {self.error_message}",
            "",
            f"What It Means  : {self.what_it_means}",
            f"Likely Cause   : {self.likely_cause}",
            f"Suggested Fix  : {self.suggested_fix}",
        ]
        if self.suggested_dsl:
            lines += [
                "",
                "── Suggested DSL Fix (must be re-compiled to validate) ──",
                self.suggested_dsl,
            ]
        return "\n".join(lines)


@dataclass
class AIWorkflowExplanation:
    """Result of asking the AI to explain a workflow."""
    workflow_name: str
    trigger_event: str
    variables: List[str]
    conditions: List[str]
    actions: List[str]
    services_used: List[str]
    retry_blocks: int
    parallel_blocks: int
    summary: str
    provider: str = "mock"

    def to_text(self) -> str:
        lines = [
            f"Workflow       : {self.workflow_name}",
            f"Trigger        : {self.trigger_event}",
            f"Variables      : {', '.join(self.variables) if self.variables else 'None'}",
            f"Conditions     : {', '.join(self.conditions) if self.conditions else 'None'}",
            f"Actions        : {', '.join(self.actions) if self.actions else 'None'}",
            f"Services Used  : {', '.join(self.services_used) if self.services_used else 'None'}",
            f"RETRY Blocks   : {self.retry_blocks}",
            f"PARALLEL Blocks: {self.parallel_blocks}",
            "",
            "── Summary ──",
            self.summary,
        ]
        return "\n".join(lines)


@dataclass
class AITraceExplanation:
    """Result of asking the AI to explain a VM execution trace."""
    total_steps: int
    executed_actions: List[str]
    skipped_actions: List[str]
    final_environment: Dict[str, Any]
    explanation: str
    provider: str = "mock"

    def to_text(self) -> str:
        lines = [
            f"VM Trace Steps : {self.total_steps}",
            f"Executed       : {', '.join(self.executed_actions) if self.executed_actions else 'None'}",
            f"Skipped        : {', '.join(self.skipped_actions) if self.skipped_actions else 'None'}",
            "",
            "── Trace Explanation ──",
            self.explanation,
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  Abstract AIProvider Interface
# ─────────────────────────────────────────────────────────────────────────────

class AIProvider(ABC):
    """Abstract base for AI provider implementations."""

    @abstractmethod
    def explain_error(
        self,
        source: str,
        error_type: str,
        error_message: str,
        error_line: Optional[int] = None,
    ) -> AIErrorExplanation:
        """Explain a compiler error and optionally suggest a corrected DSL."""

    @abstractmethod
    def explain_workflow(self, source: str) -> AIWorkflowExplanation:
        """Parse and explain what a workflow does in plain English."""

    @abstractmethod
    def explain_trace(
        self,
        source: str,
        tac: List[str],
        trace: List[Dict[str, Any]],
        environment: Dict[str, Any],
    ) -> AITraceExplanation:
        """Explain why a VM execution trace followed its path."""

    def provider_name(self) -> str:
        return "abstract"


# ─────────────────────────────────────────────────────────────────────────────
#  MockAIProvider — deterministic, offline, no API key required
# ─────────────────────────────────────────────────────────────────────────────

class MockAIProvider(AIProvider):
    """
    Deterministic mock AI provider.

    Returns rule-based, pre-computed responses for all AI features.
    Allows full automated testing without any network access or API key.
    Responses are keyed on error_type and source patterns.

    SECURITY: This provider never makes external network calls.
    """

    # Pre-computed error explanations keyed by error_type
    _ERROR_EXPLANATIONS: Dict[str, Dict[str, str]] = {
        "UNDEFINED_VARIABLE": {
            "what": "The workflow references a variable that has not been declared or extracted.",
            "cause": "You may have misspelled the variable name, or forgotten an EXTRACT or SET statement before using it.",
            "fix": "Use EXTRACT or SET before using the variable. Example: Add 'EXTRACT <variable> FROM <source>' or 'SET <variable> = <value>' before using the variable.",
        },
        "DUPLICATE_VARIABLE": {
            "what": "A variable name has been declared more than once in the same scope.",
            "cause": "The same variable was defined via EXTRACT or SET twice in the same workflow scope.",
            "fix": "Remove the duplicate declaration. Each variable should be defined exactly once.",
        },
        "INVALID_ACTION": {
            "what": "The keyword used is not a recognized Business Workflow DSL action.",
            "cause": "The action may be a typo, or it belongs to a different DSL or programming language.",
            "fix": "Replace the invalid action with one of: ON, EXTRACT, SET, VALIDATE, IF, ELSE, CALL, SAVE, NOTIFY, RETRY, WAIT, PARALLEL, LOG.",
        },
        "INVALID_EVENT": {
            "what": "The event name in the ON statement does not follow the required 'domain.action' format.",
            "cause": "Event names must use the pattern 'domain.action' such as 'email.received' or 'order.created'.",
            "fix": "Use a valid event format: ON email.received, ON order.created, ON ticket.opened, etc.",
        },
        "TYPE_MISMATCH": {
            "what": "A value of the wrong type was used in an assignment or comparison.",
            "cause": "A string literal was used where a number is expected, or a relational operator was applied to string values.",
            "fix": "Ensure numeric variables are compared with numeric values. Use '==' for string equality, not '>' or '<'.",
        },
        "USE_BEFORE_DEF": {
            "what": "A variable is used before it has been defined in the workflow.",
            "cause": "The EXTRACT or SET statement defining this variable appears after the line where it is used.",
            "fix": "Move the variable definition (EXTRACT or SET) above the line where it is first used.",
        },
        "INVALID_STRUCTURE": {
            "what": "The workflow structure is malformed — a required element is missing or misplaced.",
            "cause": "Common causes: missing WORKFLOW header, missing ON trigger, unclosed braces, or statements outside the workflow block.",
            "fix": "Ensure the workflow starts with 'WORKFLOW Name {', contains exactly one 'ON event' trigger, and all braces are balanced.",
        },
    }

    def explain_error(
        self,
        source: str,
        error_type: str,
        error_message: str,
        error_line: Optional[int] = None,
    ) -> AIErrorExplanation:
        info = self._ERROR_EXPLANATIONS.get(error_type, {
            "what": f"A compiler error of type {error_type} was detected.",
            "cause": "See the error message for details.",
            "fix": "Review the flagged line and correct the issue according to the DSL grammar.",
        })

        # Extract variable name from error message for more targeted suggestions
        var_match = re.search(r"'([^']+)'", error_message)
        var_name = var_match.group(1) if var_match else "the variable"

        # Build optional suggested DSL for undefined/duplicate variable errors
        suggested_dsl = ""
        source_lines = source.splitlines()
        if error_type == "UNDEFINED_VARIABLE" and error_line:
            # Suggest adding an EXTRACT statement before the error line
            src_domain = "email"
            m_on = re.search(r"ON\s+(\w+)\.", source, re.I)
            if m_on:
                src_domain = m_on.group(1).lower()
            fix_line = f"    EXTRACT {var_name} FROM {src_domain}"
            if error_line > 1:
                before = source_lines[:error_line - 1]
                after = source_lines[error_line - 1:]
                suggested_dsl = "\n".join(before + [fix_line] + after)

        return AIErrorExplanation(
            error_type=error_type,
            error_message=error_message,
            what_it_means=info["what"],
            likely_cause=info["cause"].replace("the variable", f"'{var_name}'"),
            suggested_fix=info["fix"],
            suggested_dsl=suggested_dsl,
            provider="mock",
            confidence="high",
        )

    def explain_workflow(self, source: str) -> AIWorkflowExplanation:
        lines = source.splitlines()

        # Extract key workflow elements
        wf_name = ""
        trigger = ""
        variables = []
        conditions = []
        actions = []
        services = []
        retry_count = 0
        parallel_count = 0

        for line in lines:
            stripped = line.strip()
            m = re.match(r"WORKFLOW\s+(\w+)", stripped, re.I)
            if m:
                wf_name = m.group(1)
            m = re.match(r"ON\s+(\S+)", stripped, re.I)
            if m:
                trigger = m.group(1)
            m = re.match(r"EXTRACT\s+(\w+)\s+FROM\s+(\w+)", stripped, re.I)
            if m:
                variables.append(f"{m.group(1)} (from {m.group(2)})")
            m = re.match(r"SET\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(.+)", stripped, re.I)
            if m:
                variables.append(f"{m.group(1)} = {m.group(2).strip()}")
            m = re.match(r"IF\s+(.+?)\s*\{?$", stripped, re.I)
            if m:
                conditions.append(m.group(1).strip().rstrip('{').strip())
            m = re.match(r"NOTIFY\s+(\S+)", stripped, re.I)
            if m:
                actions.append(f"NOTIFY {m.group(1)}")
                services.append("NotificationService")
            m = re.match(r"SAVE\s+(\w+)\s+TO\s+(\w+)", stripped, re.I)
            if m:
                actions.append(f"SAVE {m.group(1)} TO {m.group(2)}")
                services.append("DatabaseService")
            m = re.match(r"CALL\s+(\w+)", stripped, re.I)
            if m:
                actions.append(f"CALL {m.group(1)}")
                services.append("APIService")
            m = re.match(r"VALIDATE\s+(\w+)", stripped, re.I)
            if m:
                actions.append(f"VALIDATE {m.group(1)}")
            if re.match(r"RETRY", stripped, re.I):
                retry_count += 1
            if re.match(r"PARALLEL", stripped, re.I):
                parallel_count += 1

        services = list(dict.fromkeys(services))  # deduplicate

        # Build natural language summary
        parts = []
        if trigger:
            parts.append(f"This workflow is triggered when '{trigger}' occurs.")
        if variables:
            parts.append(f"It captures the following data: {', '.join(variables[:4])}.")
        if conditions:
            parts.append(f"It conditionally executes based on: {', '.join(conditions[:3])}.")
        if actions:
            parts.append(f"Its main actions are: {', '.join(actions[:5])}.")
        if services:
            parts.append(f"It uses these services: {', '.join(services)}.")
        if retry_count:
            parts.append(f"It includes {retry_count} RETRY block(s) for resilient service calls.")
        if parallel_count:
            parts.append(f"It uses {parallel_count} PARALLEL block(s) for concurrent execution.")

        summary = " ".join(parts) if parts else "This workflow has no recognized statements."

        return AIWorkflowExplanation(
            workflow_name=wf_name or "Unknown",
            trigger_event=trigger or "Unknown",
            variables=variables,
            conditions=conditions,
            actions=actions,
            services_used=services,
            retry_blocks=retry_count,
            parallel_blocks=parallel_count,
            summary=summary,
            provider="mock",
        )

    def explain_trace(
        self,
        source: str,
        tac: List[str],
        trace: List[Dict[str, Any]],
        environment: Dict[str, Any],
    ) -> AITraceExplanation:
        if not trace:
            return AITraceExplanation(
                total_steps=0,
                executed_actions=[],
                skipped_actions=[],
                final_environment=environment,
                explanation="No trace steps were recorded. The workflow may not have produced any IR instructions.",
                provider="mock",
            )

        executed = []
        skipped = []
        for step in trace:
            op = step.get("opcode", "")
            operands = step.get("operands", "")
            status = step.get("status", "SUCCESS")
            label = f"{op} {operands}".strip()
            if status == "SUCCESS":
                executed.append(label)
            else:
                skipped.append(label)

        # Build explanation from trace data (does NOT invent results)
        parts = [f"The VM executed {len(trace)} instruction(s) total."]

        notify_steps = [s for s in trace if s.get("opcode") == "NOTIFY"]
        save_steps = [s for s in trace if s.get("opcode") == "SAVE"]
        call_steps = [s for s in trace if s.get("opcode") == "CALL"]
        jump_false = [s for s in trace if s.get("opcode") in ("JUMP_IF_FALSE", "JUMP_IF_TRUE")]
        compare_steps = [s for s in trace if "COMPARE" in s.get("opcode", "")]

        if compare_steps:
            parts.append(f"Conditional checks were evaluated at step(s): {', '.join(str(s['step']) for s in compare_steps)}.")
        if jump_false:
            parts.append(f"Conditional branches were taken at step(s): {', '.join(str(s['step']) for s in jump_false)}.")
        if notify_steps:
            targets = [s.get("operands", "") for s in notify_steps]
            parts.append(f"Notifications were sent to: {', '.join(t for t in targets if t)}.")
        if save_steps:
            entities = [s.get("operands", "") for s in save_steps]
            parts.append(f"Records were saved to: {', '.join(e for e in entities if e)}.")
        if call_steps:
            services = [s.get("operands", "") for s in call_steps]
            parts.append(f"API services were called: {', '.join(s for s in services if s)}.")

        if environment:
            env_str = ", ".join(f"{k}={v!r}" for k, v in list(environment.items())[:6])
            parts.append(f"Final runtime state: {{{env_str}}}.")

        return AITraceExplanation(
            total_steps=len(trace),
            executed_actions=executed[:10],
            skipped_actions=skipped[:5],
            final_environment=environment,
            explanation=" ".join(parts),
            provider="mock",
        )

    def provider_name(self) -> str:
        return "mock"


# ─────────────────────────────────────────────────────────────────────────────
#  LLMAIProvider — optional real LLM (no API key required for base operation)
# ─────────────────────────────────────────────────────────────────────────────

class LLMAIProvider(AIProvider):
    """
    Optional LLM-backed AI provider.

    Falls back to MockAIProvider if no API key is configured.
    Reads provider/model from environment variables (same as llm_layer.py).

    SECURITY: Never commits API keys. Keys only come from environment variables.
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self._provider_name_str = (provider or os.environ.get("AI_COMPILER_LLM_PROVIDER", "none")).lower()
        self._model = model or os.environ.get("AI_COMPILER_LLM_MODEL", "")
        self._mock = MockAIProvider()  # fallback

    def _is_available(self) -> bool:
        if self._provider_name_str == "openai":
            return bool(os.environ.get("OPENAI_API_KEY"))
        if self._provider_name_str == "gemini":
            return bool(os.environ.get("GOOGLE_API_KEY"))
        return False

    def explain_error(self, source, error_type, error_message, error_line=None):
        if not self._is_available():
            return self._mock.explain_error(source, error_type, error_message, error_line)
        # Real LLM call — kept simple, falls through to mock on any failure
        try:
            prompt = self._build_error_prompt(source, error_type, error_message, error_line)
            response = self._call_llm(prompt)
            return self._parse_error_response(response, error_type, error_message)
        except Exception:
            return self._mock.explain_error(source, error_type, error_message, error_line)

    def explain_workflow(self, source):
        if not self._is_available():
            return self._mock.explain_workflow(source)
        try:
            prompt = f"Explain this Business Workflow DSL in plain English:\n\n{source}"
            response = self._call_llm(prompt)
            base = self._mock.explain_workflow(source)
            base.summary = response.strip() or base.summary
            base.provider = self._provider_name_str
            return base
        except Exception:
            return self._mock.explain_workflow(source)

    def explain_trace(self, source, tac, trace, environment):
        if not self._is_available():
            return self._mock.explain_trace(source, tac, trace, environment)
        try:
            trace_str = "\n".join(f"Step {s['step']}: {s['opcode']} {s.get('operands', '')}" for s in trace[:20])
            prompt = f"Explain this workflow execution trace:\n\nSource:\n{source}\n\nTrace:\n{trace_str}\n\nEnvironment: {environment}"
            response = self._call_llm(prompt)
            base = self._mock.explain_trace(source, tac, trace, environment)
            base.explanation = response.strip() or base.explanation
            base.provider = self._provider_name_str
            return base
        except Exception:
            return self._mock.explain_trace(source, tac, trace, environment)

    def _build_error_prompt(self, source, error_type, error_message, error_line):
        return (
            f"You are a Business Workflow DSL compiler assistant.\n"
            f"A compiler error occurred:\n"
            f"  Error type: {error_type}\n"
            f"  Message: {error_message}\n"
            f"  Line: {error_line}\n\n"
            f"Source code:\n{source}\n\n"
            f"Respond in this format:\n"
            f"WHAT: <what the error means>\n"
            f"CAUSE: <likely cause>\n"
            f"FIX: <how to fix it>\n"
            f"SUGGESTED_DSL: <corrected DSL or 'none'>"
        )

    def _parse_error_response(self, response, error_type, error_message):
        what  = re.search(r"WHAT:\s*(.+)", response)
        cause = re.search(r"CAUSE:\s*(.+)", response)
        fix   = re.search(r"FIX:\s*(.+)", response)
        dsl   = re.search(r"SUGGESTED_DSL:\s*(.+)", response, re.DOTALL)
        suggested_dsl = dsl.group(1).strip() if dsl else ""
        if suggested_dsl.lower() == "none":
            suggested_dsl = ""
        return AIErrorExplanation(
            error_type=error_type,
            error_message=error_message,
            what_it_means=what.group(1).strip() if what else "See error message.",
            likely_cause=cause.group(1).strip() if cause else "Review the flagged line.",
            suggested_fix=fix.group(1).strip() if fix else "Correct the issue per the DSL grammar.",
            suggested_dsl=suggested_dsl,
            provider=self._provider_name_str,
            confidence="medium",
        )

    def _call_llm(self, prompt: str) -> str:
        """Make a real LLM API call. Raises on failure."""
        if self._provider_name_str == "openai":
            import openai
            client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model=self._model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        if self._provider_name_str == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            model = genai.GenerativeModel(self._model or "gemini-1.5-flash")
            resp = model.generate_content(prompt)
            return resp.text or ""
        raise ValueError(f"Unknown LLM provider: {self._provider_name_str}")

    def provider_name(self) -> str:
        return self._provider_name_str


# ─────────────────────────────────────────────────────────────────────────────
#  AIAssistant — the public-facing interface
# ─────────────────────────────────────────────────────────────────────────────

class AIAssistant:
    """
    Public facade for all Stage 9 AI assistance features.

    The AIAssistant:
      - Never executes workflows
      - Never bypasses the compiler pipeline
      - Works without an API key (uses MockAIProvider by default)
      - Optionally upgrades to LLMAIProvider when credentials are available
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        effective_provider = provider or os.environ.get("AI_COMPILER_LLM_PROVIDER", "none")
        if effective_provider in ("none", "mock", ""):
            self._backend: AIProvider = MockAIProvider()
        else:
            self._backend = LLMAIProvider(provider=effective_provider, model=model)

    @property
    def backend_name(self) -> str:
        return self._backend.provider_name()

    def generate_workflow_dsl(self, nl_description: str, **kwargs):
        """
        Convert a natural language description to Workflow DSL.
        Delegates to nl_to_dsl.py — the generated DSL is NOT executed here.
        The caller must pass the returned DSL through compile_any_source().
        """
        from nl_to_dsl import nl_to_dsl
        return nl_to_dsl(
            nl_description,
            provider=kwargs.get("llm_provider"),
            model=kwargs.get("llm_model"),
            verbose=False,
        )

    def explain_error(
        self,
        source: str,
        error_type: str,
        error_message: str,
        error_line: Optional[int] = None,
    ) -> AIErrorExplanation:
        """
        Explain a compiler error in plain English and optionally suggest a fix.

        IMPORTANT: If a suggested_dsl is provided, it MUST be compiled
        through compile_any_source() before any execution is attempted.
        """
        return self._backend.explain_error(source, error_type, error_message, error_line)

    def explain_workflow(self, source: str) -> AIWorkflowExplanation:
        """
        Explain what a workflow does in plain English.
        Based on the DSL source — does not execute the workflow.
        """
        return self._backend.explain_workflow(source)

    def explain_trace(
        self,
        source: str,
        tac: List[str],
        trace: List[Dict[str, Any]],
        environment: Dict[str, Any],
    ) -> AITraceExplanation:
        """
        Explain why a VM execution trace followed the path it did.

        IMPORTANT: The AI must NOT invent execution results.
        If the trace says an action did not execute, the explanation
        must not claim it did.
        """
        return self._backend.explain_trace(source, tac, trace, environment)


# ─────────────────────────────────────────────────────────────────────────────
#  Factory function
# ─────────────────────────────────────────────────────────────────────────────

def get_ai_assistant(provider: Optional[str] = None, model: Optional[str] = None) -> AIAssistant:
    """Create an AIAssistant with the appropriate provider backend."""
    return AIAssistant(provider=provider, model=model)
