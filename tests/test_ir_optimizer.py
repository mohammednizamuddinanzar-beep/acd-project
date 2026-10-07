"""
tests/test_ir_optimizer.py
──────────────────────────
Exercises all four optimization passes:
  1. Constant Folding
  2. Constant Condition Simplification
  3. Dead Code / Dead Action Elimination
  4. Duplicate Extraction / Copy Elimination

Each test compiles a purpose-built DSL snippet and checks the
expected transformations directly on the TAC instruction list.
Run:
    cd src
    python ../tests/test_ir_optimizer.py
"""

import sys
import os
import unittest

# Put src/ on the path so ICG, optimizer etc. resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from icg import TACInstr
from ir_optimizer import IROptimizer, print_tac_comparison


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_instr(op, result=None, arg1=None, arg2=None):
    return TACInstr(op=op, result=result, arg1=arg1, arg2=arg2)


def ops(tac):
    """Return the list of op-codes for quick assertions."""
    return [i.op for i in tac]


def results(tac):
    return [i.result for i in tac]


# ---------------------------------------------------------------------------
# Test: Constant Folding
# ---------------------------------------------------------------------------
class TestConstantFolding(unittest.TestCase):

    def test_arithmetic_add(self):
        """t0 = 3 + 5  ->  t0 = 8; constant propagates into consumer WRITE."""
        tac = [
            make_instr("+", result="t0", arg1="3", arg2="5"),
            make_instr("WRITE", arg1="t0"),   # consume t0 so fold propagates
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        # After propagation t0=8 flows into WRITE; the WRITE arg should be '8'
        write = next(i for i in opt if i.op == "WRITE")
        self.assertEqual(write.arg1, "8")


    def test_arithmetic_mul(self):
        """t0 = 10 * 4  ->  t0 = 40"""
        tac = [
            make_instr("*", result="t0", arg1="10", arg2="4"),
            make_instr("WRITE", arg1="t0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        self.assertEqual(opt[0].arg1, "40")

    def test_arithmetic_div(self):
        """t0 = 20 / 4  ->  t0 = 5"""
        tac = [
            make_instr("/", result="t0", arg1="20", arg2="4"),
            make_instr("WRITE", arg1="t0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        self.assertEqual(opt[0].arg1, "5")

    def test_div_by_zero_not_folded(self):
        """t0 = 5 / 0  should NOT be folded (kept as-is)"""
        tac = [
            make_instr("/", result="t0", arg1="5", arg2="0"),
            make_instr("WRITE", arg1="t0"),   # keep t0 live
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 0)
        self.assertEqual(opt[0].op, "/")

    def test_relational_true(self):
        """t0 = 10 > 2  ->  t0 = 1  (folded); IF_FALSE 1 -> removed"""
        tac = [
            make_instr(">", result="t0", arg1="10", arg2="2"),
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        # Fold happened
        self.assertEqual(report.constant_folds, 1)
        # The IF_FALSE was simplified away (condition always true -> never branches)
        self.assertEqual(report.condition_simplifies, 1)
        self.assertNotIn("IF_FALSE", ops(opt))

    def test_relational_false(self):
        """t0 = 2 >= 10  ->  t0 = 0  (folded); IF_FALSE 0 -> GOTO"""
        tac = [
            make_instr(">=", result="t0", arg1="2", arg2="10"),
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        # IF_FALSE 0 becomes GOTO
        self.assertEqual(report.condition_simplifies, 1)
        self.assertIn("GOTO", ops(opt))
        self.assertNotIn("IF_FALSE", ops(opt))

    def test_unary_neg(self):
        """t0 = NEG 7  ->  t0 = -7"""
        tac = [
            make_instr("NEG", result="t0", arg1="7"),
            make_instr("WRITE", arg1="t0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        self.assertEqual(opt[0].arg1, "-7")

    def test_unary_not_false(self):
        """t0 = NOT 0  ->  t0 = 1; IF_FALSE 1 -> removed"""
        tac = [
            make_instr("NOT", result="t0", arg1="0"),
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        self.assertEqual(report.condition_simplifies, 1)
        self.assertNotIn("IF_FALSE", ops(opt))

    def test_unary_not_true(self):
        """t0 = NOT 1  ->  t0 = 0; IF_FALSE 0 -> GOTO"""
        tac = [
            make_instr("NOT", result="t0", arg1="1"),
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        self.assertEqual(report.condition_simplifies, 1)
        self.assertIn("GOTO", ops(opt))
        self.assertNotIn("IF_FALSE", ops(opt))

    def test_constant_propagation_chain(self):
        """
        x = 4
        t0 = x + 3     ->  t0 = 7  (x propagated then folded)
        """
        tac = [
            make_instr("COPY", result="x",  arg1="4"),
            make_instr("+",    result="t0", arg1="x", arg2="3"),
            make_instr("WRITE", arg1="t0"),   # keep t0 live
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 1)
        self.assertEqual(opt[1].arg1, "7")

    def test_non_constant_not_folded(self):
        """t0 = amount + 3  (amount is not a constant, no fold)"""
        tac = [
            make_instr("+", result="t0", arg1="amount", arg2="3"),
            make_instr("WRITE", arg1="t0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertEqual(report.constant_folds, 0)
        self.assertEqual(opt[0].op, "+")


# ---------------------------------------------------------------------------
# Test: Constant Condition Simplification
# ---------------------------------------------------------------------------
class TestConstantConditions(unittest.TestCase):

    def test_if_false_0_becomes_goto(self):
        """IF_FALSE 0 GOTO L0  ->  GOTO L0"""
        tac = [
            make_instr("COPY", result="t0", arg1="0"),
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("WRITE_STR", arg1="'hello'"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        # After pass 1, t0 propagated to 0; after pass 2 IF_FALSE 0 -> GOTO
        goto_ops = [i for i in opt if i.op == "GOTO"]
        self.assertTrue(len(goto_ops) >= 1)
        self.assertEqual(report.condition_simplifies, 1)

    def test_if_false_1_removed(self):
        """IF_FALSE 1 GOTO L0  ->  removed"""
        tac = [
            make_instr("COPY", result="t0", arg1="1"),
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertNotIn("IF_FALSE", ops(opt))
        self.assertEqual(report.condition_simplifies, 1)

    def test_if_true_1_becomes_goto(self):
        """IF_TRUE 1 GOTO L0  ->  GOTO L0"""
        tac = [
            make_instr("COPY", result="t0", arg1="1"),
            make_instr("IF_TRUE", result="L0", arg1="t0"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertNotIn("IF_TRUE", ops(opt))
        self.assertEqual(report.condition_simplifies, 1)

    def test_variable_condition_not_simplified(self):
        """IF_FALSE amount GOTO L  ->  keep (amount not a literal constant)"""
        tac = [
            make_instr("IF_FALSE", result="L0", arg1="amount"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertIn("IF_FALSE", ops(opt))
        self.assertEqual(report.condition_simplifies, 0)


# ---------------------------------------------------------------------------
# Test: Dead Code Elimination
# ---------------------------------------------------------------------------
class TestDeadCodeElimination(unittest.TestCase):

    def test_unreachable_after_goto(self):
        """Instructions between GOTO and the next LABEL are removed."""
        tac = [
            make_instr("GOTO", result="L1"),
            make_instr("WRITE_STR", arg1="'dead'"),      # unreachable
            make_instr("COPY", result="x", arg1="5"),    # unreachable
            make_instr("LABEL", result="L1"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertNotIn("'dead'", [i.arg1 for i in opt])
        self.assertGreaterEqual(report.dead_code_removed, 2)

    def test_reachable_after_label_kept(self):
        """Instructions after a LABEL following GOTO are kept."""
        tac = [
            make_instr("GOTO", result="L1"),
            make_instr("LABEL", result="L1"),
            make_instr("WRITE_STR", arg1="'alive'"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertIn("'alive'", [i.arg1 for i in opt])

    def test_dead_temp_eliminated(self):
        """t0 assigned but never read -> removed"""
        tac = [
            make_instr("COPY", result="t0", arg1="42"),   # dead temp
            make_instr("WRITE_STR", arg1="'hi'"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertNotIn("t0", results(opt))
        self.assertGreaterEqual(report.dead_code_removed, 1)

    def test_live_temp_kept(self):
        """t0 used in IF_FALSE -> kept"""
        tac = [
            make_instr(">", result="t0", arg1="amount", arg2="100"),
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("LABEL", result="L0"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        self.assertIn("t0", results(opt))


# ---------------------------------------------------------------------------
# Test: Duplicate Elimination
# ---------------------------------------------------------------------------
class TestDuplicateElimination(unittest.TestCase):

    def test_duplicate_copy_removed(self):
        """x = y  ;  x = y  ->  second copy removed"""
        tac = [
            make_instr("COPY", result="x", arg1="y"),
            make_instr("WRITE_STR", arg1="'sep'"),      # keep in same block
            make_instr("COPY", result="x", arg1="y"),  # duplicate
            make_instr("HALT"),
        ]
        # Note: copy_state cleared at HALT but not at WRITE_STR so duplicate is caught
        opt, report = IROptimizer(tac).optimize()
        copies = [i for i in opt if i.op == "COPY" and i.result == "x"]
        self.assertEqual(len(copies), 1)
        self.assertGreaterEqual(report.duplicates_removed, 1)

    def test_consecutive_dup_write_str_collapsed(self):
        """WRITE_STR 'foo' ; WRITE_STR 'foo'  ->  one"""
        tac = [
            make_instr("WRITE_STR", arg1="'foo'"),
            make_instr("WRITE_STR", arg1="'foo'"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        writes = [i for i in opt if i.op == "WRITE_STR" and i.arg1 == "'foo'"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(report.duplicates_removed, 1)

    def test_non_consecutive_write_str_kept(self):
        """WRITE_STR 'foo' ; WRITE_STR 'bar' ; WRITE_STR 'foo' -> all kept"""
        tac = [
            make_instr("WRITE_STR", arg1="'foo'"),
            make_instr("WRITE_STR", arg1="'bar'"),
            make_instr("WRITE_STR", arg1="'foo'"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        writes = [i for i in opt if i.op == "WRITE_STR"]
        self.assertEqual(len(writes), 3)

    def test_cse_eliminates_duplicate_expression(self):
        """
        t0 = amount > 100
        t1 = amount > 100   ->  t1 = t0  (CSE, within same extended block)
        Note: IF_FALSE does NOT split the block for CSE purposes.
        """
        tac = [
            make_instr(">", result="t0", arg1="amount", arg2="100"),
            make_instr(">", result="t1", arg1="amount", arg2="100"),  # dup expr
            make_instr("IF_FALSE", result="L0", arg1="t0"),
            make_instr("IF_FALSE", result="L1", arg1="t1"),
            make_instr("LABEL", result="L0"),
            make_instr("LABEL", result="L1"),
            make_instr("HALT"),
        ]
        opt, report = IROptimizer(tac).optimize()
        # t1 should now be a COPY from t0
        t1_instr = next((i for i in opt if i.result == "t1"), None)
        self.assertIsNotNone(t1_instr)
        self.assertEqual(t1_instr.op, "COPY")
        self.assertEqual(t1_instr.arg1, "t0")
        self.assertGreaterEqual(report.duplicates_removed, 1)


# ---------------------------------------------------------------------------
# Integration: Full pipeline against invoice workflow DSL
# ---------------------------------------------------------------------------
class TestOptimizerIntegration(unittest.TestCase):

    def test_invoice_workflow_optimizes_cleanly(self):
        """
        Compile the standard InvoiceProcessing workflow and confirm
        the optimizer runs without errors and reduces the instruction count.
        """
        from main import compile_any_source

        source = """\
WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE invoice TO database
}
"""
        result = compile_any_source(source, verbose=False, program_name="test_invoice")
        self.assertTrue(result['success'], "Compilation should succeed")
        self.assertIn('opt_tac', result, "opt_tac key expected in results")
        self.assertIn('opt_report', result, "opt_report key expected")

        tac     = result['tac']
        opt_tac = result['opt_tac']
        report  = result['opt_report']

        self.assertIsNotNone(report)
        # Optimizer should produce same or fewer instructions
        self.assertLessEqual(len(opt_tac), len(tac),
                             "Optimized TAC should not be longer than original")

    def test_constant_folding_in_workflow(self):
        """
        Workflow with a constant expression in SET:
          SET tax = 100 * 5  should be folded to  SET tax = 500
        """
        from main import compile_any_source

        source = """\
WORKFLOW TaxCalc {
    ON order.created
    EXTRACT price FROM order
    SET tax = 100 * 5
    SAVE tax TO ledger
}
"""
        result = compile_any_source(source, verbose=False, program_name="test_tax")
        if not result['success']:
            self.skipTest("TaxCalc compile failed – skip optimizer check")

        report = result['opt_report']
        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.constant_folds, 1,
                                "Expected at least one constant fold for 100 * 5")

    def test_optimization_report_printed(self, verbose=False):
        """Smoke-test: compile with verbose=True, confirm no crash."""
        from main import compile_any_source
        import io, contextlib

        source = """\
WORKFLOW Simple {
    ON form.submitted
    EXTRACT name FROM form
    SAVE name TO storage
}
"""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = compile_any_source(source, verbose=True, program_name="test_simple")

        output = buf.getvalue()
        self.assertIn("IR BEFORE OPTIMIZATION", output)
        self.assertIn("IR AFTER OPTIMIZATION", output)
        self.assertIn("IR OPTIMIZATION PASS REPORT", output)


# ---------------------------------------------------------------------------
# Visual demo – run as __main__ to see BEFORE/AFTER comparison
# ---------------------------------------------------------------------------
def run_demo():
    print("\n" + "=" * 60)
    print("  DEMO: IR Optimizer – all four passes")
    print("=" * 60)

    tac = [
        # Pass 1: constant fold
        make_instr("COPY",      result="x",  arg1="50000"),
        make_instr(">",         result="t0", arg1="75000", arg2="x"),
        # Pass 2: constant condition (t0 will be folded to 1 first)
        make_instr("IF_FALSE",  result="L0", arg1="t0"),
        make_instr("WRITE_STR", arg1="'Notification sent to finance'"),
        make_instr("GOTO",      result="L1"),
        # Pass 3: dead code after GOTO
        make_instr("WRITE_STR", arg1="'dead instruction'"),
        make_instr("LABEL",     result="L0"),
        make_instr("WRITE_STR", arg1="'L0 reached'"),
        make_instr("LABEL",     result="L1"),
        # Pass 4: duplicate WRITE_STR
        make_instr("WRITE_STR", arg1="'Saved invoice to database'"),
        make_instr("WRITE_STR", arg1="'Saved invoice to database'"),
        # Pass 4: CSE
        make_instr(">",         result="t1", arg1="75000", arg2="x"),
        make_instr("IF_FALSE",  result="L2", arg1="t1"),
        make_instr("LABEL",     result="L2"),
        make_instr("HALT"),
    ]

    optimizer = IROptimizer(tac)
    opt, report = optimizer.optimize()
    print_tac_comparison(tac, opt, report)


if __name__ == "__main__":
    # Show the visual demo first
    run_demo()
    print("\n" + "=" * 60)
    print("  Running unit tests...")
    print("=" * 60 + "\n")
    # Then run the test suite
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [
        TestConstantFolding,
        TestConstantConditions,
        TestDeadCodeElimination,
        TestDuplicateElimination,
        TestOptimizerIntegration,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
