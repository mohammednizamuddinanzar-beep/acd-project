import unittest
from cfg import ControlFlowGraph


class TestControlFlowGraph(unittest.TestCase):

    def test_cfg_basic_blocks_and_edges(self):
        source = """
WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    } ELSE {
        NOTIFY sales
    }
    SAVE invoice TO database
}
"""
        cfg = ControlFlowGraph("InvoiceProcessing")
        cfg.build_from_source(source)

        self.assertGreater(len(cfg.blocks), 2)
        self.assertGreater(len(cfg.edges), 2)
        self.assertIn("ENTRY", cfg.blocks[0].label)

        dot_str = cfg.to_dot()
        self.assertIn("digraph", dot_str)
        self.assertIn("ENTRY", dot_str)
        self.assertIn("EXIT", dot_str)

    def test_cfg_export_dot(self):
        source = "WORKFLOW Simple { ON test.ev NOTIFY admin }"
        cfg = ControlFlowGraph("Simple")
        cfg.build_from_source(source)
        dot_out = cfg.export_dot("workflow_cfg.dot")
        self.assertIn("digraph", dot_out)


if __name__ == '__main__':
    unittest.main()
