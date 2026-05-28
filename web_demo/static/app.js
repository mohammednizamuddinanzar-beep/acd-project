const tabs = [
  ['output', 'Program Output'],
  ['listing', 'Listing'],
  ['tokens', 'Tokens'],
  ['ast', 'AST'],
  ['tac', 'Three-Address Code'],
  ['asm', 'Assembly'],
  ['errors', 'Errors'],
  ['translated', 'Lowered Core Code'],
  ['agent', 'AI Agent Report'],
];

const elements = {
  tabs: document.getElementById('tabs'),
  source: document.getElementById('sourceEditor'),
  programName: document.getElementById('programName'),
  status: document.getElementById('statusBar'),
  runtimeInput: document.getElementById('runtimeInput'),
  agentBackend: document.getElementById('agentBackend'),
  llmProvider: document.getElementById('llmProvider'),
  llmModel: document.getElementById('llmModel'),
  successValue: document.getElementById('successValue'),
  tokenCount: document.getElementById('tokenCount'),
  errorCount: document.getElementById('errorCount'),
  tacCount: document.getElementById('tacCount'),
  output: document.getElementById('outputPanel'),
  listing: document.getElementById('listingPanel'),
  tokens: document.getElementById('tokensPanel'),
  ast: document.getElementById('astPanel'),
  tac: document.getElementById('tacPanel'),
  asm: document.getElementById('asmPanel'),
  errors: document.getElementById('errorsPanel'),
  translated: document.getElementById('translatedPanel'),
  agent: document.getElementById('agentPanel'),
};

function setupTabs() {
  tabs.forEach(([key, label], index) => {
    const btn = document.createElement('button');
    btn.className = `tab ${index === 0 ? 'active' : ''}`;
    btn.textContent = label;
    btn.addEventListener('click', () => activateTab(key, btn));
    elements.tabs.appendChild(btn);
  });
}

function activateTab(key, button) {
  document.querySelectorAll('.tab').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
  button.classList.add('active');
  const panel = document.querySelector(`[data-panel="${key}"]`);
  if (panel) panel.classList.add('active');
}

function formatTokens(tokens) {
  return tokens
    .map(t => `${String(t.line).padStart(3)}:${String(t.column).padStart(3)}  ${t.type.padEnd(18)} ${JSON.stringify(t.value)}`)
    .join('\n');
}

function formatSingleError(err) {
  const lines = [];
  lines.push(`Line ${err.line ?? '?'} Col ${err.column ?? '?'} :: ${err.message}`);
  if (err.line_text) lines.push(`    ${err.line_text}`);
  return lines.join('\n');
}

function formatErrors(groups) {
  const lines = [];
  for (const [label, arr] of Object.entries(groups)) {
    lines.push(`=== ${label} (${arr.length}) ===`);
    if (!arr.length) {
      lines.push('None');
    } else {
      arr.forEach(err => {
        lines.push(formatSingleError(err));
        lines.push('');
      });
    }
    lines.push('');
  }
  return lines.join('\n');
}

async function fetchSample(endpoint) {
  const res = await fetch(endpoint);
  const data = await res.json();
  elements.source.value = data.source || '';
  elements.status.textContent = 'Sample loaded.';
}

async function compileCode() {
  const source = elements.source.value;
  if (!source.trim()) {
    elements.status.textContent = 'Please enter source code.';
    return;
  }

  elements.status.textContent = 'Compiling...';

  let res;
  let data;
  try {
    res = await fetch('/api/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source,
        program_name: elements.programName.value || 'web_input',
        runtime_inputs: elements.runtimeInput.value || '',
        agent_backend: elements.agentBackend.value || 'deterministic',
        llm_provider: elements.llmProvider.value || null,
        llm_model: elements.llmModel.value || null,
      }),
    });
    data = await res.json();
  } catch (err) {
    elements.status.textContent = `Could not reach backend: ${err.message}`;
    return;
  }

  if (!res.ok) {
    elements.status.textContent = data.error || 'Compilation failed.';
    return;
  }

  const lexErrors = data.lex_errors || [];
  const parseErrors = data.parse_errors || [];
  const semanticErrors = data.semantic_errors || [];
  const tokens = data.tokens || [];
  const tac = data.tac || [];
  const errorCount = lexErrors.length + parseErrors.length + semanticErrors.length;

  elements.successValue.textContent = data.success ? 'SUCCESS' : 'FAILED';
  elements.successValue.className = data.success ? 'good' : 'bad';
  elements.tokenCount.textContent = tokens.length;
  elements.errorCount.textContent = errorCount;
  elements.tacCount.textContent = tac.length;

  const runtimeLines = [];
  if (data.runtime_error) {
    runtimeLines.push(`Runtime error at line ${data.runtime_error.line ?? '?'} col ${data.runtime_error.column ?? '?'}: ${data.runtime_error.message}`);
    if (data.runtime_error.line_text) runtimeLines.push(data.runtime_error.line_text);
  }
  if (data.runtime_output) runtimeLines.push(data.runtime_output.trimEnd());
  if (!data.runtime_error && !data.runtime_output) runtimeLines.push('No program output.');
  if (data.runtime_warnings?.length) {
    runtimeLines.push('');
    runtimeLines.push('Warnings:');
    data.runtime_warnings.forEach(w => runtimeLines.push(`- ${w}`));
  }

  elements.output.textContent = runtimeLines.join('\n');
  elements.listing.textContent = data.listing || 'No listing output.';
  elements.tokens.textContent = formatTokens(tokens) || 'No tokens.';
  elements.ast.textContent = data.ast || 'AST not available.';
  elements.tac.textContent = tac.join('\n') || 'No TAC generated.';
  elements.asm.textContent = data.asm || 'Assembly not generated.';
  elements.errors.textContent = formatErrors({
    Lexical: lexErrors,
    Parse: parseErrors,
    Semantic: semanticErrors,
  });
  elements.translated.textContent = data.translated_source || 'No lowered core code.';
  elements.agent.textContent = data.agent_report_text || 'No agent report generated.';

  const lang = data.source_language === 'ai_workflow_dsl' ? 'AI workflow DSL' : 'Pascal-like core DSL';
  elements.status.textContent = data.success
    ? `Compilation completed successfully. Source language: ${lang}. Agent backend: ${elements.agentBackend.value}.`
    : `Compilation completed with ${errorCount} error(s). Source language: ${lang}. Agent backend: ${elements.agentBackend.value}.`;
}

document.getElementById('loadSampleBtn').addEventListener('click', () => fetchSample('/api/sample'));
document.getElementById('loadRealBtn').addEventListener('click', () => fetchSample('/api/real-training-sample'));
document.getElementById('loadErrorBtn').addEventListener('click', () => fetchSample('/api/error-sample'));
document.getElementById('compileBtn').addEventListener('click', compileCode);

setupTabs();
fetchSample('/api/sample');
