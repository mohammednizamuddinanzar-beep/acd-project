import unittest
from workflow_vm import WorkflowVM
from icg import TACInstr


class TestExecutionTrace(unittest.TestCase):

    def test_execution_trace_captures_all_steps(self):
        vm = WorkflowVM()
        instructions = [
            TACInstr(op="EVENT", arg1="email.received"),
            TACInstr(op="EXTRACT", result="amount", arg1="email"),
            TACInstr(op="SET", result="tax", arg1="500"),
            TACInstr(op="END")
        ]
        vm.load_ir(instructions)
        res = vm.execute()

        trace = res["trace"]
        self.assertEqual(len(trace), 4)
        self.assertEqual(trace[0]["opcode"], "EVENT")
        self.assertEqual(trace[1]["opcode"], "EXTRACT")
        self.assertEqual(trace[2]["opcode"], "SET")
        self.assertEqual(trace[3]["opcode"], "END")

        for step in trace:
            self.assertIn("ip", step)
            self.assertIn("simulated_time", step)
            self.assertIn("env_snapshot", step)
            self.assertEqual(step["status"], "SUCCESS")


if __name__ == '__main__':
    unittest.main()
