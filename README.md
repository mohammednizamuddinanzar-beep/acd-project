# Business Automation Workflow DSL Compiler
### Formal 5-Phase Compiler · Workflow Virtual Machine · Mock Integrations · Interactive Web IDE · Agentic Debugger

[![Build Status](https://img.shields.io/badge/tests-149%20passed-brightgreen.svg)](#test-suite--verification)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#license)

A domain-specific compiler and execution platform designed for **Business Automation Workflows** (invoice routing, order fulfillment, customer support escalation, approval hierarchies). The system bridges classical formal compiler construction principles with modern runtime simulation, virtual machines, mock service integrations, an interactive Web IDE, and an AI agentic debugging engine.

---

## 📑 Table of Contents

- [Executive Summary](#executive-summary)
- [Architectural Pipeline](#architectural-pipeline)
- [Language Specification](#language-specification)
- [Key Features](#key-features)
- [Project Directory Structure](#project-directory-structure)
- [Getting Started](#getting-started)
- [Usage Guide](#usage-guide)
  - [Interactive Web IDE](#1-interactive-web-ide)
  - [Command-Line Interface (CLI)](#2-command-line-interface-cli)
  - [Natural Language to DSL Translation](#3-natural-language-to-dsl-ai-front-end)
  - [Agentic Debugger](#4-agentic-debugger)
  - [Repository Cleanup](#5-safe-project-cleanup)
- [Curated Workflow Examples](#curated-workflow-examples)
- [Virtual Machine & Mock Integrations](#virtual-machine--mock-integrations)
- [Test Suite & Verification](#test-suite--verification)
- [Performance Benchmarks](#performance-benchmarks)

---

## Executive Summary

Traditional business process automation often relies on bulky low-code drag-and-drop tools or ad-hoc scripts that lack formal syntax validation, type safety, and static analysis. 

This project implements a **formal Domain-Specific Language (DSL)** compiler for business workflows that provides:
1. **Compile-time validation**: Lexical, syntactic, and static semantic checks catch undefined fields, type mismatches, duplicate declarations, and missing trigger events before execution.
2. **Deterministic execution**: A dedicated **Workflow Virtual Machine (VM)** executes Three-Address Code (TAC/IR) with step-by-step tracing, simulated time, and mock enterprise integrations (databases, email notifications, ERP APIs).
3. **Execution Gate**: Faulty workflows are blocked at compile time and never reach the VM.
4. **Agentic Debugging Engine**: Diagnoses compilation and runtime issues, providing human-readable root cause explanations and suggested DSL patches.
5. **Interactive Web IDE**: A responsive visual workspace featuring live compiler tab inspection (Tokens, AST, Semantic Errors, TAC Quadruples, CFG, Assembly, VM Trace, Mock Services).

---

## Architectural Pipeline

```
       Source DSL (.workflow / .bdsl)
                     ↓
       [PHASE 1] LEXICAL ANALYSIS (lexer.py)
                     ↓ Token Stream
       [PHASE 2] SYNTAX ANALYSIS (parser.py)
                     ↓ Abstract Syntax Tree (AST)
       [PHASE 3a] SEMANTIC ANALYSIS & TYPE SYSTEM (business_semantics.py)
                     ↓ Validated Scoped AST
       [PHASE 3b] INTERMEDIATE CODE GENERATION (icg.py)
                     ↓ Linear Three-Address Code (TAC)
       [PHASE 3c] IR OPTIMIZATION (ir_optimizer.py)
                     ↓ Optimized TAC Quadruples
       [PHASE 4] TARGET CODE GENERATION (codegen.py)
                     ↓ Educational x86-like Pseudo-Assembly (.asm)
                     ↓
               EXECUTION GATE (Pass/Fail)
              ↙                          ↘
     [FAIL: BLOCKED]               [PASS: APPROVED]
            ↓                              ↓
  Agentic Debugger            [PHASE 5] WORKFLOW VM (workflow_vm.py)
  - Root-cause analysis       - Step-by-step trace & simulated time
  - Error explanation         - Mock Services (Database, Notifications, API)
  - Suggested fixes           - Runtime environment state
```

---

## Language Specification

The Business Automation Workflow DSL provides clean, declarative primitives for describing business processes:

| Keyword / Construct | Purpose | Example |
|---|---|---|
| `WORKFLOW <Name> { ... }` | Declares a business process scope | `WORKFLOW InvoiceProcessing { ... }` |
| `ON <domain>.<event>` | Defines the event trigger | `ON email.received`, `ON order.created` |
| `EXTRACT <var> FROM <src>` | Ingests payload fields into workflow state | `EXTRACT amount FROM email` |
| `VALIDATE <entity>` | Asserts entity schema integrity | `VALIDATE order` |
| `SET <var> [: TYPE] = <expr>` | Declares a typed local variable | `SET status : STRING = 'pending'` |
| `IF <cond> { ... } ELSE { ... }`| Conditional decision branching | `IF amount > 50000 { NOTIFY finance }` |
| `CALL <service>` | Invokes a third-party service/API | `CALL notify_erp`, `CALL process_payment` |
| `NOTIFY <recipient>` | Dispatches auditable notifications | `NOTIFY finance`, `NOTIFY manager` |
| `SAVE <entity> TO <target>` | Persists workflow entity to database/storage | `SAVE invoice TO database` |
| `RETRY <count> { ... }` | Fault-tolerant retry block | `RETRY 3 { CALL charge_card }` |
| `WAIT <duration>` | Simulates time delays | `WAIT 10s` |
| `LOG '<message>'` | Emits workflow audit logs | `LOG 'Order completed'` |

---

## Key Features

- **Formal 5-Phase Compiler Architecture**: Complete separation of concerns from tokenization to target assembly emission.
- **Static Type Safety**: Type checking for numeric comparisons (`amount > 50000`), string equality (`priority == 'HIGH'`), and assignment validations.
- **Symbol Table & Lexical Scoping**: Tracks variable lifetimes, prevents duplicates, and prevents use-before-definition.
- **Linear TAC & IR Optimizer**: Emits clean Three-Address Code with dead code elimination, constant folding, and condition simplification.
- **Workflow Virtual Machine**: In-memory bytecode execution engine with simulated timestamping, step tracing, and deterministic outcomes.
- **Mock Service Architecture**: In-memory mock drivers for transactional databases, customer email notifications, and external APIs.
- **Interactive Multi-View Web IDE**: Features 12 inspector panels including Control Flow Graph (CFG) rendering, VM trace inspector, mock service monitor, token viewer, and AST visualizer.
- **AI Agentic Debugger**: Multi-dimensional diagnostic engine providing root-cause analysis, line references, and auto-generated DSL patches.
- **Natural Language Front-End**: Converts plain English descriptions into valid Business Workflow DSL.

---

## Project Directory Structure

```text
acd-project/
├── .env.example                     # Configuration template for optional LLM keys
├── .gitignore                       # Clean Git ignore specification
├── README.md                        # Project documentation
├── report.md                        # Detailed benchmark and architectural report
├── requirements.txt                 # Core dependencies
├── requirements-agent.txt           # Optional agent dependencies
├── server.py                        # Web IDE server launcher
├── Dockerfile                       # Container deployment definition
│
├── benchmarks/
│   ├── benchmark_compiler.py        # Automated compiler throughput benchmark suite
│   └── benchmark_results.json       # Baseline performance evidence
│
├── docs/                            # In-depth architectural & specification documentation
│
├── examples/                        # Validated sample business workflows
│   ├── invoice_processing.workflow  # Invoice approval workflow
│   ├── order_processing.workflow    # Order validation & dispatch workflow
│   ├── customer_support.workflow    # Ticket prioritization & SLA escalation
│   ├── order_fulfillment.bdsl       # Order fulfillment with discounts
│   ├── invoice_workflow.bdsl        # Minimal invoice workflow
│   └── faulty_workflow.bdsl         # Diagnostic sample for Agentic Debugger
│
├── scripts/
│   └── clean.py                     # Safe artifact cleanup utility
│
├── src/                             # Core Compiler & VM Implementation
│   ├── main.py                      # CLI driver & pipeline coordinator
│   ├── lexer.py                     # Phase 1: Lexical analyzer (tokenizer)
│   ├── parser.py                    # Phase 2: Recursive-descent AST parser
│   ├── ast_nodes.py                 # Typed AST node definitions
│   ├── business_semantics.py        # Phase 3a: Static semantic analysis & type system
│   ├── symbol_table.py              # Symbol table & scope manager
│   ├── icg.py                       # Phase 3b: Three-Address Code (TAC) generator
│   ├── ir_optimizer.py              # Phase 3c: Intermediate representation optimizer
│   ├── codegen.py                   # Phase 4: Target pseudo-assembly generator
│   ├── workflow_vm.py               # Phase 5: Workflow Virtual Machine runtime
│   ├── mock_services.py             # Mock enterprise service drivers
│   ├── service_registry.py          # Service integration registry
│   ├── interpreter.py               # AST interpreter for core procedural grammar
│   ├── listing.py                   # Compiler listing file generator (.lst)
│   ├── nl_to_dsl.py                 # AI Front-End (Natural Language → DSL)
│   ├── ai_assistant.py              # AI explanation provider
│   └── agentic_debugger.py          # Rule-based and LLM diagnostic engine
│
├── tests/                           # Complete Test Suite (149 Test Cases)
│   ├── test_business_semantics.py   # Semantic analyzer test cases
│   ├── test_type_system.py          # Static type system tests
│   ├── test_symbol_table_scopes.py  # Scope and identifier resolution tests
│   ├── test_ir_generation.py        # Three-Address Code verification
│   ├── test_ir_optimizer.py         # Optimizer passes verification
│   ├── test_cfg.py                  # Control flow graph construction tests
│   ├── test_workflow_vm.py          # Virtual Machine execution tests
│   ├── test_mock_services.py        # Enterprise mock driver tests
│   ├── test_execution_trace.py      # VM step-by-step trace tests
│   ├── test_nl_to_dsl.py            # Natural Language conversion tests
│   ├── test_ai_assistant.py         # Assistant explanation tests
│   ├── test_agentic_debugger_workflow.py # Agentic debugger diagnostics tests
│   ├── test_end_to_end.py           # Core end-to-end integration tests
│   └── test_e2e_comprehensive.py    # Comprehensive end-to-end pipeline suite
│
└── web_demo/                        # Interactive Web IDE Frontend & Backend
    ├── server.py                    # HTTP API server
    └── static/                      # Frontend assets (HTML5, Vanilla CSS, JS)
```

---

## Getting Started

### Prerequisites
- Python 3.10+ (tested on Python 3.10, 3.11, 3.12)
- Zero external packages required for core compiler, VM, and Web IDE! (Standard library only).

### Installation
Clone the repository:
```bash
git clone https://github.com/mohammednizamuddinanzar-beep/acd-project.git
cd acd-project
```

(Optional) Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate
```

Install optional dependencies (required only for ML dataset runtime / third-party LLM providers):
```bash
pip install -r requirements.txt
```

---

## Usage Guide

### 1. Interactive Web IDE
Launch the Web IDE:
```bash
python server.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8080
```
- Click on any sample workflow button (`Invoice Processing`, `Order Processing`, `Customer Support`, `Faulty Workflow`).
- Click **`Compile & Execute`** (or press `Ctrl + Enter`).
- Explore the interactive panels: **VM Trace**, **Mock Services**, **Control Flow Graph**, **Errors & Diagnostics**, **TAC Quadruples**, and **Agentic Debugger**.

---

### 2. Command-Line Interface (CLI)

#### Compile and Execute a Workflow:
```bash
python src/main.py examples/invoice_processing.workflow --run
```

#### Compile and Generate Target Assembly + Listing:
```bash
python src/main.py examples/invoice_processing.workflow -o output
```
*Outputs are saved to `output/invoice_processing.asm` and `output/invoice_processing.lst`.*

#### Run the Agentic Debugger on a Buggy Workflow:
```bash
python src/main.py examples/faulty_workflow.bdsl --agent-report
```

---

### 3. Natural Language to DSL (AI Front-End)
Translate plain English workflow descriptions directly into valid DSL code:
```bash
python src/main.py --nl "When an invoice arrives by email, extract the amount and notify finance if it is above 50000."
```

---

### 4. Agentic Debugger
The Agentic Debugger evaluates workflows along **7 Core Diagnostic Dimensions**:
1. **Undefined Variables**: Missing `EXTRACT` or `SET` statements before use.
2. **Duplicate Variable Declarations**: Redeclaring variables within the same scope.
3. **Invalid Actions**: Typographical errors or unrecognized keywords (e.g. `DISPATCH`).
4. **Invalid Trigger Events**: Event names that do not follow the `<domain>.<action>` format.
5. **Static Type Mismatches**: Numeric variables compared with strings or assigned string literals.
6. **Execution Order Violations**: Using variables prior to their declaration.
7. **Malformed Workflow Structure**: Missing headers, unclosed braces, or statements outside `WORKFLOW`.

---

### 5. Safe Project Cleanup
To safely clean intermediate compilation files, temporary logs, and bytecode caches:
```bash
python src/main.py --clean
```
or:
```bash
python scripts/clean.py
```

---

## Curated Workflow Examples

### Example 1: Invoice Processing
```dsl
WORKFLOW InvoiceProcessing {
    ON email.received

    EXTRACT amount FROM email
    EXTRACT vendor FROM email
    EXTRACT invoice_id FROM email

    IF amount > 50000 {
        NOTIFY finance
        NOTIFY manager
    }

    CALL notify_erp
    SAVE invoice TO database
    NOTIFY vendor
}
```

### Example 2: Order Fulfillment with Entity Validation
```dsl
WORKFLOW OrderProcessing {
    ON order.created

    VALIDATE order
    EXTRACT amount FROM order
    EXTRACT customer FROM order
    EXTRACT order_id FROM order

    IF amount > 10000 {
        NOTIFY manager
    }

    CALL process_order
    SAVE order TO database
    NOTIFY customer
}
```

### Example 3: Customer Support Ticket Escalation
```dsl
WORKFLOW CustomerSupport {
    ON ticket.created

    EXTRACT priority FROM ticket
    EXTRACT ticket_id FROM ticket

    IF priority == "HIGH" {
        NOTIFY manager
        NOTIFY oncall_engineer
    }

    SAVE ticket TO database
}
```

---

## Virtual Machine & Mock Integrations

The **Workflow VM** executes compiled Three-Address Code with full enterprise integration simulation:
- **`MockDatabase`**: Tracks entity records created via `SAVE <entity> TO database`.
- **`MockNotificationService`**: Records dispatch logs for `NOTIFY <recipient>`.
- **`MockExternalService`**: Simulates external API calls invoked via `CALL <service>`.
- **`Simulated Clock`**: Tracks simulated duration and latency for `WAIT` and `RETRY` steps.

---

## Test Suite & Verification

The project includes an automated test suite comprising **149 test cases** covering every compiler phase, edge case, and end-to-end flow:

```bash
python -m unittest discover -s tests
```

### Test Results:
```text
Ran 149 tests in 0.148s

OK
```

Test coverage includes:
- `test_business_semantics.py`: Semantic rules (undefined variables, duplicate definitions, event formats).
- `test_type_system.py`: Type mismatch and relational comparison tests.
- `test_symbol_table_scopes.py`: Lexical scoping and variable lookup tests.
- `test_ir_generation.py`: TAC instruction and opcode generation tests.
- `test_ir_optimizer.py`: Constant folding and dead code elimination tests.
- `test_workflow_vm.py`: Bytecode execution, environments, and branching tests.
- `test_mock_services.py`: Mock DB, email, and API activity tracking tests.
- `test_nl_to_dsl.py`: Rule-based and LLM prompt translation tests.
- `test_agentic_debugger_workflow.py`: Error diagnostic and patch generation tests.
- `test_e2e_comprehensive.py`: Full end-to-end pipeline execution tests.

---

## Performance Benchmarks

Run the compiler performance benchmark suite:
```bash
python benchmarks/benchmark_compiler.py
```

### Benchmark Summary:
| Operation | Mean Latency | Median Latency | Scale / Throughput |
|---|---|---|---|
| **Lexer Tokenization** | `0.34 ms` | `0.39 ms` | ~3,000 passes/sec |
| **Semantic Analysis** | `0.48 ms` | `0.37 ms` | ~2,500 passes/sec |
| **Full Compilation (Simple)** | `1.34 ms` | `1.21 ms` | ~750 workflows/sec |
| **Full Compilation (Medium)** | `2.65 ms` | `2.00 ms` | ~380 workflows/sec |
| **Full Compilation (Complex)** | `3.29 ms` | `2.51 ms` | ~300 workflows/sec |
| **VM Execution (Medium)** | `2.64 ms` | `1.95 ms` | Full trace + Mock I/O |
| **NL-to-DSL Translation** | `0.11 ms` | `0.04 ms` | Instantaneous |
| **AI Mock Provider Explanation** | `0.01 ms` | `0.01 ms` | Zero runtime overhead |
| **Scale Test (100 sequential runs)**| `1.05 ms / run` | `1.05 ms` | 100% pass rate |

*Detailed benchmark evidence is recorded in [`benchmarks/benchmark_results.json`](file:///d:/ACD_CBP/agentic-ai-dsl-workflow-compiler/benchmarks/benchmark_results.json).*

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
