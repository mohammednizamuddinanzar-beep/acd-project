import io
import json
import os
import re
import sys
import tempfile
import threading
import webbrowser
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / 'src'
STATIC_DIR = Path(__file__).resolve().parent / 'static'
sys.path.insert(0, str(SRC_DIR))

# Make Windows console/file interactions UTF-8 friendly when possible
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from main import compile_any_source  # noqa: E402
from ai_dsl import AIDSLCompileError  # noqa: E402
from ast_nodes import ASTPrinter  # noqa: E402
from interpreter import Interpreter, RuntimeExecutionError  # noqa: E402
from ai_runtime import AIWorkflowRuntime, AIRuntimeError  # noqa: E402
from agent_orchestrator import build_agent_report  # noqa: E402

SAMPLE_PATH = ROOT / 'tests' / 'ai_sample.aidl'
ERROR_PATH = ROOT / 'tests' / 'ai_error.aidl'
LEGACY_SAMPLE_PATH = ROOT / 'tests' / 'sample.pas'
REAL_TRAINING_SAMPLE_PATH = ROOT / 'examples' / 'real_training.aidl'


def ast_to_string(ast):
    if ast is None:
        return ''
    printer = ASTPrinter()
    buf = io.StringIO()
    with redirect_stdout(buf):
        printer.print(ast)
    return buf.getvalue()


def normalize_errors(errors, source_lines=None):
    out = []
    source_lines = source_lines or []
    for e in errors or []:
        line = getattr(e, 'line', None)
        column = getattr(e, 'col', getattr(e, 'column', None))
        line_text = None
        if isinstance(line, int) and 1 <= line <= len(source_lines):
            line_text = source_lines[line - 1]
        out.append({
            'message': getattr(e, 'message', str(e)),
            'line': line,
            'column': column,
            'text': str(e),
            'line_text': line_text,
        })
    return out


def compile_payload(source_code: str, program_name: str = 'web_input', runtime_inputs=None, agent_backend='deterministic', llm_provider=None, llm_model=None):
    source_lines = source_code.splitlines()
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            results = compile_any_source(
                source_code,
                verbose=False,
                output_dir=tmpdir,
                program_name=program_name,
            )
        except AIDSLCompileError as exc:
            line_text = source_lines[exc.line - 1] if 1 <= exc.line <= len(source_lines) else None
            return build_error_response(
                source_code,
                str(exc),
                line=exc.line,
                column=exc.col,
                line_text=line_text,
                agent_backend=agent_backend,
                llm_provider=llm_provider,
                llm_model=llm_model,
                status_message='AI DSL preprocessing failed before the core compiler pipeline could complete.',
            )
        except Exception as exc:
            return build_error_response(
                source_code,
                f'Compilation failed: {exc}',
                agent_backend=agent_backend,
                llm_provider=llm_provider,
                llm_model=llm_model,
                status_message='Unexpected compiler server failure. The agent report was generated from the captured exception.',
            )
        asm_text = '\n'.join(str(line) for line in results['asm']) if results['asm'] else ''
        runtime_output = ''
        runtime_error = None
        runtime_warnings = []
        if results['success']:
            try:
                if results.get('source_language') == 'ai_workflow_dsl':
                    runtime = AIWorkflowRuntime(source_code, base_dir=str(ROOT)).execute()
                else:
                    runtime = Interpreter(inputs=runtime_inputs or []).run(results['ast'])
                runtime_output = runtime['output']
                runtime_warnings = runtime.get('warnings', [])
            except AIRuntimeError as exc:
                runtime_error = {
                    'message': str(exc),
                    'line': getattr(exc, 'line', None),
                    'column': getattr(exc, 'col', None),
                    'line_text': source_lines[exc.line - 1] if isinstance(getattr(exc, 'line', None), int) and 1 <= exc.line <= len(source_lines) else None,
                }
            except RuntimeExecutionError as exc:
                runtime_error = {
                    'message': str(exc),
                    'line': getattr(exc, 'line', None),
                    'column': getattr(exc, 'col', None),
                    'line_text': source_lines[exc.line - 1] if isinstance(getattr(exc, 'line', None), int) and 1 <= exc.line <= len(source_lines) else None,
                }
        agent_report = build_agent_report(
            source_code,
            {**results, 'runtime_warnings': runtime_warnings},
            runtime_result={'output': runtime_output, 'warnings': runtime_warnings},
            runtime_error=runtime_error,
            backend=agent_backend,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )

        return {
            'success': results['success'],
            'tokens': [
                {
                    'type': tok.type.name,
                    'value': tok.value,
                    'line': tok.line,
                    'column': tok.column,
                }
                for tok in results['tokens']
            ],
            'lex_errors': normalize_errors(results['lex_errors'], source_lines),
            'parse_errors': normalize_errors(results['parse_errors'], source_lines),
            'semantic_errors': normalize_errors(results['sem_errors'], source_lines) if results['sem_errors'] and not isinstance(results['sem_errors'][0], str) else [
                {
                    'message': e,
                    'line': (lambda m: int(m.group(1)) if m else None)(re.search(r'Line\s+(\d+)', e)),
                    'column': None,
                    'text': e,
                    'line_text': source_lines[int(m.group(1)) - 1] if (m := re.search(r'Line\s+(\d+)', e)) and 1 <= int(m.group(1)) <= len(source_lines) else None,
                }
                for e in results['sem_errors']
            ],
            'ast': ast_to_string(results['ast']),
            'tac': [str(instr) for instr in results['tac']],
            'asm': asm_text,
            'listing': results['listing'],
            'runtime_output': runtime_output,
            'runtime_error': runtime_error,
            'runtime_warnings': runtime_warnings,
            'source_language': results.get('source_language', 'pascal_like_core_dsl'),
            'translated_source': results.get('translated_source', source_code),
            'agent_report': agent_report.to_dict(),
            'agent_report_text': agent_report.to_text(),
        }


def build_error_response(source_code: str, message: str, line=None, column=None, line_text=None,
                         agent_backend='deterministic', llm_provider=None, llm_model=None,
                         status_message='Compilation failed before full compiler output was produced.'):
    """Return a normal Web IDE payload plus an AI Agent Report for failure paths.

    This keeps the web response shape stable even when AI DSL preprocessing,
    parsing, or unexpected runtime setup fails before compile_payload can finish.
    """
    compile_results = {
        'success': False,
        'tokens': [],
        'lex_errors': [],
        'parse_errors': [{
            'message': message,
            'line': line,
            'col': column,
            'column': column,
            'text': message,
            'line_text': line_text,
        }],
        'sem_errors': [],
        'tac': [],
        'asm': [],
        'listing': '',
        'ast': None,
        'source_language': 'ai_workflow_dsl' if source_code.strip().upper().startswith(('PIPELINE', 'DATASET', 'MODEL', 'SET', 'TRAIN', 'EVALUATE', 'PREDICT', 'DEPLOY', 'MONITOR', 'LOG', 'ENDPIPELINE')) else 'pascal_like_core_dsl',
        'translated_source': '',
        'original_source': source_code,
        'runtime_warnings': [],
    }
    agent_report = build_agent_report(
        source_code,
        compile_results,
        runtime_result={'output': '', 'warnings': []},
        runtime_error={'message': message, 'line': line, 'column': column, 'line_text': line_text},
        backend=agent_backend,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    return {
        'success': False,
        'tokens': [],
        'lex_errors': [],
        'parse_errors': [{
            'message': message,
            'line': line,
            'column': column,
            'text': message,
            'line_text': line_text,
        }],
        'semantic_errors': [],
        'ast': '',
        'tac': [],
        'asm': '',
        'listing': status_message,
        'runtime_output': '',
        'runtime_error': {'message': message, 'line': line, 'column': column, 'line_text': line_text},
        'runtime_warnings': [],
        'source_language': compile_results['source_language'],
        'translated_source': '',
        'agent_report': agent_report.to_dict(),
        'agent_report_text': agent_report.to_text(),
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        raw = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, file_path: Path, content_type='text/html; charset=utf-8'):
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/healthz', '/_ah/health'):
            return self._send_json({'status': 'ok', 'service': 'ai-workflow-compiler-agent'})
        if self.path in ('/', '/index.html'):
            return self._send_file(STATIC_DIR / 'index.html')
        if self.path == '/styles.css':
            return self._send_file(STATIC_DIR / 'styles.css', 'text/css; charset=utf-8')
        if self.path == '/app.js':
            return self._send_file(STATIC_DIR / 'app.js', 'application/javascript; charset=utf-8')
        if self.path == '/api/sample':
            return self._send_json({'source': SAMPLE_PATH.read_text(encoding='utf-8')})
        if self.path == '/api/error-sample':
            return self._send_json({'source': ERROR_PATH.read_text(encoding='utf-8')})
        if self.path == '/api/legacy-sample':
            return self._send_json({'source': LEGACY_SAMPLE_PATH.read_text(encoding='utf-8')})
        if self.path == '/api/real-training-sample':
            return self._send_json({'source': REAL_TRAINING_SAMPLE_PATH.read_text(encoding='utf-8')})
        return self._send_json({'error': 'Not found'}, status=404)

    def do_POST(self):
        if self.path != '/api/compile':
            return self._send_json({'error': 'Not found'}, status=404)
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return self._send_json({'error': 'Invalid JSON'}, status=400)

        source = payload.get('source', '')
        program_name = payload.get('program_name', 'web_input')
        runtime_inputs = payload.get('runtime_inputs', [])
        agent_backend = payload.get('agent_backend', 'deterministic')
        llm_provider = payload.get('llm_provider')
        llm_model = payload.get('llm_model')
        if not isinstance(source, str) or not source.strip():
            return self._send_json({'error': 'Source code is required'}, status=400)
        try:
            if isinstance(runtime_inputs, str):
                runtime_inputs = [int(x) for x in runtime_inputs.replace(',', ' ').split()] if runtime_inputs.strip() else []
            elif isinstance(runtime_inputs, list):
                runtime_inputs = [int(x) for x in runtime_inputs]
            else:
                runtime_inputs = []
            result = compile_payload(
                source,
                program_name,
                runtime_inputs=runtime_inputs,
                agent_backend=agent_backend,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
            return self._send_json(result)
        except AIDSLCompileError as exc:
            source_lines = source.splitlines()
            line_text = source_lines[exc.line - 1] if 1 <= exc.line <= len(source_lines) else None
            return self._send_json(build_error_response(
                source,
                str(exc),
                line=exc.line,
                column=exc.col,
                line_text=line_text,
                agent_backend=agent_backend,
                llm_provider=llm_provider,
                llm_model=llm_model,
                status_message='AI DSL preprocessing failed before the core compiler pipeline could complete.',
            ), status=200)
        except Exception as exc:
            return self._send_json(build_error_response(
                source,
                f'Compilation failed: {exc}',
                agent_backend=agent_backend,
                llm_provider=llm_provider,
                llm_model=llm_model,
                status_message='Unexpected compiler server failure. The agent report was generated from the captured exception.',
            ), status=200)


def run_server():
    """Start the Web IDE locally or on Google Cloud Run.

    Cloud Run requires binding to 0.0.0.0:$PORT. Local Windows machines can
    block common ports, so local mode tries several safe localhost fallbacks.
    """
    is_cloud_run = bool(os.environ.get("K_SERVICE"))
    requested_port = int(os.environ.get("PORT", 8080))

    if is_cloud_run:
        bind_options = [("0.0.0.0", requested_port)]
    else:
        bind_options = [
            ("127.0.0.1", requested_port),
            ("127.0.0.1", 8501),
            ("127.0.0.1", 9000),
            ("127.0.0.1", 5000),
            ("127.0.0.1", 8000),
            ("localhost", 8501),
        ]

    server = None
    last_error = None
    for host, port in bind_options:
        try:
            server = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError as exc:
            last_error = exc
            print(f"Could not bind to {host}:{port} -> {exc}", flush=True)

    if server is None:
        raise RuntimeError(
            "Could not start the Web IDE on any configured port. "
            "Try PowerShell: $env:PORT='9000'; python server.py"
        ) from last_error

    host, actual_port = server.server_address
    display_host = "127.0.0.1" if host in ("0.0.0.0", "localhost") else host
    url = f"http://{display_host}:{actual_port}"
    print(f"Web IDE running on {url}", flush=True)

    if not is_cloud_run:
        def _open_browser():
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Timer(0.6, _open_browser).start()

    server.serve_forever()


if __name__ == '__main__':
    run_server()
