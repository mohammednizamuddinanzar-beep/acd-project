# Agentic Compiler Upgrade

This project now includes an agentic debugging layer around the existing compiler pipeline.

## What was added

- `src/agentic_debugger.py` — deterministic AI-agent-style reviewer for compiler outputs.
- Web IDE `AI Agent Report` tab.
- CLI flag: `--agent-report`.
- Workflow validation for AI DSL order and dependencies.
- Root-cause explanations for lexical, parse, semantic, runtime, and ML workflow issues.
- Suggested fixes and a production-readiness score.

## What was preserved

The original compiler pipeline remains deterministic and unchanged in behavior:

```text
Lexer -> Parser -> AST -> Semantic Analysis -> TAC -> Pseudo Assembly
```

The agent runs after compilation. It does not mutate the source, AST, TAC, assembly, symbol table, or runtime logic.

## Agent workflow

```text
Source + Compiler Artifacts
        |
        v
Observer Agent
        |
        v
Diagnostic Agent
        |
        v
Workflow Validation Agent
        |
        v
Fix Planner Agent
        |
        v
Report Generator Agent
```

## Run from CLI

```bash
python src/main.py examples/real_training.aidl -o output --agent-report
```

## Run Web IDE

```bash
python server.py
```

Open the browser URL printed in the terminal, then use **Load Real Training Demo** and **Compile**.
