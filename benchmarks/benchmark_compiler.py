"""
benchmarks/benchmark_compiler.py
==================================
Business Workflow DSL Compiler — Performance Benchmarks
Stage 10: Advanced Testing, Robustness & Benchmarking

Measures:
  1. Lexer throughput (tokens/sec)
  2. Parser throughput (AST nodes/sec)
  3. Semantic analysis time per workflow
  4. Full compile_any_source() end-to-end latency
  5. VM execution throughput (steps/sec)
  6. NL-to-DSL conversion time
  7. AI Assistant response time (MockAIProvider)
  8. Scale tests: 10, 100, 1000 compile runs

Usage:
  python benchmarks/benchmark_compiler.py

Output:
  benchmarks/benchmark_results.json  — structured JSON results
  Console table                       — human-readable summary

Requirements:
  No external packages. Uses only stdlib (timeit, statistics, json, os, sys).
"""

import sys
import os
import time
import timeit
import statistics
import json
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import compile_any_source
from workflow_vm import WorkflowVM
from icg import TACInstr
from nl_to_dsl import nl_to_dsl
from ai_assistant import MockAIProvider


# ─────────────────────────────────────────────────────────────────────────────
#  Benchmark Source Fixtures
# ─────────────────────────────────────────────────────────────────────────────

SIMPLE_WORKFLOW = """WORKFLOW SimpleWF {
    ON email.received
    EXTRACT amount FROM email
    NOTIFY finance
}"""

MEDIUM_WORKFLOW = """WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    EXTRACT vendor FROM email
    SET tax = 0
    SET discount = 0
    IF amount > 50000 {
        NOTIFY finance
        NOTIFY director
    } ELSE {
        NOTIFY manager
    }
    SAVE invoice TO database
    LOG 'Invoice processed'
}"""

COMPLEX_WORKFLOW = """WORKFLOW ComplexOrderProcessing {
    ON order.created
    VALIDATE order
    EXTRACT amount FROM order
    EXTRACT quantity FROM order
    EXTRACT customer FROM order
    SET tax = 0
    SET discount = 0
    IF amount > 100000 {
        IF quantity > 50 {
            NOTIFY director
        } ELSE {
            NOTIFY manager
        }
        RETRY 3 {
            CALL process_large_order
        }
    } ELSE {
        IF amount > 10000 {
            NOTIFY finance
        }
        CALL process_standard_order
    }
    SAVE order TO orders_database
    LOG 'Order processing complete'
}"""

FAULTY_WORKFLOW = """WORKFLOW FaultyWF {
    ON email.received
    IF amount > 50000 {
        NOTIFY finance
    }
}"""


def _make_large_workflow(n_statements: int) -> str:
    """Generate a workflow with n_statements LOG statements."""
    stmts = "\n".join([f"    LOG 'Step {i}'" for i in range(n_statements)])
    return f"""WORKFLOW LargeWF {{
    ON email.received
    EXTRACT amount FROM email
{stmts}
    SAVE data TO database
}}"""


# ─────────────────────────────────────────────────────────────────────────────
#  Benchmark Runner
# ─────────────────────────────────────────────────────────────────────────────

class BenchmarkResult:
    def __init__(self, name: str, iterations: int, times_ms: list):
        self.name = name
        self.iterations = iterations
        self.times_ms = times_ms
        self.mean_ms = statistics.mean(times_ms)
        self.median_ms = statistics.median(times_ms)
        self.min_ms = min(times_ms)
        self.max_ms = max(times_ms)
        self.stdev_ms = statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0

    def to_dict(self):
        return {
            "name": self.name,
            "iterations": self.iterations,
            "mean_ms": round(self.mean_ms, 3),
            "median_ms": round(self.median_ms, 3),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "stdev_ms": round(self.stdev_ms, 3),
        }

    def __str__(self):
        return (
            f"  {self.name:<50s} | "
            f"mean: {self.mean_ms:7.2f}ms | "
            f"median: {self.median_ms:7.2f}ms | "
            f"min: {self.min_ms:7.2f}ms | "
            f"max: {self.max_ms:7.2f}ms"
        )


def run_benchmark(name: str, fn, iterations: int = 50) -> BenchmarkResult:
    """Time `fn` for `iterations` runs, return BenchmarkResult."""
    times_ms = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times_ms.append((t1 - t0) * 1000)
    return BenchmarkResult(name, iterations, times_ms)


# ─────────────────────────────────────────────────────────────────────────────
#  Individual Benchmarks
# ─────────────────────────────────────────────────────────────────────────────

def bench_lexer_simple():
    from lexer import Lexer
    lex = Lexer(MEDIUM_WORKFLOW)
    lex.tokenize()

def bench_full_compile_simple():
    compile_any_source(SIMPLE_WORKFLOW, verbose=False, program_name="BenchSimple")

def bench_full_compile_medium():
    compile_any_source(MEDIUM_WORKFLOW, verbose=False, program_name="BenchMedium")

def bench_full_compile_complex():
    compile_any_source(COMPLEX_WORKFLOW, verbose=False, program_name="BenchComplex")

def bench_full_compile_faulty():
    compile_any_source(FAULTY_WORKFLOW, verbose=False, program_name="BenchFaulty")

def bench_vm_execute_medium():
    comp = compile_any_source(MEDIUM_WORKFLOW, verbose=False, program_name="BenchVMSetup")
    if comp["success"] and comp["tac"]:
        vm = WorkflowVM()
        vm.load_ir(comp["tac"])
        vm.execute()

def bench_semantic_analysis():
    from business_semantics import WorkflowSemanticAnalyzer
    analyzer = WorkflowSemanticAnalyzer(COMPLEX_WORKFLOW)
    analyzer.analyze()

def bench_nl_to_dsl():
    nl_to_dsl("When an invoice arrives by email, extract the amount and notify finance if it is above 50000.", verbose=False)

def bench_ai_mock_explain_error():
    provider = MockAIProvider()
    provider.explain_error(
        source=MEDIUM_WORKFLOW,
        error_type="UNDEFINED_VARIABLE",
        error_message="Variable 'amount' is undefined",
        error_line=3,
    )

def bench_ai_mock_explain_workflow():
    provider = MockAIProvider()
    provider.explain_workflow(COMPLEX_WORKFLOW)

def bench_large_workflow_50_stmts():
    src = _make_large_workflow(50)
    compile_any_source(src, verbose=False, program_name="BenchLarge50")

def bench_large_workflow_200_stmts():
    src = _make_large_workflow(200)
    compile_any_source(src, verbose=False, program_name="BenchLarge200")


# ─────────────────────────────────────────────────────────────────────────────
#  Scale Test: 100 Compile Runs
# ─────────────────────────────────────────────────────────────────────────────

def bench_100_compile_runs():
    """Total throughput: 100 compilations in sequence."""
    for i in range(100):
        compile_any_source(SIMPLE_WORKFLOW, verbose=False, program_name=f"Scale{i}")


# ─────────────────────────────────────────────────────────────────────────────
#  Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 90)
    print("  Business Workflow DSL Compiler — Performance Benchmarks")
    print(f"  Run at: {datetime.datetime.now().isoformat()}")
    print("=" * 90)
    print()

    benchmarks = [
        ("Lexer tokenize (medium workflow)",       bench_lexer_simple,             100),
        ("Semantic analysis (complex workflow)",    bench_semantic_analysis,        100),
        ("Full compile: simple workflow",           bench_full_compile_simple,      100),
        ("Full compile: medium workflow",           bench_full_compile_medium,       50),
        ("Full compile: complex workflow",          bench_full_compile_complex,      50),
        ("Full compile: faulty workflow (errors)",  bench_full_compile_faulty,      100),
        ("Full compile: 50-statement workflow",     bench_large_workflow_50_stmts,   30),
        ("Full compile: 200-statement workflow",    bench_large_workflow_200_stmts,  10),
        ("VM execute: medium workflow",             bench_vm_execute_medium,         50),
        ("NL-to-DSL conversion",                   bench_nl_to_dsl,                 50),
        ("AI MockProvider: explain_error",          bench_ai_mock_explain_error,    100),
        ("AI MockProvider: explain_workflow",       bench_ai_mock_explain_workflow,  100),
    ]

    results = []
    for name, fn, iters in benchmarks:
        print(f"  Running: {name} ({iters}x)...", end="", flush=True)
        try:
            result = run_benchmark(name, fn, iterations=iters)
            results.append(result)
            print(f" ✓  mean={result.mean_ms:.2f}ms")
        except Exception as exc:
            print(f" ✗ FAILED: {exc}")
            results.append(BenchmarkResult(f"{name} [FAILED: {exc}]", iters, [0.0]))

    # Scale test (runs 100 compilations — report total time)
    print(f"  Running: Scale test (100 full compile runs)...", end="", flush=True)
    t0 = time.perf_counter()
    try:
        bench_100_compile_runs()
        total_ms = (time.perf_counter() - t0) * 1000
        per_compile = total_ms / 100
        print(f" ✓  total={total_ms:.0f}ms, {per_compile:.2f}ms/compile")
        results.append(BenchmarkResult(
            "Scale test: 100 compilations (total)",
            100,
            [total_ms / 100] * 100,
        ))
    except Exception as exc:
        print(f" ✗ FAILED: {exc}")

    print()
    print("=" * 90)
    print("  RESULTS SUMMARY")
    print("=" * 90)
    for r in results:
        print(r)

    # Write JSON report
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "benchmark_results.json")
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "python_version": sys.version,
        "results": [r.to_dict() for r in results],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print()
    print(f"  Results written to: {output_path}")
    print("=" * 90)
    print()


if __name__ == "__main__":
    main()
