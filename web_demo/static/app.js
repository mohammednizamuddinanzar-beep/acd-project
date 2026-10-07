/* ============================================================
   Business Workflow DSL Compiler — Web IDE Frontend
   Handles: compilation, VM trace, CFG display, mock services,
   pipeline stage animation, tab management, NL-to-DSL, samples.
   ============================================================ */

// ─── Tab Definitions ────────────────────────────────────────────────
const tabs = [
  ['output',     '⚡ Execution Output'],
  ['vm_trace',   '🔬 VM Trace'],
  ['cfg',        '🗺️ Control Flow Graph'],
  ['services',   '🔧 Mock Services'],
  ['agent',      '🤖 Agentic Debugger'],
  ['errors',     '❌ Errors & Diagnostics'],
  ['tac',        '🧱 TAC / IR Quadruples'],
  ['ast',        '🌳 AST (Parser)'],
  ['tokens',     '🔤 Tokens (Lexer)'],
  ['listing',    '📋 Listing File'],
  ['asm',        '⚙️ Assembly (CodeGen)'],
  ['translated', '🔄 Lowered Core IR'],
];

// ─── Element References ──────────────────────────────────────────────
const el = {
  tabs:            document.getElementById('tabs'),
  source:          document.getElementById('sourceEditor'),
  programName:     document.getElementById('programName'),
  status:          document.getElementById('statusBar'),
  agentBackend:    document.getElementById('agentBackend'),
  llmProvider:     document.getElementById('llmProvider'),
  llmModel:        document.getElementById('llmModel'),
  nlPrompt:        document.getElementById('nlPrompt'),
  nlGenerateBtn:   document.getElementById('nlGenerateBtn'),
  // Metrics
  successValue:    document.getElementById('successValue'),
  tokenCount:      document.getElementById('tokenCount'),
  errorCount:      document.getElementById('errorCount'),
  tacCount:        document.getElementById('tacCount'),
  vmStatusValue:   document.getElementById('vmStatusValue'),
  vmTimeValue:     document.getElementById('vmTimeValue'),
  traceStepCount:  document.getElementById('traceStepCount'),
  serviceCallCount:document.getElementById('serviceCallCount'),
  // Panels
  output:      document.getElementById('outputPanel'),
  vm_trace:    document.getElementById('vmTracePanel'),
  cfg:         document.getElementById('cfgPanel'),
  services:    document.getElementById('servicesPanel'),
  agent:       document.getElementById('agentPanel'),
  listing:     document.getElementById('listingPanel'),
  tokens:      document.getElementById('tokensPanel'),
  ast:         document.getElementById('astPanel'),
  tac:         document.getElementById('tacPanel'),
  asm:         document.getElementById('asmPanel'),
  errors:      document.getElementById('errorsPanel'),
  translated:  document.getElementById('translatedPanel'),
  // Pipeline steps
  pipeLexer:    document.getElementById('pipe-lexer'),
  pipeParser:   document.getElementById('pipe-parser'),
  pipeAst:      document.getElementById('pipe-ast'),
  pipeSemantic: document.getElementById('pipe-semantic'),
  pipeCfg:      document.getElementById('pipe-cfg'),
  pipeIr:       document.getElementById('pipe-ir'),
  pipeVm:       document.getElementById('pipe-vm'),
  pipeServices: document.getElementById('pipe-services'),
  // AI Assistant
  aiExplainErrorBtn:    document.getElementById('aiExplainErrorBtn'),
  aiExplainWorkflowBtn: document.getElementById('aiExplainWorkflowBtn'),
  aiExplainTraceBtn:    document.getElementById('aiExplainTraceBtn'),
  aiOutput:             document.getElementById('aiOutput'),
  aiOutputTitle:        document.getElementById('aiOutputTitle'),
  aiOutputContent:      document.getElementById('aiOutputContent'),
  aiOutputClose:        document.getElementById('aiOutputClose'),
  aiSuggestedDslWrap:   document.getElementById('aiSuggestedDslWrap'),
  aiSuggestedDsl:       document.getElementById('aiSuggestedDsl'),
  aiApplySuggestedBtn:  document.getElementById('aiApplySuggestedBtn'),
};

// ─── Tab Setup ───────────────────────────────────────────────────────
function setupTabs() {
  el.tabs.innerHTML = '';
  tabs.forEach(([key, label], index) => {
    const btn = document.createElement('button');
    btn.className = `tab${index === 0 ? ' active' : ''}`;
    btn.textContent = label;
    btn.setAttribute('data-key', key);
    btn.addEventListener('click', () => activateTab(key, btn));
    el.tabs.appendChild(btn);
  });
}

function activateTab(key, button) {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  button.classList.add('active');
  const panel = document.querySelector(`[data-panel="${key}"]`);
  if (panel) panel.classList.add('active');
}

function activateTabByKey(key) {
  const btn = Array.from(document.querySelectorAll('.tab')).find(b => b.getAttribute('data-key') === key);
  if (btn) activateTab(key, btn);
}

// ─── Status Bar ──────────────────────────────────────────────────────
function setStatus(text, mode = 'idle') {
  el.status.innerHTML = `<span class="status-dot ${mode}"></span> ${text}`;
}

// ─── Pipeline Stage Highlighting ─────────────────────────────────────
const pipeStages = [
  el.pipeLexer, el.pipeParser, el.pipeAst,
  el.pipeSemantic, el.pipeCfg, el.pipeIr,
  el.pipeVm, el.pipeServices,
];

function resetPipeline() {
  pipeStages.forEach(s => { if (s) s.className = 'pipe-step'; });
}

function setPipelineSuccess() {
  pipeStages.forEach(s => { if (s) s.classList.add('done-pipe'); });
}

function setPipelineError(upToIndex) {
  pipeStages.forEach((s, i) => {
    if (!s) return;
    if (i < upToIndex) s.classList.add('done-pipe');
    else if (i === upToIndex) s.classList.add('error-pipe');
  });
}

async function animatePipeline(success, errorCount) {
  resetPipeline();
  for (let i = 0; i < pipeStages.length; i++) {
    await new Promise(r => setTimeout(r, 90));
    const s = pipeStages[i];
    if (!s) continue;
    const isLast = i === pipeStages.length - 1;
    if (!success && errorCount > 0 && i >= 3) {
      s.classList.add('error-pipe');
    } else {
      s.classList.add(isLast && success ? 'done-pipe' : 'done-pipe');
    }
  }
}

// ─── Formatters ──────────────────────────────────────────────────────
function formatTokens(tokens) {
  if (!tokens?.length) return 'No tokens generated.';
  return tokens.map(t =>
    `${String(t.line).padStart(4)}:${String(t.column).padStart(3)}  ${t.type.padEnd(22)} ${JSON.stringify(t.value)}`
  ).join('\n');
}

function formatSingleError(err) {
  const lines = [];
  lines.push(`  Line ${err.line ?? '?'}, Col ${err.column ?? '?'} — ${err.message || err.text}`);
  if (err.line_text) lines.push(`    ▶ ${err.line_text.trim()}`);
  return lines.join('\n');
}

function formatErrors(groups) {
  const lines = [];
  for (const [label, arr] of Object.entries(groups)) {
    const icon = arr.length ? '✗' : '✓';
    lines.push(`${icon} ${label} (${arr.length} issue${arr.length !== 1 ? 's' : ''})`);
    lines.push('─'.repeat(50));
    if (!arr.length) {
      lines.push('  No issues found.\n');
    } else {
      arr.forEach(err => { lines.push(formatSingleError(err)); lines.push(''); });
    }
    lines.push('');
  }
  return lines.join('\n');
}

function formatVMTrace(trace, executionAllowed) {
  if (!executionAllowed) {
    return [
      'VM Execution: NOT STARTED',
      '═'.repeat(60),
      '',
      '  Compilation failed — VM execution was blocked.',
      '  Fix all compiler errors first, then re-compile.',
      '',
      '  Pipeline enforces: SOURCE → LEXER → PARSER → SEMANTIC → IR → VM',
      '  Invalid programs must not reach the VM.',
    ].join('\n');
  }
  if (!trace?.length) return 'No VM trace recorded. (Workflow may not have produced TAC IR.)';
  const lines = ['VM Execution Trace', '═'.repeat(60), ''];
  trace.forEach(step => {
    const time = typeof step.simulated_time === 'number'
      ? `t=${step.simulated_time.toFixed(2)}s`
      : 't=?';
    const status = step.status === 'SUCCESS' ? '✓' : '✗';
    lines.push(`Step ${String(step.step).padStart(3)} | IP:${String(step.ip).padStart(3)} | ${time} | ${status} ${step.opcode || ''}`);
    if (step.operands) lines.push(`           Operands : ${step.operands}`);
    if (step.result)   lines.push(`           Result   : ${step.result}`);
    if (step.error)    lines.push(`           Error    : ${step.error}`);
    const env = step.env_snapshot;
    if (env && Object.keys(env).length) {
      const envStr = Object.entries(env).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ');
      lines.push(`           Env     : { ${envStr} }`);
    }
    lines.push('');
  });
  return lines.join('\n');
}

function formatCFG(cfgDot) {
  if (!cfgDot) return 'Control Flow Graph not available.\n\n(CFG is built after a successful compile — run Compile & Execute first.)';
  return [
    'Control Flow Graph (DOT format)',
    '═'.repeat(60),
    '',
    cfgDot,
    '',
    '──────────────────────────────────────────────────────────',
    'Tip: Paste the DOT source above into https://dreampuf.github.io/GraphvizOnline/',
    'to visualize the full CFG as an interactive graph.',
  ].join('\n');
}

function formatMockServices(services, vmEnv) {
  const lines = ['Mock Service Activity', '═'.repeat(60), ''];

  if (services && Object.keys(services).length) {
    lines.push('Service Call Summary:');
    lines.push('─'.repeat(40));
    for (const [svc, info] of Object.entries(services)) {
      if (typeof info === 'object' && info !== null) {
        lines.push(`  ${svc.toUpperCase().padEnd(14)} calls=${info.calls ?? 0}  errors=${info.errors ?? 0}  latency=${info.avg_latency_ms ?? 0}ms`);
      } else {
        lines.push(`  ${svc.toUpperCase().padEnd(14)} ${JSON.stringify(info)}`);
      }
    }
    lines.push('');
  } else {
    lines.push('No service calls recorded during this execution.\n');
  }

  if (vmEnv && Object.keys(vmEnv).length) {
    lines.push('VM Runtime Environment (final state):');
    lines.push('─'.repeat(40));
    for (const [k, v] of Object.entries(vmEnv)) {
      lines.push(`  ${k.padEnd(20)} = ${JSON.stringify(v)}`);
    }
  }
  return lines.join('\n');
}

// ─── Load Sample Workflows ───────────────────────────────────────────
async function fetchSample(endpoint) {
  setStatus('Loading workflow sample...', 'running');
  try {
    const res = await fetch(endpoint);
    const data = await res.json();
    el.source.value = data.source || '';
    const match = (data.source || '').match(/WORKFLOW\s+(\w+)/i);
    if (match?.[1]) el.programName.value = match[1];
    setStatus('Sample loaded — click Compile & Execute to run the full pipeline.', 'idle');
  } catch (err) {
    setStatus(`Could not load sample: ${err.message}`, 'bad');
  }
}

// ─── NL → DSL Conversion ─────────────────────────────────────────────
async function convertNLtoDSL() {
  const prompt = el.nlPrompt.value.trim();
  if (!prompt) {
    setStatus('Please enter a natural language workflow description.', 'idle');
    el.nlPrompt.focus();
    return;
  }
  setStatus('Converting natural language to Business Workflow DSL...', 'running');
  el.nlGenerateBtn.disabled = true;
  el.nlGenerateBtn.textContent = 'Converting...';
  try {
    const res = await fetch('/api/nl-to-dsl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        llm_provider: el.llmProvider.value || null,
        llm_model:    el.llmModel.value || null,
      }),
    });
    const data = await res.json();
    if (data.dsl) {
      el.source.value = data.dsl;
      if (data.workflow_name) el.programName.value = data.workflow_name;
      setStatus(`DSL generated via ${data.method} (confidence: ${data.confidence}). Ready to compile.`, 'good');
    } else {
      setStatus(data.notes || 'Failed to generate DSL.', 'bad');
    }
  } catch (err) {
    setStatus(`NL conversion error: ${err.message}`, 'bad');
  } finally {
    el.nlGenerateBtn.disabled = false;
    el.nlGenerateBtn.textContent = 'Convert to DSL';
  }
}

// ─── Compile & Execute ───────────────────────────────────────────────
async function compileCode() {
  const source = el.source.value;
  if (!source.trim()) {
    setStatus('Please enter or load a workflow before compiling.', 'idle');
    return;
  }

  setStatus('Running compiler pipeline...', 'running');
  resetPipeline();

  let res, data;
  try {
    res = await fetch('/api/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source,
        program_name:   el.programName.value || 'BusinessWorkflow',
        agent_backend:  el.agentBackend.value || 'deterministic',
        llm_provider:   el.llmProvider.value || null,
        llm_model:      el.llmModel.value || null,
      }),
    });
    data = await res.json();
  } catch (err) {
    setStatus(`Could not reach backend: ${err.message}`, 'bad');
    return;
  }

  if (!res.ok) {
    setStatus(data.error || 'Compilation failed.', 'bad');
    return;
  }

  // ── Extract Fields ──
  const lexErrors      = data.lex_errors      || [];
  const parseErrors    = data.parse_errors    || [];
  const semanticErrors = data.semantic_errors || [];
  const tokens         = data.tokens          || [];
  const tac            = data.tac             || [];
  const vmTrace        = data.vm_trace        || [];
  const vmStatus       = data.vm_status       || '—';
  const vmTime         = data.vm_simulated_time ?? 0;
  const vmEnv          = data.vm_environment  || {};
  const mockServices   = data.mock_services   || {};
  const cfgDot         = data.cfg_dot         || '';
  const errorCount     = lexErrors.length + parseErrors.length + semanticErrors.length;

  // ── Count service calls ──
  const totalCalls = Object.values(mockServices).reduce((sum, svc) => {
    return sum + (typeof svc === 'object' ? (svc.calls || 0) : 0);
  }, 0);

  // ── Update Metrics ──
  el.successValue.textContent = data.success ? 'SUCCESS' : 'BLOCKED';
  el.successValue.className = `metric-val ${data.success ? 'good' : 'bad'}`;

  el.tokenCount.textContent = tokens.length;
  el.tokenCount.className = 'metric-val accent';

  el.errorCount.textContent = errorCount;
  el.errorCount.className = `metric-val ${errorCount > 0 ? 'bad' : 'good'}`;

  el.tacCount.textContent = tac.length;
  el.tacCount.className = 'metric-val accent';

  el.vmStatusValue.textContent = vmStatus;
  el.vmStatusValue.className = `metric-val ${
    vmStatus === 'SUCCESS' ? 'good' :
    vmStatus === 'NOT_STARTED' ? 'warn' :
    vmStatus === 'FAILED' ? 'bad' : 'warn'
  }`;

  el.vmTimeValue.textContent = `${vmTime.toFixed(2)}s`;
  el.vmTimeValue.className = 'metric-val teal';

  el.traceStepCount.textContent = vmTrace.length;
  el.traceStepCount.className = 'metric-val purple';

  el.serviceCallCount.textContent = totalCalls;
  el.serviceCallCount.className = `metric-val ${totalCalls > 0 ? 'accent' : ''}`;

  const executionAllowed = data.execution_allowed ?? data.success ?? false;

  // ── Populate Panels ──
  // Runtime output
  const runtimeLines = [];
  if (data.runtime_error) {
    runtimeLines.push(`✗ Runtime Error at line ${data.runtime_error.line ?? '?'}, col ${data.runtime_error.column ?? '?'}:`);
    runtimeLines.push(`  ${data.runtime_error.message}`);
    if (data.runtime_error.line_text) runtimeLines.push(`  ▶ ${data.runtime_error.line_text.trim()}`);
  }
  if (data.runtime_output) runtimeLines.push(data.runtime_output.trimEnd());
  if (!data.runtime_error && !data.runtime_output) {
    runtimeLines.push('Workflow compiled and submitted for VM execution.');
    runtimeLines.push('');
    runtimeLines.push('→ Check the "VM Trace" tab for step-by-step execution details.');
    runtimeLines.push('→ Check the "Mock Services" tab for service call activity.');
  }
  if (data.runtime_warnings?.length) {
    runtimeLines.push('');
    runtimeLines.push('Warnings:');
    data.runtime_warnings.forEach(w => runtimeLines.push(`  ⚠ ${w}`));
  }
  el.output.textContent = runtimeLines.join('\n');

  el.vm_trace.textContent   = formatVMTrace(vmTrace, executionAllowed);
  el.cfg.textContent        = formatCFG(cfgDot);
  el.services.textContent   = formatMockServices(mockServices, vmEnv);
  el.agent.textContent      = data.agent_report_text || 'No agent report generated.';
  el.listing.textContent    = data.listing || 'No listing output.';
  el.tokens.textContent     = formatTokens(tokens);
  el.ast.textContent        = data.ast || 'AST not available.';
  el.tac.textContent        = tac.join('\n') || 'No TAC generated.';
  el.asm.textContent        = data.asm || 'Assembly not generated.';
  el.errors.textContent     = formatErrors({
    'Lexical Errors':   lexErrors,
    'Syntax Errors':    parseErrors,
    'Semantic Errors':  semanticErrors,
  });
  el.translated.textContent = data.translated_source || 'No lowered core code.';

  // ── Animate Pipeline ──
  animatePipeline(data.success, errorCount);

  // ── Auto-switch Tab ──
  if (!data.success) {
    activateTabByKey('agent');
  } else {
    activateTabByKey('output');
  }

  // ── Status ──
  const modeLabel = el.agentBackend.value || 'deterministic';
  if (data.success) {
    setStatus(
      `✓ Pipeline complete — ${tokens.length} tokens, ${tac.length} IR instructions, VM: ${vmStatus}. Agent mode: ${modeLabel}.`,
      'good'
    );
  } else {
    setStatus(
      `✗ Workflow blocked — ${errorCount} error(s) found. See Agentic Debugger report for diagnostics.`,
      'bad'
    );
  }

  // Notify AI Assistant of new compile result
  window.dispatchEvent(new CustomEvent('compile-done', { detail: data }));
}

// ─── Wire Buttons ────────────────────────────────────────────────────
document.getElementById('loadInvoiceBtn').addEventListener('click', () => fetchSample('/api/sample'));
document.getElementById('loadOrderBtn').addEventListener('click',   () => fetchSample('/api/order-sample'));
document.getElementById('loadFaultyBtn').addEventListener('click',  () => fetchSample('/api/error-sample'));
el.nlGenerateBtn.addEventListener('click', convertNLtoDSL);
el.nlPrompt.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); convertNLtoDSL(); } });
document.getElementById('compileBtn').addEventListener('click', compileCode);

// ─── AI Assistant State ───────────────────────────────────────────────
// Tracks last compile result so AI can reference real compiler artifacts
let _lastCompileData = null;

function _updateAIButtonState(data) {
  _lastCompileData = data;
  const hasErrors = data && (data.semantic_errors?.length || data.lex_errors?.length || data.parse_errors?.length);
  const hasTrace  = data && data.vm_trace?.length;
  // Explain Error enabled only when there are actual errors
  el.aiExplainErrorBtn.disabled = !hasErrors;
  el.aiExplainErrorBtn.title    = hasErrors ? 'Click to explain the first compiler error' : 'No errors to explain';
  // Explain Trace enabled only when we have trace data
  el.aiExplainTraceBtn.disabled = !hasTrace;
  el.aiExplainTraceBtn.title    = hasTrace ? 'Click to explain the VM execution trace' : 'Compile first to see trace';
  // Explain Workflow always enabled if there's source
  el.aiExplainWorkflowBtn.disabled = !el.source.value.trim();
}

function _showAIOutput(title, text, suggestedDsl = '') {
  el.aiOutputTitle.textContent = title;
  el.aiOutputContent.textContent = text;
  el.aiOutput.style.display = 'block';
  if (suggestedDsl) {
    el.aiSuggestedDsl.textContent = suggestedDsl;
    el.aiSuggestedDslWrap.style.display = 'block';
  } else {
    el.aiSuggestedDslWrap.style.display = 'none';
  }
}

async function _callAIAssist(payload) {
  const resp = await fetch('/api/ai-assist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`AI assist failed: ${resp.status}`);
  return resp.json();
}

// Explain first error
el.aiExplainErrorBtn.addEventListener('click', async () => {
  if (!_lastCompileData) return;
  const allErrors = [
    ...(_lastCompileData.semantic_errors || []),
    ...(_lastCompileData.lex_errors || []),
    ...(_lastCompileData.parse_errors || []),
  ];
  if (!allErrors.length) return;
  const firstErr = allErrors[0];
  const btn = el.aiExplainErrorBtn;
  btn.classList.add('loading');
  btn.disabled = true;
  try {
    const result = await _callAIAssist({
      action: 'explain_error',
      source: el.source.value,
      error_type: firstErr.error_type || 'UNKNOWN',
      error_message: firstErr.message || firstErr.text || '',
      error_line: firstErr.line,
    });
    _showAIOutput('🔍 Error Explanation', result.text || result.error, result.suggested_dsl || '');
  } catch(e) {
    _showAIOutput('AI Error', e.message);
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
});

// Explain workflow
el.aiExplainWorkflowBtn.addEventListener('click', async () => {
  const source = el.source.value.trim();
  if (!source) return;
  const btn = el.aiExplainWorkflowBtn;
  btn.classList.add('loading');
  btn.disabled = true;
  try {
    const result = await _callAIAssist({ action: 'explain_workflow', source });
    _showAIOutput('📖 Workflow Explanation', result.text || result.error);
  } catch(e) {
    _showAIOutput('AI Error', e.message);
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
});

// Explain trace
el.aiExplainTraceBtn.addEventListener('click', async () => {
  if (!_lastCompileData) return;
  const btn = el.aiExplainTraceBtn;
  btn.classList.add('loading');
  btn.disabled = true;
  try {
    const result = await _callAIAssist({
      action: 'explain_trace',
      source: el.source.value,
      tac: _lastCompileData.tac || [],
      trace: _lastCompileData.vm_trace || [],
      environment: _lastCompileData.vm_environment || {},
    });
    _showAIOutput('🔬 Trace Explanation', result.text || result.error);
  } catch(e) {
    _showAIOutput('AI Error', e.message);
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
});

// Close AI output
el.aiOutputClose.addEventListener('click', () => {
  el.aiOutput.style.display = 'none';
});

// Apply suggested DSL to editor and recompile
el.aiApplySuggestedBtn.addEventListener('click', () => {
  const suggested = el.aiSuggestedDsl.textContent.trim();
  if (!suggested) return;
  el.source.value = suggested;
  el.aiOutput.style.display = 'none';
  compileCode();
});

// Hook into compile response to update AI button state
const _origCompileCode = compileCode;
window.addEventListener('compile-done', e => _updateAIButtonState(e.detail));

// ─── Init ────────────────────────────────────────────────────────────
setupTabs();
fetchSample('/api/sample');
