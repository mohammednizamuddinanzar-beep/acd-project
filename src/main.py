"""
============================================================
  DSL Compiler – Main Driver
  Orchestrates all 4 phases of the compiler pipeline:
    1. Lexical Analysis   (Lexer)
    2. Syntax Analysis    (Parser → AST)
    3. Semantic Analysis  + Intermediate Code Generation (ICG)
    4. Target Code Generation (CodeGen → Assembly)
  Produces: listing file, token table, TAC, Assembly output
============================================================
"""

import sys
import os
import argparse
from typing import Optional, List, Dict, Any

# Make Windows console UTF-8 friendly
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Add src to path when running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer    import Lexer,    print_token_table
from parser   import Parser
from icg      import ICG
from codegen  import CodeGen
from interpreter import Interpreter
from listing  import ListingGenerator
from ast_nodes import ASTPrinter
from ai_dsl import detect_ai_dsl, transpile_ai_dsl, AIDSLCompileError
from agent_orchestrator import build_agent_report
from ir_optimizer import IROptimizer, print_tac_comparison


BANNER = """
╔══════════════════════════════════════════════════════════╗
║          DSL / Pascal-like Language Compiler             ║
║          Full 4-Phase Compiler Pipeline                  ║
║          Lexer → Parser → ICG → CodeGen                  ║
╚══════════════════════════════════════════════════════════╝
"""


def compile_source(source: str,
                   verbose: bool = True,
                   output_dir: Optional[str] = None,
                   program_name: str = "program") -> dict:
    """
    Full compilation pipeline.
    Returns dict with all phase results for integration / testing.
    """
    results = {
        'tokens':      [],
        'lex_errors':  [],
        'ast':         None,
        'parse_errors': [],
        'tac':         [],
        'opt_tac':     [],
        'opt_report':  None,
        'sem_errors':  [],
        'asm':         [],
        'listing':     '',
        'success':     False,
    }

    listing = ListingGenerator(source)

    # ══════════════════════════════════════════════════════
    #  PHASE 1 – LEXICAL ANALYSIS
    # ══════════════════════════════════════════════════════
    if verbose:
        print("\n" + "─" * 60)
        print("  PHASE 1 – LEXICAL ANALYSIS")
        print("─" * 60)

    lexer          = Lexer(source)
    tokens, lex_err = lexer.tokenize()
    results['tokens']     = tokens
    results['lex_errors'] = lex_err

    listing.add_all_lex_errors(lex_err)

    if verbose:
        print_token_table(tokens)
        if lex_err:
            print(f"\n  ✗ {len(lex_err)} Lexical error(s):")
            for e in lex_err:
                print(f"    {e}")
        else:
            print(f"\n  ✓ Lexical analysis completed. {len(tokens)} tokens produced.")

    # ══════════════════════════════════════════════════════
    #  PHASE 2 – SYNTAX ANALYSIS (PARSER)
    # ══════════════════════════════════════════════════════
    if verbose:
        print("\n" + "─" * 60)
        print("  PHASE 2 – SYNTAX ANALYSIS (PARSER)")
        print("─" * 60)

    # Filter out ERROR tokens before parsing
    clean_tokens = [t for t in tokens if t.type.name != 'ERROR']
    parser       = Parser(clean_tokens)
    ast          = parser.parse()
    parse_err    = parser.errors
    results['ast']          = ast
    results['parse_errors'] = parse_err

    listing.add_all_parse_errors(parse_err)

    if verbose:
        if parse_err:
            print(f"\n  ✗ {len(parse_err)} Parse error(s):")
            for e in parse_err:
                print(f"    {e}")
        else:
            print(f"\n  ✓ Parsing successful. AST built.")
        if ast and verbose:
            print("\n  AST:")
            printer = ASTPrinter()
            printer.print(ast)

    # ══════════════════════════════════════════════════════
    #  PHASE 3 – INTERMEDIATE CODE GENERATION (+ Semantics)
    # ══════════════════════════════════════════════════════
    if verbose:
        print("\n" + "─" * 60)
        print("  PHASE 3 – INTERMEDIATE CODE GENERATION")
        print("─" * 60)

    if ast is None:
        if verbose:
            print("  ✗ Skipping ICG — no AST available (parser failed).")
        listing_text = listing.generate(
            output_path=os.path.join(output_dir, f"{program_name}.lst"))
        results['listing'] = listing_text
        return results

    icg       = ICG()
    tac       = icg.generate(ast)
    sem_err   = icg.errors + icg.sym_tab.errors
    results['tac']        = tac
    results['sem_errors'] = sem_err

    listing.add_all_sem_errors(sem_err)

    if verbose:
        icg.sym_tab.dump()
        if sem_err:
            print(f"\n  ✗ {len(sem_err)} Semantic error(s):")
            for e in sem_err:
                print(f"    {e}")
        else:
            print(f"\n  ✓ ICG successful. {len(tac)} TAC instructions generated.")

    # ══════════════════════════════════════════════════════
    #  PHASE 3b – IR OPTIMIZATION PASS
    # ══════════════════════════════════════════════════════
    if not sem_err:
        if verbose:
            print("\n" + "─" * 60)
            print("  PHASE 3b – IR OPTIMIZATION PASS")
            print("─" * 60)

        optimizer = IROptimizer(tac)
        opt_tac, opt_report = optimizer.optimize()
        results['opt_tac']    = opt_tac
        results['opt_report'] = opt_report

        if verbose:
            print_tac_comparison(tac, opt_tac, opt_report)
    else:
        opt_tac    = tac
        opt_report = None

    # ══════════════════════════════════════════════════════
    #  PHASE 4 – TARGET CODE GENERATION
    # ══════════════════════════════════════════════════════
    all_errors = lex_err + parse_err + sem_err

    if verbose:
        print("\n" + "─" * 60)
        print("  PHASE 4 – TARGET CODE GENERATION")
        print("─" * 60)

    if all_errors:
        if verbose:
            print(f"  ✗ Code generation SKIPPED — {len(all_errors)} error(s) present.")
            print("    (Per spec: target code only generated if no errors)")
    else:
        cg  = CodeGen(opt_tac)
        asm = cg.generate()
        results['asm'] = asm
        results['success'] = True

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            asm_path = os.path.join(output_dir, f"{program_name}.asm")
            with open(asm_path, 'w', encoding='utf-8') as f:
                f.write(cg.get_asm_string())
            if verbose:
                cg.print_asm()
                print(f"\n  ✓ Assembly written to: {asm_path}")
        elif verbose:
            cg.print_asm()

        # ══════════════════════════════════════════════════════
        #  PHASE 5 – EXECUTION (RUNTIME)
        # ══════════════════════════════════════════════════════
        interpreter = Interpreter()
        exec_res = interpreter.run(ast)
        results['runtime_output'] = exec_res['output']

        if verbose:
            print("\n" + "─" * 60)
            print("  PHASE 5 – EXECUTION (RUNTIME)")
            print("─" * 60)
            print(exec_res['output'])

    # ══════════════════════════════════════════════════════
    #  LISTING FILE
    # ══════════════════════════════════════════════════════
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        lst_path     = os.path.join(output_dir, f"{program_name}.lst")
        listing_text = listing.generate(output_path=lst_path)
    else:
        lst_path     = None
        listing_text = listing.generate(output_path=None)
    results['listing'] = listing_text

    if verbose:
        print("\n" + "═" * 60)
        print("  LISTING FILE")
        print("═" * 60)
        print(listing_text)
        if lst_path:
            print(f"\n  Listing written to: {lst_path}")

    return results




def build_failed_compile_results(source: str, error: Exception) -> dict:
    """Create a compiler-shaped result for early failures so the agent can still report."""
    line = getattr(error, 'line', None)
    col = getattr(error, 'col', getattr(error, 'column', None))
    message = getattr(error, 'message', str(error))
    return {
        'success': False,
        'tokens': [],
        'lex_errors': [],
        'parse_errors': [error],
        'sem_errors': [],
        'ast': None,
        'tac': [],
        'asm': [],
        'listing': f'Early compiler failure: {message}',
        'source_language': 'ai_workflow_dsl' if detect_ai_dsl(source) else 'pascal_like_core_dsl',
        'translated_source': '',
        'original_source': source,
        'runtime_warnings': [],
        'error_line': line,
        'error_column': col,
    }

def compile_any_source(source: str,
                       verbose: bool = True,
                       output_dir: Optional[str] = None,
                       program_name: str = "program",
                       with_agent: bool = False,
                       agent_backend: str = "deterministic",
                       llm_provider: str = None,
                       llm_model: str = None) -> dict:
    """Compile either the legacy Pascal-like DSL or the AI workflow DSL.

    The agent is optional and runs after compilation. It never mutates compiler
    inputs, AST, TAC, or generated assembly.
    """
    if detect_ai_dsl(source):
        from business_semantics import WorkflowSemanticAnalyzer
        sem_analyzer = WorkflowSemanticAnalyzer(source)
        sem_errors = sem_analyzer.analyze()

        if sem_errors:
            listing = ListingGenerator(source)
            listing.add_all_sem_errors(sem_errors)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                lst_path = os.path.join(output_dir, f"{program_name}.lst")
                listing_text = listing.generate(output_path=lst_path)
            else:
                lst_path = None
                listing_text = listing.generate(output_path=None)

            results = {
                'tokens': [],
                'lex_errors': [],
                'ast': None,
                'parse_errors': [],
                'tac': [],
                'sem_errors': [str(e) for e in sem_errors],
                'sem_error_objects': sem_errors,
                'asm': [],
                'listing': listing_text,
                'success': False,
                'source_language': 'business_workflow_dsl',
                'translated_source': '',
                'original_source': source,
            }

            if verbose:
                print("\n" + "─" * 60)
                print("  PHASE 3 – SEMANTIC ANALYSIS (BUSINESS WORKFLOW DSL)")
                print("─" * 60)
                print(f"  ✗ {len(sem_errors)} Semantic error(s) detected:")
                for e in sem_errors:
                    print(f"    {e}")
                print("\n" + "═" * 60)
                print("  LISTING FILE")
                print("═" * 60)
                print(listing_text)
                print(f"\n  Listing written to: {lst_path}")

            if with_agent:
                agent_report = build_agent_report(
                    source,
                    results,
                    backend=agent_backend,
                    llm_provider=llm_provider,
                    llm_model=llm_model,
                )
                results['agent_report'] = agent_report.to_dict()
                results['agent_report_text'] = agent_report.to_text()

            return results

        transpiled = transpile_ai_dsl(source)
        results = compile_source(
            transpiled.translated_source,
            verbose=verbose,
            output_dir=output_dir,
            program_name=program_name,
        )
        results['source_language'] = transpiled.source_language
        results['translated_source'] = transpiled.translated_source
        results['original_source'] = source
        if results['success']:
            from ai_runtime import BusinessWorkflowRuntime
            runtime_res = BusinessWorkflowRuntime(source).execute()
            results['runtime_output'] = runtime_res['output']
            results['runtime_variables'] = runtime_res.get('variables', {})
            results['runtime_database'] = runtime_res.get('database', {})
            results['runtime_notifications'] = runtime_res.get('notifications', [])
            if verbose:
                print("\n" + "─" * 60)
                print("  PHASE 5 – BUSINESS WORKFLOW ENGINE (RUNTIME)")
                print("─" * 60)
                print(runtime_res['output'])
    else:
        results = compile_source(source, verbose=verbose, output_dir=output_dir, program_name=program_name)
        results['source_language'] = 'pascal_like_core_dsl'
        results['translated_source'] = source
        results['original_source'] = source

    if with_agent:
        agent_report = build_agent_report(
            source,
            results,
            backend=agent_backend,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        results['agent_report'] = agent_report.to_dict()
        results['agent_report_text'] = agent_report.to_text()
    return results


# ──────────────────────────────────────────────────────────
#  CLI entry point
# ──────────────────────────────────────────────────────────
def main():
    print(BANNER)

    ap = argparse.ArgumentParser(
        description='DSL Pascal-like Compiler – Full 4-Phase Pipeline')
    ap.add_argument('--clean', action='store_true', help='Clean generated compiler artifacts and temporary files')
    ap.add_argument('source_file', nargs='?', default=None, help='Path to source file (.pas, .aidl, or .workflow)')
    ap.add_argument('--nl', default=None, help='Natural language workflow description to compile')
    ap.add_argument('-o', '--output-dir', default='output', help='Output directory (default: output)')
    ap.add_argument('-q', '--quiet', action='store_true', help='Suppress verbose output')
    ap.add_argument('--run', action='store_true', help='Execute compiled workflow through Workflow Virtual Machine (VM)')
    ap.add_argument('--agent-report', action='store_true', help='Run the AI agent debugger after compilation')
    ap.add_argument('--agent-backend', default='deterministic', choices=['deterministic', 'llm', 'langgraph', 'langgraph-llm', 'auto'], help='Agent execution mode')
    ap.add_argument('--llm-provider', default=None, help='Optional LLM provider: openai or gemini')
    ap.add_argument('--llm-model', default=None, help='Optional model name for the selected LLM provider')
    args = ap.parse_args()

    if args.clean:
        scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from clean import clean_repository
        clean_repository(verbose=True)
        return

    prog_name = "workflow"
    if args.nl:
        from nl_to_dsl import nl_to_dsl
        conv = nl_to_dsl(args.nl, provider=args.llm_provider, model=args.llm_model, verbose=not args.quiet)
        source = conv.dsl
        prog_name = conv.workflow_name or "NLWorkflow"
    elif args.source_file:
        if not os.path.exists(args.source_file):
            print(f"ERROR: Source file not found: {args.source_file}")
            sys.exit(1)
        with open(args.source_file, 'r', encoding='utf-8') as f:
            source = f.read()
        prog_name = os.path.splitext(os.path.basename(args.source_file))[0]
    else:
        ap.print_help()
        sys.exit(1)

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    try:
        results = compile_any_source(
            source,
            verbose=not args.quiet,
            output_dir=args.output_dir,
            program_name=prog_name,
            with_agent=args.agent_report,
            agent_backend=args.agent_backend,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
        )
    except Exception as exc:
        results = build_failed_compile_results(source, exc)
        if args.agent_report:
            agent_report = build_agent_report(
                source,
                results,
                runtime_result={'output': '', 'warnings': []},
                runtime_error={'message': str(exc), 'line': getattr(exc, 'line', None), 'column': getattr(exc, 'col', None)},
                backend=args.agent_backend,
                llm_provider=args.llm_provider,
                llm_model=args.llm_model,
            )
            results['agent_report'] = agent_report.to_dict()
            results['agent_report_text'] = agent_report.to_text()

    if args.run:
        from workflow_vm import WorkflowVM
        from cfg import ControlFlowGraph
        vm = WorkflowVM()
        tac_list = results.get('tac', [])
        if tac_list:
            vm.load_ir(tac_list)
            vm_res = vm.execute()
        else:
            # Generate CFG & IR fallback execution from source
            cfg = ControlFlowGraph(prog_name)
            cfg.build_from_source(source)
            # Create synthetic TAC instructions from source statements for VM execution
            from icg import TACInstr
            tac_list = []
            for idx, line in enumerate(source.splitlines()):
                l_str = line.strip()
                if not l_str or l_str.startswith('#') or l_str.startswith('//'):
                    continue
                first = l_str.split()[0].upper().rstrip('{')
                tac_list.append(TACInstr(op=first, arg1=l_str))
            vm.load_ir(tac_list)
            vm_res = vm.execute()

        results['vm_execution'] = vm_res

        if not args.quiet:
            print("\n" + "═" * 60)
            print("  WORKFLOW VIRTUAL MACHINE (VM) EXECUTION")
            print("═" * 60)
            print(f"  Status:         {vm_res['status']}")
            print(f"  Simulated Time: {vm_res['simulated_time']} seconds")
            print(f"  Environment:    {vm_res['environment']}")
            print("\n  EXECUTION TRACE:")
            print(f"  {'STEP':<6} {'IP':<5} {'OPCODE':<16} {'OPERANDS':<25} {'TIME':<8} {'STATUS'}")
            print("  " + "-" * 70)
            for step in vm_res['trace']:
                print(f"  {step['step']:<6} {step['ip']:<5} {step['opcode']:<16} {step['operands']:<25} {step['simulated_time']:<8.1f} {step['status']}")
            print("\n  MOCK SERVICE ACTIVITY SUMMARY:")
            print(f"  {vm_res['activity_summary']}")

    if args.agent_report:
        print("\n" + "═" * 60)
        print("  AI AGENT DEBUGGER REPORT")
        print("═" * 60)
        print(results.get('agent_report_text', 'Agent report unavailable.'))

    print(f"\n{'✓ COMPILATION SUCCEEDED' if results['success'] or (args.run and results.get('vm_execution', {}).get('status') == 'SUCCESS') else '✗ COMPILATION FAILED'}")
    sys.exit(0 if results['success'] or (args.run and results.get('vm_execution', {}).get('status') == 'SUCCESS') else 1)




if __name__ == '__main__':
    main()
