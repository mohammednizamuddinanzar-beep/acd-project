"""
============================================================
  Business Workflow DSL – Semantic Analyzer Test Suite
  Comprehensive tests for all 7 semantic validation rules:
    1. Undefined variables
    2. Duplicate variables
    3. Invalid event names
    4. Invalid action names
    5. Type mismatches
    6. Using a variable before it is defined
    7. Invalid workflow structure
  Also includes tests for valid single and multi-branch workflows.
============================================================
"""

import sys
import os
import unittest

# Ensure src is on Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from business_semantics import WorkflowSemanticAnalyzer, WorkflowSemanticError
from main import compile_any_source


class TestBusinessWorkflowSemantics(unittest.TestCase):

    # ══════════════════════════════════════════════════════
    #  TEST SUITE: VALID WORKFLOWS
    # ══════════════════════════════════════════════════════

    def test_valid_standard_invoice_workflow(self):
        """Test canonical InvoiceProcessing workflow passes with 0 errors."""
        dsl = """
        WORKFLOW InvoiceProcessing {
            ON email.received
            EXTRACT amount FROM email
            IF amount > 50000 {
                NOTIFY finance
            }
            SAVE invoice TO database
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertEqual(len(errors), 0, f"Expected 0 errors, got: {[str(e) for e in errors]}")

    def test_valid_workflow_with_if_else_and_set(self):
        """Test valid workflow with SET, IF/ELSE branching, and notifications."""
        dsl = """
        WORKFLOW OrderApproval {
            ON order.placed
            EXTRACT total FROM order
            SET threshold = 10000
            IF total > threshold {
                NOTIFY manager
                LOG 'Escalated to management'
            }
            ELSE {
                NOTIFY shipping
                LOG 'Standard processing'
            }
            SAVE order TO database
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertEqual(len(errors), 0, f"Expected 0 errors, got: {[str(e) for e in errors]}")

    def test_valid_workflow_full_pipeline_compilation(self):
        """Test that a valid workflow compiles end-to-end through compile_any_source."""
        dsl = """
        WORKFLOW PaymentValidation {
            ON payment.received
            EXTRACT fee FROM payment
            IF fee > 500 {
                NOTIFY audit
            }
            SAVE payment TO 'ledger'
        }
        """
        results = compile_any_source(dsl, verbose=False)
        self.assertTrue(results['success'])
        self.assertEqual(len(results['sem_errors']), 0)
        self.assertIn('PaymentValidation', results['translated_source'])

    # ══════════════════════════════════════════════════════
    #  RULE 1: UNDEFINED VARIABLES
    # ══════════════════════════════════════════════════════

    def test_check1_undefined_variable_in_condition(self):
        """Detect undefined variable referenced in IF condition."""
        dsl = """
        WORKFLOW TestUndefinedVar {
            ON email.received
            IF unknown_amount > 50000 {
                NOTIFY finance
            }
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'UNDEFINED_VARIABLE' for e in errors))
        err = next(e for e in errors if e.error_type == 'UNDEFINED_VARIABLE')
        self.assertEqual(err.line, 4)
        self.assertIn("unknown_amount", err.message)

    def test_check1_undefined_source_in_extract(self):
        """Detect undefined source in EXTRACT statement (domain mismatch)."""
        dsl = """
        WORKFLOW TestUndefinedSource {
            ON email.received
            EXTRACT amount FROM unknown_service
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'UNDEFINED_VARIABLE' for e in errors))
        err = next(e for e in errors if e.error_type == 'UNDEFINED_VARIABLE')
        self.assertEqual(err.line, 4)
        self.assertIn("unknown_service", err.message)

    def test_check1_undefined_variable_in_set_rhs(self):
        """Detect undefined variable referenced in RHS of SET statement."""
        dsl = """
        WORKFLOW TestUndefinedSetRHS {
            ON order.placed
            SET final_price = missing_tax
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'UNDEFINED_VARIABLE' for e in errors))
        err = next(e for e in errors if e.error_type == 'UNDEFINED_VARIABLE')
        self.assertEqual(err.line, 4)
        self.assertIn("missing_tax", err.message)

    # ══════════════════════════════════════════════════════
    #  RULE 2: DUPLICATE VARIABLES
    # ══════════════════════════════════════════════════════

    def test_check2_duplicate_extracted_variable(self):
        """Detect duplicate extraction of the same variable name."""
        dsl = """
        WORKFLOW TestDuplicateExtract {
            ON email.received
            EXTRACT amount FROM email
            EXTRACT amount FROM email
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'DUPLICATE_VARIABLE' for e in errors))
        err = next(e for e in errors if e.error_type == 'DUPLICATE_VARIABLE')
        self.assertEqual(err.line, 5)
        self.assertIn("amount", err.message)
        self.assertIn("line 4", err.message)

    def test_check2_duplicate_set_after_extract(self):
        """Detect variable redefined via SET after already being extracted."""
        dsl = """
        WORKFLOW TestDuplicateSetAfterExtract {
            ON order.created
            EXTRACT total FROM order
            SET total = 500
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'DUPLICATE_VARIABLE' for e in errors))
        err = next(e for e in errors if e.error_type == 'DUPLICATE_VARIABLE')
        self.assertEqual(err.line, 5)
        self.assertIn("total", err.message)

    # ══════════════════════════════════════════════════════
    #  RULE 3: INVALID EVENT NAMES
    # ══════════════════════════════════════════════════════

    def test_check3_missing_event_name(self):
        """Detect ON trigger with missing event name."""
        dsl = """
        WORKFLOW TestMissingEvent {
            ON
            EXTRACT amount FROM email
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_EVENT' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_EVENT')
        self.assertEqual(err.line, 3)

    def test_check3_invalid_event_format_no_dot(self):
        """Detect event name that does not follow <domain>.<action> pattern."""
        dsl = """
        WORKFLOW TestInvalidEventNoDot {
            ON order_received_now
            EXTRACT amount FROM order
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_EVENT' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_EVENT')
        self.assertEqual(err.line, 3)
        self.assertIn("order_received_now", err.message)

    def test_check3_invalid_event_numeric_or_special_chars(self):
        """Detect event name with numbers only or invalid double dots."""
        dsl = """
        WORKFLOW TestInvalidEventChars {
            ON email..received
            EXTRACT amount FROM email
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_EVENT' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_EVENT')
        self.assertEqual(err.line, 3)

    # ══════════════════════════════════════════════════════
    #  RULE 4: INVALID ACTION NAMES
    # ══════════════════════════════════════════════════════

    def test_check4_unrecognized_action_trigger(self):
        """Detect unsupported action verb 'TRIGGER'."""
        dsl = """
        WORKFLOW TestInvalidAction {
            ON email.received
            TRIGGER webhook
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_ACTION' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_ACTION')
        self.assertEqual(err.line, 4)
        self.assertIn("TRIGGER", err.message)

    def test_check4_unrecognized_action_fetch(self):
        """Detect unsupported action verb 'FETCH'."""
        dsl = """
        WORKFLOW TestInvalidActionFetch {
            ON user.registered
            FETCH profile_data
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_ACTION' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_ACTION')
        self.assertEqual(err.line, 4)
        self.assertIn("FETCH", err.message)

    def test_check4_disallowed_ml_action(self):
        """Detect ML keyword 'TRAIN' in business automation workflow."""
        dsl = """
        WORKFLOW TestMLActionDisallowed {
            ON data.received
            TRAIN model ON dataset
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_ACTION' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_ACTION')
        self.assertEqual(err.line, 4)
        self.assertIn("TRAIN", err.message)

    # ══════════════════════════════════════════════════════
    #  RULE 5: TYPE MISMATCHES
    # ══════════════════════════════════════════════════════

    def test_check5_relational_comparison_with_string_literal(self):
        """Detect relational comparison (>) between numeric variable and string literal."""
        dsl = """
        WORKFLOW TestRelationalStringMismatch {
            ON email.received
            EXTRACT amount FROM email
            IF amount > '50000' {
                NOTIFY finance
            }
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'TYPE_MISMATCH' for e in errors))
        err = next(e for e in errors if e.error_type == 'TYPE_MISMATCH')
        self.assertEqual(err.line, 5)
        self.assertIn("Relational operator '>'", err.message)

    def test_check5_relational_string_operand_lhs(self):
        """Detect relational comparison (<) where LHS is a string literal."""
        dsl = """
        WORKFLOW TestRelationalLHSString {
            ON order.placed
            EXTRACT amount FROM order
            IF '100' <= amount {
                NOTIFY finance
            }
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'TYPE_MISMATCH' for e in errors))
        err = next(e for e in errors if e.error_type == 'TYPE_MISMATCH')
        self.assertEqual(err.line, 5)

    def test_check5_set_string_literal_type_mismatch(self):
        """Detect assigning string literal to numeric variable in SET."""
        dsl = """
        WORKFLOW TestSetStringTypeMismatch {
            ON order.placed
            SET amount = 'fifty_thousand'
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'TYPE_MISMATCH' for e in errors))
        err = next(e for e in errors if e.error_type == 'TYPE_MISMATCH')
        self.assertEqual(err.line, 4)
        self.assertIn("fifty_thousand", err.message)

    def test_check5_equality_numeric_with_string_mismatch(self):
        """Detect equality comparison between numeric variable and string literal."""
        dsl = """
        WORKFLOW TestEqualityTypeMismatch {
            ON invoice.uploaded
            EXTRACT amount FROM invoice
            IF amount == 'paid' {
                NOTIFY finance
            }
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'TYPE_MISMATCH' for e in errors))
        err = next(e for e in errors if e.error_type == 'TYPE_MISMATCH')
        self.assertEqual(err.line, 5)

    # ══════════════════════════════════════════════════════
    #  RULE 6: USING A VARIABLE BEFORE IT IS DEFINED
    # ══════════════════════════════════════════════════════

    def test_check6_use_before_def_in_condition(self):
        """Detect variable used in condition on line 4, but extracted on line 7."""
        dsl = """
        WORKFLOW TestUseBeforeDef {
            ON email.received
            IF amount > 50000 {
                NOTIFY finance
            }
            EXTRACT amount FROM email
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'USE_BEFORE_DEF' for e in errors))
        err = next(e for e in errors if e.error_type == 'USE_BEFORE_DEF')
        self.assertEqual(err.line, 4)
        self.assertIn("amount", err.message)
        self.assertIn("line 7", err.message)

    def test_check6_use_before_def_in_set(self):
        """Detect variable used in SET RHS on line 4, but defined on line 5."""
        dsl = """
        WORKFLOW TestUseBeforeDefSet {
            ON order.placed
            SET total = discount
            SET discount = 50
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'USE_BEFORE_DEF' for e in errors))
        err = next(e for e in errors if e.error_type == 'USE_BEFORE_DEF')
        self.assertEqual(err.line, 4)
        self.assertIn("discount", err.message)
        self.assertIn("line 5", err.message)

    # ══════════════════════════════════════════════════════
    #  RULE 7: INVALID WORKFLOW STRUCTURE
    # ══════════════════════════════════════════════════════

    def test_check7_missing_workflow_declaration(self):
        """Detect missing WORKFLOW declaration at top of file."""
        dsl = """
        ON email.received
        EXTRACT amount FROM email
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_STRUCTURE' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_STRUCTURE')
        self.assertEqual(err.line, 2)
        self.assertIn("before WORKFLOW", err.message)

    def test_check7_missing_on_event_trigger(self):
        """Detect action statements before ON event trigger."""
        dsl = """
        WORKFLOW TestMissingON {
            EXTRACT amount FROM email
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_STRUCTURE' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_STRUCTURE')
        self.assertEqual(err.line, 3)
        self.assertIn("ON <event>", err.message)

    def test_check7_unclosed_workflow_brace(self):
        """Detect unclosed workflow (missing closing brace)."""
        dsl = """
        WORKFLOW TestUnclosed {
            ON email.received
            EXTRACT amount FROM email
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_STRUCTURE' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_STRUCTURE')
        self.assertIn("unclosed", err.message)

    def test_check7_stray_closing_brace(self):
        """Detect stray closing brace when no block is open."""
        dsl = """
        WORKFLOW TestStrayBrace {
            ON email.received
        }
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_STRUCTURE' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_STRUCTURE')
        self.assertEqual(err.line, 5)
        self.assertIn("Mismatched closing brace", err.message)

    def test_check7_orphan_else_block(self):
        """Detect ELSE block without preceding IF statement."""
        dsl = """
        WORKFLOW TestOrphanElse {
            ON email.received
            ELSE {
                NOTIFY finance
            }
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_STRUCTURE' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_STRUCTURE')
        self.assertEqual(err.line, 4)
        self.assertIn("'ELSE' block must follow", err.message)

    def test_check7_malformed_extract_statement(self):
        """Detect malformed EXTRACT missing FROM clause."""
        dsl = """
        WORKFLOW TestMalformedExtract {
            ON email.received
            EXTRACT amount
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_STRUCTURE' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_STRUCTURE')
        self.assertEqual(err.line, 4)
        self.assertIn("EXTRACT <variable> FROM <source>", err.message)

    def test_check7_malformed_save_statement(self):
        """Detect malformed SAVE missing TO clause."""
        dsl = """
        WORKFLOW TestMalformedSave {
            ON email.received
            SAVE invoice
        }
        """
        analyzer = WorkflowSemanticAnalyzer(dsl)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'INVALID_STRUCTURE' for e in errors))
        err = next(e for e in errors if e.error_type == 'INVALID_STRUCTURE')
        self.assertEqual(err.line, 4)
        self.assertIn("SAVE <entity> TO <destination>", err.message)


if __name__ == '__main__':
    unittest.main(verbosity=2)
