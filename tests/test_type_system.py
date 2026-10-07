import unittest
from business_semantics import WorkflowSemanticAnalyzer


class TestStaticTypeSystem(unittest.TestCase):

    def test_valid_typed_set_declarations(self):
        source = """
WORKFLOW TypedWorkflow {
    ON email.received
    SET amount : NUMBER = 50000
    SET vendor : STRING = "ABC"
    SET approved : BOOLEAN = false
}
"""
        analyzer = WorkflowSemanticAnalyzer(source)
        errors = analyzer.analyze()
        self.assertEqual(len(errors), 0, f"Expected 0 errors, got: {[str(e) for e in errors]}")

    def test_invalid_assignment_type_mismatch(self):
        source = """
WORKFLOW InvalidTypeWorkflow {
    ON email.received
    SET amount : NUMBER = "hello"
}
"""
        analyzer = WorkflowSemanticAnalyzer(source)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'TYPE_MISMATCH' for e in errors))
        self.assertTrue(any("Expected NUMBER but found STRING" in e.message for e in errors))

    def test_invalid_relational_comparison_type_error(self):
        source = """
WORKFLOW RelationalTypeError {
    ON email.received
    SET amount : NUMBER = 50000
    IF amount > "hello" {
        NOTIFY finance
    }
}
"""
        analyzer = WorkflowSemanticAnalyzer(source)
        errors = analyzer.analyze()
        self.assertTrue(any(e.error_type == 'TYPE_MISMATCH' for e in errors))
        self.assertTrue(any("Relational operator" in e.message for e in errors))

    def test_valid_relational_comparison(self):
        source = """
WORKFLOW ValidComparison {
    ON email.received
    SET amount : NUMBER = 50000
    IF amount > 10000 {
        NOTIFY finance
    }
}
"""
        analyzer = WorkflowSemanticAnalyzer(source)
        errors = analyzer.analyze()
        self.assertEqual(len(errors), 0, f"Expected 0 errors, got: {[str(e) for e in errors]}")


if __name__ == '__main__':
    unittest.main()
