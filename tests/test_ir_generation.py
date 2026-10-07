import unittest
from main import compile_any_source


class TestWorkflowIRGeneration(unittest.TestCase):

    def test_ir_generation_invoice(self):
        source = """
WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE invoice TO database
}
"""
        res = compile_any_source(source, verbose=False, program_name="invoice_test")
        self.assertTrue(res['success'])
        self.assertIsNotNone(res['tac'])
        self.assertGreater(len(res['tac']), 0)


if __name__ == '__main__':
    unittest.main()
