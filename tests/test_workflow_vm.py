import unittest
from workflow_vm import WorkflowVM, VMRuntimeError
from service_registry import ServiceRegistry
from icg import TACInstr


class TestWorkflowVM(unittest.TestCase):

    def test_vm_event_extract_set(self):
        vm = WorkflowVM()
        instructions = [
            TACInstr(op="EVENT", arg1="invoice.received"),
            TACInstr(op="EXTRACT", result="amount", arg1="invoice"),
            TACInstr(op="SET", result="status", arg1="'PENDING'"),
            TACInstr(op="END")
        ]
        vm.load_ir(instructions)
        res = vm.execute()

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["environment"]["amount"], 75000)
        self.assertEqual(res["environment"]["status"], "PENDING")

    def test_vm_branching_if_true(self):
        vm = WorkflowVM()
        instructions = [
            TACInstr(op="EVENT", arg1="order.created"),
            TACInstr(op="EXTRACT", result="amount", arg1="order"),
            TACInstr(op="COMPARE_GT", result="t0", arg1="amount", arg2="50000"),
            TACInstr(op="JUMP_IF_FALSE", result="L1", arg1="t0"),
            TACInstr(op="NOTIFY", arg1="finance"),
            TACInstr(op="LABEL", result="L1"),
            TACInstr(op="SAVE", arg1="order", arg2="database"),
            TACInstr(op="END")
        ]
        vm.load_ir(instructions)
        res = vm.execute()

        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("t0", res["environment"])
        self.assertTrue(res["environment"]["t0"])
        self.assertEqual(res["activity_summary"]["notifications_sent"], 1)

    def test_vm_wait_simulated_time(self):
        vm = WorkflowVM()
        instructions = [
            TACInstr(op="EVENT", arg1="ticket.created"),
            TACInstr(op="WAIT", arg1="5", arg2="seconds"),
            TACInstr(op="END")
        ]
        vm.load_ir(instructions)
        res = vm.execute()

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["simulated_time"], 5.0)

    def test_vm_retry_success(self):
        vm = WorkflowVM()
        vm.service_registry.set_failure_simulation("email", 1)  # fail once then succeed
        instructions = [
            TACInstr(op="RETRY_BEGIN", arg1="3"),
            TACInstr(op="CALL", arg1="send_email"),
            TACInstr(op="RETRY_END"),
            TACInstr(op="END")
        ]
        vm.load_ir(instructions)
        res = vm.execute()

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["activity_summary"]["emails_sent"], 1)

    def test_vm_retry_exhaustion_failure(self):
        vm = WorkflowVM()
        vm.service_registry.set_failure_simulation("email", 5)  # fails 5 times, max attempt 2
        instructions = [
            TACInstr(op="RETRY_BEGIN", arg1="2"),
            TACInstr(op="CALL", arg1="send_email"),
            TACInstr(op="RETRY_END"),
            TACInstr(op="END")
        ]
        vm.load_ir(instructions)
        res = vm.execute()

        self.assertEqual(res["status"], "FAILED")
        self.assertTrue(any("Retry exhaustion" in err for err in res["errors"]))


if __name__ == '__main__':
    unittest.main()
