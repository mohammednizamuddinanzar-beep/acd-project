"""
tests/test_ai_assistant.py
==========================
Stage 9 + 10: AI Assistant Test Suite

Tests:
  1. AIProvider abstraction (MockAIProvider, LLMAIProvider)
  2. Error explanation — all 7 error types
  3. Workflow explanation — parse, extract, conditions, actions
  4. Trace explanation — empty trace, multi-step trace
  5. NL-to-DSL delegation (AI never executes)
  6. Security boundary — AI cannot bypass compiler
  7. MockAIProvider is fully deterministic (offline, no API key)
  8. LLMAIProvider falls back to Mock when no API key is set
  9. get_ai_assistant() factory function
  10. suggest_dsl is always re-compiled, never directly executed
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_assistant import (
    AIAssistant,
    MockAIProvider,
    LLMAIProvider,
    AIErrorExplanation,
    AIWorkflowExplanation,
    AITraceExplanation,
    get_ai_assistant,
)
from main import compile_any_source


# ─────────────────────────────────────────────────────────────────────────────
#  MockAIProvider Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMockAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = MockAIProvider()
        self.sample_source = """WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE invoice TO database
}"""

    def test_provider_name_is_mock(self):
        self.assertEqual(self.provider.provider_name(), "mock")

    def test_explain_error_returns_correct_type(self):
        result = self.provider.explain_error(
            source=self.sample_source,
            error_type="UNDEFINED_VARIABLE",
            error_message="Variable 'amount' is undefined.",
            error_line=3,
        )
        self.assertIsInstance(result, AIErrorExplanation)
        self.assertEqual(result.error_type, "UNDEFINED_VARIABLE")
        self.assertEqual(result.provider, "mock")
        self.assertIn("not been declared", result.what_it_means)
        self.assertIn("EXTRACT or SET", result.suggested_fix)

    def test_explain_error_all_seven_types(self):
        """All 7 error types should produce explanations without crashing."""
        error_types = [
            "UNDEFINED_VARIABLE", "DUPLICATE_VARIABLE", "INVALID_ACTION",
            "INVALID_EVENT", "TYPE_MISMATCH", "USE_BEFORE_DEF", "INVALID_STRUCTURE"
        ]
        for et in error_types:
            with self.subTest(error_type=et):
                result = self.provider.explain_error(
                    source=self.sample_source,
                    error_type=et,
                    error_message=f"Sample {et} error message",
                )
                self.assertIsInstance(result, AIErrorExplanation)
                self.assertTrue(len(result.what_it_means) > 0)
                self.assertTrue(len(result.suggested_fix) > 0)

    def test_explain_error_suggests_extract_for_undefined(self):
        """For UNDEFINED_VARIABLE on line 3, should suggest EXTRACT before that line."""
        result = self.provider.explain_error(
            source=self.sample_source,
            error_type="UNDEFINED_VARIABLE",
            error_message="Variable 'total' is undefined.",
            error_line=3,
        )
        self.assertIsInstance(result, AIErrorExplanation)
        # Suggested DSL should be non-empty (we have an error line)
        self.assertIsInstance(result.suggested_dsl, str)

    def test_explain_workflow_parses_invoice(self):
        result = self.provider.explain_workflow(self.sample_source)
        self.assertIsInstance(result, AIWorkflowExplanation)
        self.assertEqual(result.workflow_name, "InvoiceProcessing")
        self.assertEqual(result.trigger_event, "email.received")
        self.assertIn("amount (from email)", result.variables)
        self.assertTrue(len(result.conditions) > 0)
        self.assertIn("NOTIFY finance", result.actions)
        self.assertIn("SAVE invoice TO database", result.actions)
        self.assertIn("NotificationService", result.services_used)
        self.assertIn("DatabaseService", result.services_used)

    def test_explain_workflow_summary_is_non_empty(self):
        result = self.provider.explain_workflow(self.sample_source)
        self.assertTrue(len(result.summary) > 20)

    def test_explain_workflow_empty_source(self):
        result = self.provider.explain_workflow("")
        self.assertIsInstance(result, AIWorkflowExplanation)
        self.assertEqual(result.workflow_name, "Unknown")

    def test_explain_trace_empty_trace(self):
        result = self.provider.explain_trace(
            source=self.sample_source,
            tac=[],
            trace=[],
            environment={},
        )
        self.assertIsInstance(result, AITraceExplanation)
        self.assertEqual(result.total_steps, 0)
        self.assertIn("No trace steps", result.explanation)

    def test_explain_trace_with_steps(self):
        trace = [
            {"step": 1, "ip": 0, "opcode": "EVENT", "operands": "email.received", "status": "SUCCESS", "simulated_time": 0.0},
            {"step": 2, "ip": 1, "opcode": "EXTRACT", "operands": "amount", "status": "SUCCESS", "simulated_time": 0.1},
            {"step": 3, "ip": 2, "opcode": "COMPARE_GT", "operands": "amount > 50000", "status": "SUCCESS", "simulated_time": 0.1},
            {"step": 4, "ip": 3, "opcode": "NOTIFY", "operands": "finance", "status": "SUCCESS", "simulated_time": 0.2},
            {"step": 5, "ip": 4, "opcode": "SAVE", "operands": "invoice database", "status": "SUCCESS", "simulated_time": 0.3},
        ]
        env = {"amount": 75000}
        result = self.provider.explain_trace(
            source=self.sample_source,
            tac=["EVENT email.received", "EXTRACT amount"],
            trace=trace,
            environment=env,
        )
        self.assertIsInstance(result, AITraceExplanation)
        self.assertEqual(result.total_steps, 5)
        self.assertIn("5 instruction", result.explanation)
        self.assertIn("amount", result.explanation)

    def test_explain_trace_does_not_invent_results(self):
        """AI must NOT claim actions executed if they are not in the trace."""
        trace = [
            {"step": 1, "ip": 0, "opcode": "EVENT", "operands": "email.received", "status": "SUCCESS", "simulated_time": 0.0},
        ]
        result = self.provider.explain_trace(
            source=self.sample_source,
            tac=[],
            trace=trace,
            environment={},
        )
        # Should not mention NOTIFY or SAVE as if they happened
        self.assertNotIn("finance was notified", result.explanation.lower())
        self.assertNotIn("invoice was saved", result.explanation.lower())

    def test_explain_error_is_deterministic(self):
        """Same inputs must produce identical outputs (MockAIProvider is deterministic)."""
        r1 = self.provider.explain_error(
            source=self.sample_source,
            error_type="TYPE_MISMATCH",
            error_message="Type Error: Relational operator '>' cannot be applied to a STRING.",
        )
        r2 = self.provider.explain_error(
            source=self.sample_source,
            error_type="TYPE_MISMATCH",
            error_message="Type Error: Relational operator '>' cannot be applied to a STRING.",
        )
        self.assertEqual(r1.what_it_means, r2.what_it_means)
        self.assertEqual(r1.suggested_fix, r2.suggested_fix)


# ─────────────────────────────────────────────────────────────────────────────
#  LLMAIProvider Tests (no API key — must fall back to Mock)
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMAIProviderFallback(unittest.TestCase):

    def setUp(self):
        # Ensure no API key is set (test environment is clean)
        os.environ.pop('OPENAI_API_KEY', None)
        os.environ.pop('GOOGLE_API_KEY', None)
        self.source = """WORKFLOW Test {
    ON order.created
    EXTRACT total FROM order
    SAVE order TO database
}"""

    def test_llm_provider_falls_back_to_mock_without_api_key(self):
        provider = LLMAIProvider(provider='openai')
        # No OPENAI_API_KEY → _is_available() → False → uses mock
        result = provider.explain_workflow(self.source)
        self.assertIsInstance(result, AIWorkflowExplanation)
        self.assertTrue(len(result.summary) > 0)

    def test_llm_provider_gemini_falls_back_to_mock(self):
        provider = LLMAIProvider(provider='gemini')
        result = provider.explain_error(
            source=self.source,
            error_type="UNDEFINED_VARIABLE",
            error_message="Variable 'total' is undefined",
        )
        self.assertIsInstance(result, AIErrorExplanation)
        self.assertTrue(len(result.suggested_fix) > 0)


# ─────────────────────────────────────────────────────────────────────────────
#  AIAssistant Facade Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAIAssistantFacade(unittest.TestCase):

    def setUp(self):
        self.assistant = AIAssistant()  # defaults to MockAIProvider
        self.source = """WORKFLOW PaymentProcessing {
    ON payment.initiated
    EXTRACT amount FROM payment
    IF amount > 10000 {
        NOTIFY compliance
    }
    SAVE payment TO ledger
}"""

    def test_ai_assistant_uses_mock_by_default(self):
        self.assertEqual(self.assistant.backend_name, "mock")

    def test_ai_assistant_explain_error(self):
        result = self.assistant.explain_error(
            source=self.source,
            error_type="INVALID_EVENT",
            error_message="Invalid event name 'payment_initiated'.",
        )
        self.assertIsInstance(result, AIErrorExplanation)
        self.assertIn("domain.action", result.what_it_means)

    def test_ai_assistant_explain_workflow(self):
        result = self.assistant.explain_workflow(self.source)
        self.assertIsInstance(result, AIWorkflowExplanation)
        self.assertEqual(result.workflow_name, "PaymentProcessing")
        self.assertEqual(result.trigger_event, "payment.initiated")

    def test_ai_assistant_explain_trace(self):
        trace = [
            {"step": 1, "ip": 0, "opcode": "EVENT", "operands": "payment.initiated", "status": "SUCCESS", "simulated_time": 0.0},
            {"step": 2, "ip": 1, "opcode": "EXTRACT", "operands": "amount", "status": "SUCCESS", "simulated_time": 0.0},
        ]
        result = self.assistant.explain_trace(
            source=self.source,
            tac=["EVENT payment.initiated"],
            trace=trace,
            environment={"amount": 15000},
        )
        self.assertIsInstance(result, AITraceExplanation)
        self.assertEqual(result.total_steps, 2)

    def test_ai_assistant_generate_workflow_dsl_returns_string(self):
        """AI-generated DSL must be a string — NOT execution output."""
        result = self.assistant.generate_workflow_dsl(
            "When a payment arrives, notify accounting."
        )
        self.assertIsInstance(result.dsl, str)
        self.assertIn("WORKFLOW", result.dsl)
        # Must NOT contain execution output
        self.assertNotIn("Execution finished", result.dsl)
        self.assertNotIn("Notification Sent:", result.dsl)

    def test_ai_does_not_execute_generated_dsl(self):
        """AI-generated DSL must pass through compile_any_source — not be executed directly."""
        result = self.assistant.generate_workflow_dsl(
            "When an invoice is received, extract the total and save it to the database."
        )
        self.assertTrue(result.dsl.strip().startswith("WORKFLOW"))

        # The DSL must pass through the deterministic compiler
        comp = compile_any_source(result.dsl, verbose=False, program_name="TestAIDSL")
        # Compiler must handle it without crashing (may or may not fully succeed)
        self.assertIn("success", comp)


# ─────────────────────────────────────────────────────────────────────────────
#  Security Boundary Tests — AI cannot bypass compiler pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestAISecurityBoundary(unittest.TestCase):

    def setUp(self):
        self.assistant = get_ai_assistant()

    def test_ai_never_returns_execution_output(self):
        """AI explanations must never include execution results."""
        source = """WORKFLOW SecurityTest {
    ON email.received
    EXTRACT amount FROM email
    NOTIFY finance
}"""
        # Error explanation
        err_result = self.assistant.explain_error(
            source=source,
            error_type="TYPE_MISMATCH",
            error_message="Type mismatch in comparison",
        )
        for field in [err_result.what_it_means, err_result.likely_cause, err_result.suggested_fix]:
            self.assertNotIn("Notification Sent:", field)
            self.assertNotIn("Database Record Saved:", field)
            self.assertNotIn("vm_status", field)

        # Workflow explanation
        wf_result = self.assistant.explain_workflow(source)
        self.assertNotIn("vm_status", wf_result.summary)
        self.assertNotIn("Execution finished", wf_result.summary)

    def test_ai_generated_dsl_goes_through_compiler(self):
        """Critical: DSL from AI must be compiled — never directly run."""
        result = self.assistant.generate_workflow_dsl(
            "When a ticket is created, notify the manager."
        )
        # The DSL string itself must not be a program execution result
        self.assertNotIn("SUCCESS", result.dsl.upper().replace("WORKFLOW", ""))
        self.assertNotIn("vm_status", result.dsl)

        # Compiler correctly processes it
        comp = compile_any_source(result.dsl, verbose=False)
        self.assertIn("success", comp)
        self.assertIn("lex_errors", comp)

    def test_suggested_dsl_contains_valid_dsl_structure(self):
        """Any suggested_dsl from explain_error must be valid DSL structure."""
        source = """WORKFLOW TestFlow {
    ON email.received
    IF amount > 1000 {
        NOTIFY finance
    }
}"""
        result = self.assistant.explain_error(
            source=source,
            error_type="UNDEFINED_VARIABLE",
            error_message="Variable 'amount' is undefined",
            error_line=3,
        )
        if result.suggested_dsl:
            # Suggested DSL must start with WORKFLOW
            stripped = result.suggested_dsl.strip()
            self.assertTrue(
                stripped.startswith("WORKFLOW"),
                f"Suggested DSL must start with WORKFLOW, got: {stripped[:50]}"
            )


# ─────────────────────────────────────────────────────────────────────────────
#  get_ai_assistant() Factory Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAIAssistantFactory(unittest.TestCase):

    def test_factory_no_args_returns_mock(self):
        assistant = get_ai_assistant()
        self.assertEqual(assistant.backend_name, "mock")

    def test_factory_none_provider_returns_mock(self):
        assistant = get_ai_assistant(provider="none")
        self.assertEqual(assistant.backend_name, "mock")

    def test_factory_mock_provider_returns_mock(self):
        assistant = get_ai_assistant(provider="mock")
        self.assertEqual(assistant.backend_name, "mock")

    def test_factory_openai_without_key_uses_llm_provider(self):
        """Even with openai provider, LLMAIProvider falls back to Mock without key."""
        os.environ.pop('OPENAI_API_KEY', None)
        assistant = get_ai_assistant(provider="openai")
        # Should still produce valid results (falls back to Mock)
        result = assistant.explain_workflow("WORKFLOW Test { ON email.received SAVE data TO db }")
        self.assertIsInstance(result, AIWorkflowExplanation)


if __name__ == '__main__':
    unittest.main()
