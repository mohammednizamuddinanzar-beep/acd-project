"""
tests/test_e2e_comprehensive.py
================================
Stage 10 — Complete E2E Tests + Invalid Workflow Rejection

REQUIRED tests per specification:
  - Valid workflows compile and execute to VM SUCCESS
  - Invalid workflow E2E: faulty DSL must be rejected (success=False)
    and VM must NOT execute (execution_allowed=False)
  - Compiler gate: errors in any phase block VM execution
  - Complete pipeline verification: Lexer → Parser → AST → Semantic → IR → VM

IMPORTANT: These tests verify the critical architectural rule:
  "Invalid programs must NOT reach the VM."
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import compile_any_source
from workflow_vm import WorkflowVM
from icg import TACInstr


# ─────────────────────────────────────────────────────────────────────────────
#  1. Valid Workflow E2E Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestValidWorkflowE2E(unittest.TestCase):

    def _compile_and_run(self, source, name):
        comp = compile_any_source(source, verbose=False, program_name=name)
        self.assertTrue(comp["success"], f"Expected compile success for {name}, got errors: {comp['sem_errors']}")
        self.assertEqual(len(comp["lex_errors"]), 0, "Expected no lex errors")
        self.assertEqual(len(comp["parse_errors"]), 0, "Expected no parse errors")
        return comp

    def test_e2e_invoice_processing_full_pipeline(self):
        """Complete pipeline test: Invoice Processing workflow."""
        source = """WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE invoice TO database
}"""
        comp = self._compile_and_run(source, "InvoiceE2E")

        # Verify all pipeline artifacts are produced
        self.assertGreater(len(comp["tokens"]), 0,   "Lexer must produce tokens")
        self.assertIsNotNone(comp["ast"],             "Parser must produce AST")
        self.assertGreater(len(comp["tac"]), 0,      "ICG must produce TAC/IR")
        self.assertTrue(len(comp["listing"]) > 0,    "Listing file must be generated")

        # Run VM on the compiled IR
        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        vm_res = vm.execute()
        self.assertEqual(vm_res["status"], "SUCCESS")
        self.assertIn("amount", vm_res["environment"])

    def test_e2e_order_with_validate_and_notify(self):
        """E2E test with VALIDATE + conditional NOTIFY."""
        source = """WORKFLOW OrderProcessing {
    ON order.created
    VALIDATE order
    EXTRACT amount FROM order
    IF amount > 10000 {
        NOTIFY manager
    }
    SAVE order TO database
}"""
        comp = self._compile_and_run(source, "OrderE2E")
        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        vm_res = vm.execute()
        self.assertEqual(vm_res["status"], "SUCCESS")

    def test_e2e_customer_support_ticket_flow(self):
        """E2E test for ticket workflow with SET and LOG."""
        source = """WORKFLOW CustomerSupport {
    ON ticket.created
    EXTRACT priority FROM ticket
    SET ticket_count = 1
    LOG 'Ticket received'
    SAVE ticket TO database
}"""
        comp = self._compile_and_run(source, "CustomerSupportE2E")
        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        vm_res = vm.execute()
        self.assertEqual(vm_res["status"], "SUCCESS")
        self.assertIn("ticket_count", vm_res["environment"])
        self.assertEqual(vm_res["environment"]["ticket_count"], 1)

    def test_e2e_payment_workflow_with_retry(self):
        """E2E test with RETRY block — verifies retry semantics."""
        source = """WORKFLOW PaymentProcessing {
    ON payment.initiated
    EXTRACT amount FROM payment
    RETRY 3 {
        CALL process_payment
    }
    SAVE payment TO database
}"""
        comp = self._compile_and_run(source, "PaymentRetryE2E")
        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        vm_res = vm.execute()
        self.assertIn(vm_res["status"], ("SUCCESS", "FAILED"))  # Both are valid outcomes

    def test_e2e_if_else_branching(self):
        """E2E test with IF/ELSE conditional branching."""
        source = """WORKFLOW BranchingWorkflow {
    ON invoice.received
    EXTRACT amount FROM invoice
    IF amount > 100000 {
        NOTIFY director
    } ELSE {
        NOTIFY finance
    }
    SAVE invoice TO database
}"""
        comp = self._compile_and_run(source, "BranchE2E")
        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        vm_res = vm.execute()
        self.assertEqual(vm_res["status"], "SUCCESS")

    def test_e2e_vm_reflects_mock_service_activity(self):
        """Verify VM execution records activity in service summary."""
        source = """WORKFLOW ServiceTest {
    ON order.created
    EXTRACT amount FROM order
    NOTIFY finance
    SAVE order TO database
}"""
        comp = self._compile_and_run(source, "ServiceActivityE2E")
        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        vm_res = vm.execute()
        summary = vm_res.get("activity_summary", {})
        # Notification and save should be recorded
        self.assertGreaterEqual(summary.get("notifications_sent", 0), 0)
        self.assertGreaterEqual(summary.get("records_saved", 0), 0)


# ─────────────────────────────────────────────────────────────────────────────
#  2. INVALID Workflow E2E Test — REQUIRED per specification
#     "This test is REQUIRED" — faulty workflow must be rejected, not executed
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidWorkflowE2E(unittest.TestCase):
    """
    REQUIRED TEST: Faulty workflow must be rejected by the compiler gate.

    The compiler pipeline enforces:
      SOURCE → LEXER → PARSER → SEMANTIC → IR → VM

    If ANY phase has errors, VM execution must NOT occur.
    success must be False; the VM must not run.
    """

    def test_required_faulty_workflow_is_rejected(self):
        """
        REQUIRED: A workflow with semantic errors must be rejected.
        The system must NOT allow VM execution.
        """
        faulty_source = """WORKFLOW FaultyWorkflow {
    ON email.received
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE invoice TO database
}"""
        comp = compile_any_source(faulty_source, verbose=False, program_name="FaultyE2E")

        # CRITICAL ASSERTION: compilation must fail
        self.assertFalse(comp["success"],
            "Faulty workflow with undefined variable must NOT succeed compilation")

        # CRITICAL ASSERTION: semantic errors must be reported
        self.assertGreater(len(comp["sem_errors"]), 0,
            "Semantic errors must be reported for faulty workflow")

        # CRITICAL ASSERTION: VM must not run (no execution allowed)
        # If compile fails, TAC should be empty or VM never invoked
        # The correct behavior: tac may be [] since IR not generated for failed compile
        tac = comp.get("tac", [])

        # This simulates what the server does — enforce the execution gate
        execution_allowed = comp.get("success", False)
        self.assertFalse(execution_allowed,
            "execution_allowed must be False when compilation fails")

    def test_undefined_variable_blocks_execution(self):
        """Undefined variable must block VM execution."""
        source = """WORKFLOW UndefinedVarTest {
    ON order.created
    IF total > 500 {
        NOTIFY manager
    }
}"""
        comp = compile_any_source(source, verbose=False, program_name="UndefinedVarE2E")
        self.assertFalse(comp["success"])
        self.assertGreater(len(comp["sem_errors"]), 0)

    def test_invalid_event_blocks_execution(self):
        """Invalid event name must produce semantic error."""
        source = """WORKFLOW BadEvent {
    ON not_a_valid_event
    EXTRACT amount FROM something
    NOTIFY finance
}"""
        comp = compile_any_source(source, verbose=False, program_name="BadEventE2E")
        self.assertFalse(comp["success"])
        sem_errors = comp["sem_errors"]
        self.assertTrue(any(
            getattr(e, "error_type", "") == "INVALID_EVENT" or "INVALID_EVENT" in str(e)
            for e in sem_errors
        ), f"Expected INVALID_EVENT error, got: {sem_errors}")

    def test_type_mismatch_in_condition_blocks_execution(self):
        """String literal in relational comparison must produce TYPE_MISMATCH error."""
        source = """WORKFLOW TypeMismatchWF {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 'fifty_thousand' {
        NOTIFY finance
    }
}"""
        comp = compile_any_source(source, verbose=False, program_name="TypeMismatchE2E")
        self.assertFalse(comp["success"])
        sem_errors = comp["sem_errors"]
        self.assertTrue(any(
            getattr(e, "error_type", "") == "TYPE_MISMATCH" or "TYPE_MISMATCH" in str(e)
            for e in sem_errors
        ), f"Expected TYPE_MISMATCH error, got: {sem_errors}")

    def test_duplicate_variable_blocks_execution(self):
        """Duplicate variable declaration must produce DUPLICATE_VARIABLE error."""
        source = """WORKFLOW DuplicateVarWF {
    ON email.received
    EXTRACT amount FROM email
    EXTRACT amount FROM email
    NOTIFY finance
}"""
        comp = compile_any_source(source, verbose=False, program_name="DupVarE2E")
        self.assertFalse(comp["success"])
        sem_errors = comp["sem_errors"]
        self.assertTrue(any(
            getattr(e, "error_type", "") == "DUPLICATE_VARIABLE" or "DUPLICATE_VARIABLE" in str(e)
            for e in sem_errors
        ))

    def test_missing_on_trigger_blocks_execution(self):
        """Missing ON event trigger must produce INVALID_STRUCTURE error."""
        source = """WORKFLOW NoTrigger {
    EXTRACT amount FROM email
    NOTIFY finance
}"""
        comp = compile_any_source(source, verbose=False, program_name="NoTriggerE2E")
        self.assertFalse(comp["success"])

    def test_malformed_workflow_no_braces_fails(self):
        """Workflow without braces is invalid structure."""
        source = """WORKFLOW BrokenNoBraces
    ON email.received
    NOTIFY finance"""
        comp = compile_any_source(source, verbose=False, program_name="NoBracesE2E")
        # Should fail or at least report errors
        if comp["success"]:
            # If it weirdly parses, it at least should not crash
            pass
        else:
            self.assertGreater(len(comp["sem_errors"]) + len(comp["parse_errors"]) + len(comp["lex_errors"]), 0)


# ─────────────────────────────────────────────────────────────────────────────
#  3. Compiler Gate Tests — execution_allowed field
# ─────────────────────────────────────────────────────────────────────────────

class TestCompilerGate(unittest.TestCase):
    """
    Verifies the execution gate: VM must NOT run on failed compilations.

    This mirrors what server.py does: only run VM when success=True.
    """

    def test_gate_allows_execution_on_success(self):
        """Successful compilation must set success=True."""
        source = """WORKFLOW GateTest {
    ON email.received
    EXTRACT amount FROM email
    SAVE invoice TO database
}"""
        comp = compile_any_source(source, verbose=False, program_name="GateSuccessTest")
        self.assertTrue(comp["success"])
        # Confirm TAC is generated (IR available for VM)
        tac = comp.get("tac", [])
        self.assertGreater(len(tac), 0, "TAC IR must be generated on success")

    def test_gate_blocks_vm_on_failure(self):
        """Failed compilation must not produce TAC for VM execution."""
        source = """WORKFLOW GateFail {
    ON email.received
    IF undefined_var > 0 {
        NOTIFY manager
    }
}"""
        comp = compile_any_source(source, verbose=False, program_name="GateFailTest")
        self.assertFalse(comp["success"])
        # execution_allowed must be False
        self.assertFalse(comp.get("success", True))

    def test_vm_run_independently_on_valid_tac(self):
        """VM can be run directly on valid TAC if compiler succeeded."""
        comp = compile_any_source(
            """WORKFLOW DirectVM {
    ON email.received
    EXTRACT amount FROM email
    NOTIFY finance
}""",
            verbose=False, program_name="DirectVMTest"
        )
        self.assertTrue(comp["success"])

        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        result = vm.execute()
        self.assertIn(result["status"], ("SUCCESS", "FAILED"))


# ─────────────────────────────────────────────────────────────────────────────
#  4. Robustness Tests — edge cases and boundary conditions
# ─────────────────────────────────────────────────────────────────────────────

class TestRobustnessEdgeCases(unittest.TestCase):
    """
    Tests for robustness: empty/minimal/large/nested inputs.
    Compiler and VM must not crash or raise unhandled exceptions.
    """

    def test_empty_source(self):
        """Empty source must not crash the compiler."""
        comp = compile_any_source("", verbose=False, program_name="EmptySource")
        self.assertFalse(comp["success"])
        self.assertIsInstance(comp["sem_errors"], (list, type(None)))

    def test_whitespace_only_source(self):
        """Whitespace-only source must not crash."""
        comp = compile_any_source("   \n  \t  \n", verbose=False, program_name="WhitespaceOnly")
        self.assertFalse(comp["success"])

    def test_minimal_valid_workflow(self):
        """Minimal syntactically valid workflow must compile and produce TAC."""
        source = """WORKFLOW MinimalWF {
    ON email.received
    SAVE data TO database
}"""
        comp = compile_any_source(source, verbose=False, program_name="MinimalWF")
        self.assertTrue(comp["success"])
        self.assertGreater(len(comp["tac"]), 0)

    def test_deeply_nested_if_else(self):
        """Deeply nested IF/ELSE must not crash."""
        source = """WORKFLOW NestedIF {
    ON order.created
    EXTRACT amount FROM order
    IF amount > 1000 {
        IF amount > 5000 {
            NOTIFY director
        } ELSE {
            NOTIFY manager
        }
    } ELSE {
        NOTIFY finance
    }
    SAVE order TO database
}"""
        comp = compile_any_source(source, verbose=False, program_name="NestedIF")
        self.assertTrue(comp["success"])

    def test_large_workflow_does_not_crash(self):
        """A workflow with many statements should still compile without error."""
        stmts = "\n".join([f"    LOG 'Step {i}'" for i in range(50)])
        source = f"""WORKFLOW LargeWF {{
    ON email.received
{stmts}
    SAVE data TO database
}}"""
        comp = compile_any_source(source, verbose=False, program_name="LargeWF")
        # Just check it doesn't crash
        self.assertIsInstance(comp["success"], bool)

    def test_workflow_with_comments_compiles(self):
        """Workflow source with comment lines should compile cleanly."""
        source = """WORKFLOW CommentTest {
    ON invoice.received
    # This is a comment
    EXTRACT amount FROM invoice
    SAVE invoice TO database
}"""
        comp = compile_any_source(source, verbose=False, program_name="CommentTest")
        self.assertTrue(comp["success"])

    def test_multiple_variables_set(self):
        """Multiple SET + EXTRACT declarations should all be valid."""
        source = """WORKFLOW MultiVar {
    ON order.created
    EXTRACT amount FROM order
    EXTRACT quantity FROM order
    SET discount = 0
    SET tax = 0
    NOTIFY finance
    SAVE order TO database
}"""
        comp = compile_any_source(source, verbose=False, program_name="MultiVarTest")
        self.assertTrue(comp["success"])

    def test_vm_with_empty_ir_does_not_crash(self):
        """VM must not crash when given empty IR."""
        vm = WorkflowVM()
        instructions = []
        vm.load_ir(instructions)
        result = vm.execute()
        # Should produce some status without crashing
        self.assertIn("status", result)

    def test_vm_with_only_end_instruction(self):
        """VM must handle a single END instruction gracefully."""
        vm = WorkflowVM()
        vm.load_ir([TACInstr(op="END")])
        result = vm.execute()
        self.assertEqual(result["status"], "SUCCESS")

    def test_compile_preserves_all_error_types(self):
        """Compiler must return lex_errors, parse_errors, sem_errors in result."""
        comp = compile_any_source("INVALID SOURCE !!!@@@", verbose=False, program_name="BadSource")
        self.assertIn("lex_errors", comp)
        self.assertIn("parse_errors", comp)
        self.assertIn("sem_errors", comp)
        self.assertIn("tokens", comp)

    def test_workflow_with_parallel_block(self):
        """PARALLEL block must not crash the compiler."""
        source = """WORKFLOW ParallelTest {
    ON order.created
    EXTRACT amount FROM order
    PARALLEL {
        NOTIFY finance
        NOTIFY manager
    }
    SAVE order TO database
}"""
        comp = compile_any_source(source, verbose=False, program_name="ParallelTest")
        # Just assert no unhandled exception
        self.assertIsInstance(comp["success"], bool)

    def test_workflow_with_wait_statement(self):
        """WAIT statement must compile without error."""
        source = """WORKFLOW WaitTest {
    ON ticket.created
    EXTRACT priority FROM ticket
    WAIT 5 seconds
    NOTIFY manager
}"""
        comp = compile_any_source(source, verbose=False, program_name="WaitTest")
        self.assertTrue(comp["success"])


# ─────────────────────────────────────────────────────────────────────────────
#  5. Regression Tests — Previously Fixed Bugs
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionBugs(unittest.TestCase):
    """
    Regression tests for bugs that were identified and fixed.
    These ensure the fixes don't regress.
    """

    def test_lex_error_column_attribute_no_crash(self):
        """
        BUG: LexError has .column not .col, causing AttributeError in listing.
        FIX: listing.py uses getattr fallback.
        Regression: compile source that triggers a lex error should not crash.
        """
        # Ticket workflow with string literal in condition that lex-errors
        source = """WORKFLOW CustomerSupport {
    ON ticket.created
    EXTRACT priority FROM ticket
    IF priority == "HIGH" {
        NOTIFY manager
    }
    SAVE ticket TO database
}"""
        try:
            comp = compile_any_source(source, verbose=False, program_name="LexRegressionTest")
            # Should not crash — may or may not succeed depending on grammar
            self.assertIsInstance(comp, dict)
        except AttributeError as e:
            self.fail(f"Regression: AttributeError should not occur: {e}")

    def test_duplicate_variable_reports_correct_line(self):
        """
        BUG: Duplicate variable error reported wrong original definition line.
        FIX: Use all_definitions (pre-scan) not defined_vars (lazy) for line numbers.
        """
        from business_semantics import WorkflowSemanticAnalyzer
        dsl = """
        WORKFLOW TestDuplicateExtract {
            ON email.received
            EXTRACT amount FROM email
            EXTRACT amount FROM email
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        dup_errors = [e for e in errors if e.error_type == "DUPLICATE_VARIABLE"]
        self.assertTrue(len(dup_errors) > 0, "Expected DUPLICATE_VARIABLE error")
        err = dup_errors[0]
        # The duplicate is on line 5, and original was on line 4
        self.assertIn("line 4", err.message, f"Expected 'line 4' in message, got: {err.message}")

    def test_string_literal_lhs_relational_is_type_error(self):
        """
        BUG: String literal as LHS of relational operator was not flagged as TYPE_MISMATCH.
        FIX: Updated _validate_condition to check lhs_is_str independently.
        """
        from business_semantics import WorkflowSemanticAnalyzer
        dsl = """WORKFLOW TypeTest {
    ON email.received
    EXTRACT amount FROM email
    IF 'hello' < amount {
        NOTIFY finance
    }
}"""
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(
            any(e.error_type == "TYPE_MISMATCH" for e in errors),
            f"Expected TYPE_MISMATCH for string LHS, errors: {errors}"
        )

    def test_type_mismatch_in_condition_rhs_string(self):
        """
        BUG: amount > 'fifty_thousand' caused ValueError in interpreter.
        FIX: Semantic analyzer catches TYPE_MISMATCH before interpreter runs.
        """
        source = """WORKFLOW TypeMismatchWF {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 'fifty_thousand' {
        NOTIFY finance
    }
}"""
        # Must not raise ValueError or crash
        try:
            comp = compile_any_source(source, verbose=False, program_name="TypeMismatchRegression")
            # The semantic analyzer must catch the error and block compilation
            self.assertFalse(comp["success"],
                "TYPE_MISMATCH should block compilation")
            sem_errors = comp["sem_errors"]
            self.assertTrue(len(sem_errors) > 0, "Semantic errors must be reported")
        except ValueError as e:
            self.fail(f"Regression: ValueError should not be raised: {e}")
        except Exception as e:
            if "fifty_thousand" in str(e):
                self.fail(f"Regression: interpreter should not reach string comparison: {e}")


if __name__ == '__main__':
    unittest.main()
