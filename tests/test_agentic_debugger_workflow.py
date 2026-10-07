"""
test_agentic_debugger_workflow.py — Test Suite for Business Workflow Agentic Debugger
======================================================================================

Validates that the Agentic Debugger diagnoses:
1. Undefined variables
2. Invalid workflow actions
3. Invalid event dependencies
4. Type errors
5. Invalid execution order
6. Unreachable actions
7. Missing required workflow steps

Also verifies:
- The debugger analyzes compiler artifacts without modifying compiler state.
- Deterministic debugging is the default mode (zero API keys needed).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agentic_debugger import (
    CompilerAgent,
    CAT_UNDEFINED_VARS,
    CAT_INVALID_ACTIONS,
    CAT_INVALID_EVENT_DEPS,
    CAT_TYPE_ERRORS,
    CAT_INVALID_EXEC_ORDER,
    CAT_UNREACHABLE_ACTIONS,
    CAT_MISSING_STEPS,
)
from agent_orchestrator import build_agent_report
from main import compile_any_source


class TestBusinessWorkflowAgenticDebugger(unittest.TestCase):

    def setUp(self):
        self.agent = CompilerAgent()

    # ──────────────────────────────────────────────────────────
    # 1. Undefined variables
    # ──────────────────────────────────────────────────────────
    def test_diagnose_undefined_variable(self):
        source = """WORKFLOW UndefinedVarWF {
    ON email.received
    IF score > 90 {
        NOTIFY security
    }
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)
        
        categories = [f.category for f in report.findings]
        self.assertIn(CAT_UNDEFINED_VARS, categories)
        finding = next(f for f in report.findings if f.category == CAT_UNDEFINED_VARS)
        self.assertIn("score", finding.message.lower())
        self.assertEqual(report.status, "blocked")

    # ──────────────────────────────────────────────────────────
    # 2. Invalid workflow actions
    # ──────────────────────────────────────────────────────────
    def test_diagnose_invalid_workflow_action(self):
        source = """WORKFLOW InvalidActionWF {
    ON email.received
    PUBLISH invoice TO cloud
    SAVE invoice TO database
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_INVALID_ACTIONS, categories)
        finding = next(f for f in report.findings if f.category == CAT_INVALID_ACTIONS)
        self.assertIn("publish", finding.message.lower())

    # ──────────────────────────────────────────────────────────
    # 3. Invalid event dependencies
    # ──────────────────────────────────────────────────────────
    def test_diagnose_invalid_event_dependencies(self):
        # Trigger is email.received, but extraction tries to pull from unknown entity 'sms'
        source = """WORKFLOW EventDepWF {
    ON email.received
    EXTRACT amount FROM sms
    NOTIFY finance
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_INVALID_EVENT_DEPS, categories)
        finding = next(f for f in report.findings if f.category == CAT_INVALID_EVENT_DEPS)
        self.assertIn("sms", finding.message.lower())

    def test_diagnose_malformed_event_name(self):
        source = """WORKFLOW BadEventWF {
    ON emailreceived
    EXTRACT amount FROM email
    NOTIFY finance
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_INVALID_EVENT_DEPS, categories)

    # ──────────────────────────────────────────────────────────
    # 4. Type errors
    # ──────────────────────────────────────────────────────────
    def test_diagnose_type_errors(self):
        source = """WORKFLOW TypeMismatchWF {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 'fifty_thousand' {
        NOTIFY finance
    }
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_TYPE_ERRORS, categories)
        finding = next(f for f in report.findings if f.category == CAT_TYPE_ERRORS)
        self.assertIn("fifty_thousand", finding.message.lower())

    # ──────────────────────────────────────────────────────────
    # 5. Invalid execution order
    # ────────────────────────────────----------------──────────
    def test_diagnose_use_before_def_order(self):
        source = """WORKFLOW OrderWF {
    ON email.received
    IF amount > 50000 {
        NOTIFY finance
    }
    EXTRACT amount FROM email
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_INVALID_EXEC_ORDER, categories)

    def test_diagnose_actions_before_on_order(self):
        source = """WORKFLOW ActionBeforeOnWF {
    NOTIFY admin
    ON email.received
    SAVE invoice TO database
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertTrue(CAT_INVALID_EXEC_ORDER in categories or CAT_INVALID_EVENT_DEPS in categories)

    # ──────────────────────────────────────────────────────────
    # 6. Unreachable actions
    # ──────────────────────────────────────────────────────────
    def test_diagnose_unreachable_actions(self):
        # Statically impossible condition: 0 > 100
        source = """WORKFLOW UnreachableWF {
    ON email.received
    EXTRACT amount FROM email
    IF 0 > 100 {
        NOTIFY finance
    }
    SAVE email TO database
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_UNREACHABLE_ACTIONS, categories)
        finding = next(f for f in report.findings if f.category == CAT_UNREACHABLE_ACTIONS)
        self.assertEqual(finding.severity, "warning")

    # ──────────────────────────────────────────────────────────
    # 7. Missing required workflow steps
    # ──────────────────────────────────────────────────────────
    def test_diagnose_missing_trigger_event(self):
        source = """WORKFLOW NoTriggerWF {
    EXTRACT amount FROM email
    SAVE email TO database
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_MISSING_STEPS, categories)

    def test_diagnose_missing_outcome_steps(self):
        # Workflow extracts amount but has no NOTIFY, SAVE, or LOG
        source = """WORKFLOW NoOutcomeWF {
    ON email.received
    EXTRACT amount FROM email
}"""
        results = compile_any_source(source, verbose=False)
        report = self.agent.analyze(source, results)

        categories = [f.category for f in report.findings]
        self.assertIn(CAT_MISSING_STEPS, categories)
        finding = next(f for f in report.findings if f.category == CAT_MISSING_STEPS)
        self.assertIn("outcome", finding.message.lower())

    # ──────────────────────────────────────────────────────────
    # 8. Valid workflow & State Immutability
    # ──────────────────────────────────────────────────────────
    def test_valid_production_ready_workflow(self):
        source = """WORKFLOW CleanInvoiceWF {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE email TO database
}"""
        results = compile_any_source(source, verbose=False)
        self.assertTrue(results['success'])
        
        # Verify compiler artifacts before agent review
        ast_before = results['ast']
        tac_count_before = len(results['tac'])

        # Run agent through orchestrator
        adapter = build_agent_report(source, results, backend="deterministic")
        report_dict = adapter.to_dict()

        # Check production readiness
        self.assertEqual(report_dict['status'], "production-ready")
        self.assertGreaterEqual(report_dict['validation_score'], 85)
        self.assertTrue(len(report_dict['workflow_graph']) >= 3)

        # Immutability check: compiler results must remain unmutated
        self.assertEqual(results['ast'], ast_before)
        self.assertEqual(len(results['tac']), tac_count_before)


if __name__ == '__main__':
    unittest.main()
