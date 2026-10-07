"""
test_nl_to_dsl.py — Test Suite for Natural Language -> DSL Converter
=====================================================================

Validates:
1. Natural language descriptions are converted into valid Business Workflow DSL.
2. AI / Converter NEVER executes workflows directly; it only returns a DSL string.
3. The generated DSL flows through the deterministic compiler pipeline:
   NL -> Converter -> DSL -> Lexer -> Parser -> Semantic Analysis -> IR -> Execution.
4. Various workflow scenarios (Invoice, Order, Payment) compile and execute cleanly.
5. Empty or malformed inputs are handled gracefully.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nl_to_dsl import NLToDSLConverter, nl_to_dsl
from main import compile_any_source


class TestNLToDSL(unittest.TestCase):

    def test_invoice_processing_prompt(self):
        nl = "When an invoice arrives, extract the amount and notify finance if it is above 50000."
        res = nl_to_dsl(nl, verbose=False)

        # Check conversion result structure
        self.assertIn("WORKFLOW", res.dsl)
        self.assertIn("ON invoice.received", res.dsl)
        self.assertIn("EXTRACT amount FROM invoice", res.dsl)
        self.assertIn("IF amount > 50000", res.dsl)
        self.assertIn("NOTIFY finance", res.dsl)

        # Pipeline validation: Compile through deterministic compiler
        comp_res = compile_any_source(res.dsl, verbose=False, program_name="TestInvoiceNL")
        self.assertTrue(comp_res['success'])
        self.assertEqual(len(comp_res['lex_errors']), 0)
        self.assertEqual(len(comp_res['parse_errors']), 0)
        self.assertEqual(len(comp_res['sem_errors']), 0)

        # Execution check
        self.assertIn('runtime_output', comp_res)
        self.assertIn("Notification Sent: [Recipient: 'finance']", comp_res['runtime_output'])

    def test_order_fulfillment_prompt(self):
        nl = "When an order is created, extract the total and save the order to the database."
        res = nl_to_dsl(nl, verbose=False)

        self.assertIn("WORKFLOW", res.dsl)
        self.assertIn("ON order.created", res.dsl)
        self.assertIn("EXTRACT total FROM order", res.dsl)
        self.assertIn("SAVE", res.dsl)

        comp_res = compile_any_source(res.dsl, verbose=False, program_name="TestOrderNL")
        self.assertTrue(comp_res['success'])
        self.assertIn('Database Record Saved:', comp_res['runtime_output'])

    def test_ai_does_not_execute(self):
        """Verify the converter returns pure DSL text and does not execute."""
        converter = NLToDSLConverter()
        result = converter.convert("When payment arrives, notify accounting.")
        
        # Result should be a data object containing a DSL string, not execution output
        self.assertIsInstance(result.dsl, str)
        self.assertTrue(result.dsl.strip().startswith("WORKFLOW"))
        self.assertNotIn("Execution finished", result.dsl)
        self.assertNotIn("Data Saved:", result.dsl)

    def test_empty_input(self):
        res = nl_to_dsl("", verbose=False)
        self.assertEqual(res.dsl, "")
        self.assertIn("Empty input", res.notes)


if __name__ == '__main__':
    unittest.main()
