from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from main import compile_any_source

source = (ROOT / 'examples' / 'real_training.aidl').read_text(encoding='utf-8')
result = compile_any_source(
    source,
    verbose=False,
    output_dir=str(ROOT / 'output'),
    program_name='agent_demo',
    with_agent=True,
    agent_backend='auto',
)
print(result['agent_report_text'])
assert result['success'] is True
assert result['agent_report']['validation_score'] >= 85

assert 'execution_mode' in result['agent_report']
assert 'llm_review' in result['agent_report']
