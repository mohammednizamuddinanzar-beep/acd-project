import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import compile_any_source
from workflow_vm import WorkflowVM


class TestEndToEndPipeline(unittest.TestCase):

    def test_invoice_processing_end_to_end(self):
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
        comp_res = compile_any_source(source, verbose=False, program_name="invoice_e2e")
        self.assertTrue(comp_res["success"])

        vm = WorkflowVM()
        vm.load_ir(comp_res["tac"])
        vm_res = vm.execute()

        self.assertEqual(vm_res["status"], "SUCCESS")
        self.assertEqual(vm_res["environment"]["amount"], 75000)

    def test_customer_support_end_to_end(self):
        source = """
WORKFLOW CustomerSupport {
    ON ticket.created
    EXTRACT priority FROM ticket
    IF priority == "HIGH" {
        NOTIFY manager
    }
    SAVE ticket TO database
}
"""
        comp_res = compile_any_source(source, verbose=False, program_name="cust_e2e")
        self.assertTrue(comp_res["success"])

        vm = WorkflowVM()
        vm.load_ir(comp_res["tac"])
        vm_res = vm.execute()

        self.assertEqual(vm_res["status"], "SUCCESS")

    def test_order_processing_end_to_end(self):
        source = """
WORKFLOW OrderProcessing {
    ON order.created
    VALIDATE order
    EXTRACT amount FROM order
    IF amount > 10000 {
        NOTIFY manager
    }
    SAVE order TO database
}
"""
        comp_res = compile_any_source(source, verbose=False, program_name="order_e2e")
        self.assertTrue(comp_res["success"])

        vm = WorkflowVM()
        vm.load_ir(comp_res["tac"])
        vm_res = vm.execute()

        self.assertEqual(vm_res["status"], "SUCCESS")


if __name__ == '__main__':
    unittest.main()
