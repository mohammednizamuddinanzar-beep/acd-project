import unittest
from symbol_table import SymbolTable, TypeDesc
from business_semantics import WorkflowSemanticAnalyzer


class TestSymbolTableScopes(unittest.TestCase):

    def test_symbol_table_methods(self):
        sym_tab = SymbolTable()
        self.assertEqual(sym_tab.current_scope.name, "global")

        sym_tab.enter_scope("workflow_scope")
        self.assertEqual(sym_tab.current_scope.name, "workflow_scope")

        ok = sym_tab.declare("x", TypeDesc("NUMBER"), line=10, col=5)
        self.assertTrue(ok)
        self.assertIsNotNone(sym_tab.lookup_current_scope("x"))
        self.assertIsNotNone(sym_tab.lookup("x"))

        # Duplicate declaration in same scope
        ok_dup = sym_tab.declare("x", TypeDesc("NUMBER"), line=11)
        self.assertFalse(ok_dup)

        sym_tab.enter_scope("if_scope")
        self.assertIsNotNone(sym_tab.lookup("x"))  # lookup walks up parent scopes
        self.assertIsNone(sym_tab.lookup_current_scope("x"))  # local scope does not have x

        sym_tab.exit_scope()
        self.assertEqual(sym_tab.current_scope.name, "workflow_scope")

    def test_block_scope_isolation_semantic_error(self):
        source = """
WORKFLOW ScopeTest {
    ON email.received
    IF true {
        SET x : NUMBER = 10
    }
    NOTIFY x
}
"""
        analyzer = WorkflowSemanticAnalyzer(source)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'UNDEFINED_VARIABLE' for e in errors))
        self.assertTrue(any("Variable 'x' is unavailable outside its block scope" in e.message for e in errors))


if __name__ == '__main__':
    unittest.main()
