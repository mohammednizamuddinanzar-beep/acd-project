# Business Automation Workflow Runtime Architecture

> **Version**: 2.0  
> **Target System**: Compiler Runtime, Mock Integration Layer & Web IDE  

---

## 1. System Architecture Overview

The Business Automation Workflow Compiler system is structured into a 5-phase deterministic compilation pipeline and a 3-phase execution runtime architecture:

```
[ DSL Source ]
      │
      ▼
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌────────────────┐
│   Lexer   │ ──► │  Parser   │ ──► │    AST    │ ──► │ Semantic Check │
└───────────┘     └───────────┘     └───────────┘     └────────────────┘
                                                              │
                                                              ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  Execution   │ ◄── │ Mock Service │ ◄── │ Workflow VM  │ ◄──┘
│ Trace & Web  │     │ Integration  │     │   (IR/TAC)   │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 2. Component Descriptions

### 2.1 Workflow Virtual Machine (`src/workflow_vm.py`)
- Executes Three-Address Code (TAC) IR quadruples directly.
- Maintains runtime variable storage, temporaries, instruction pointer, and simulated clock.
- Handles control flow jumps (`JUMP_IF_FALSE`), retries, delays (`WAIT`), and error catching.

### 2.2 Mock Service Layer (`src/mock_services.py`, `src/service_registry.py`)
- **`EmailService`**: Captures outbound emails in `sent_messages`.
- **`DatabaseService`**: Captures entity persistence in `saved_records`.
- **`NotificationService`**: Captures real-time notifications in `notifications`.
- **`APIService`**: Captures REST/HTTP requests in `requests`.
- **Failure Simulation**: Allows configuring intentional service failure counts to test `RETRY` logic and error recovery without external network calls.

### 2.3 Execution Trace Engine
- Logs a complete step-by-step history (`TraceStep`) of every VM instruction.
- Serves as the primary data model for the Web IDE visualizer and CLI diagnostic output.

---

## 3. Web IDE Integration

The Web IDE exposes the entire pipeline visually:
1. **Source Code Editor**: Load or edit workflow samples.
2. **Compiler Outputs**: Tokens, AST Tree, Semantic Diagnostics, Symbol Table, CFG Graph.
3. **VM Execution View**: Instruction Pointer steps, Execution Trace table, Environment state, Mock Service activity summaries.
