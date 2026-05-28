# Optional LLM + LangGraph Layer

This project now has three layers:

1. **Original compiler pipeline**
   - Lexer
   - Parser
   - Semantic validation / ICG
   - TAC generation
   - Pseudo-assembly generation

2. **Deterministic compiler agent**
   - Always works without API keys
   - Explains compiler errors
   - Checks AI workflow order
   - Suggests safe fixes
   - Produces an AI Agent Report

3. **Optional LangGraph + LLM layer**
   - Runs only when optional packages and API keys are available
   - Does not change compiler output
   - Orchestrates: `observe -> deterministic_diagnose -> optional_llm_review -> synthesize`
   - Adds LLM-based senior-engineer review on top of deterministic compiler artifacts

## Install core project

```bash
pip install -r requirements.txt
```

## Install optional agent stack

```bash
pip install -r requirements-agent.txt
```

## Run deterministic agent only

```bash
python src/main.py examples/real_training.aidl -o output --agent-report
```

## Run LangGraph orchestration without LLM

```bash
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend langgraph
```

If `langgraph` is not installed, the project automatically falls back to the deterministic agent and reports the fallback mode.

## Run optional OpenAI review

PowerShell:

```powershell
$env:OPENAI_API_KEY="your_key_here"
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend llm --llm-provider openai --llm-model gpt-4o-mini
```

Linux/macOS:

```bash
export OPENAI_API_KEY="your_key_here"
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend llm --llm-provider openai --llm-model gpt-4o-mini
```

## Run LangGraph + optional LLM

```bash
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend langgraph-llm --llm-provider openai --llm-model gpt-4o-mini
```

## Run optional Gemini review

```bash
export GOOGLE_API_KEY="your_key_here"
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend langgraph-llm --llm-provider gemini --llm-model gemini-1.5-flash
```

## Web IDE

```bash
python server.py
```

Open the Web IDE and choose the agent backend from the **Agent mode** section.

## Design guarantee

The optional LLM and LangGraph layers are advisory only. They never mutate source code, AST, TAC, assembly, or runtime execution. The deterministic compiler remains the source of truth.
