# Business Automation Workflow Virtual Machine (VM) — Specification

> **Version**: 2.0  
> **Status**: Formal Specification  
> **Target System**: Workflow Virtual Machine & Execution Trace Engine  

---

## 1. Overview & VM Architecture

The **Workflow Virtual Machine (VM)** is a deterministic execution engine that directly executes Three-Address Code (TAC) Intermediate Representation (IR) instructions produced by the compiler pipeline.

$$\text{Source DSL} \longrightarrow \text{Lexer/Parser} \longrightarrow \text{AST} \longrightarrow \text{Semantics} \longrightarrow \text{Workflow IR (TAC)} \longrightarrow \text{Workflow VM} \longrightarrow \text{Mock Services \& Trace}$$

### Core VM State Components:
- **`ip` (Instruction Pointer)**: Integer index pointing to the current executing instruction in the IR sequence.
- **`environment`**: Symbol table dictionary storing runtime variable values (`NUMBER`, `STRING`, `BOOLEAN`, `OBJECT`).
- **`temporaries`**: Dictionary storing temporary calculation and comparison results (`t0`, `t1`).
- **`simulated_time`**: Floating-point clock tracking elapsed seconds without blocking execution thread.
- **`service_registry`**: Dispatcher for mock service integrations (`EmailService`, `DatabaseService`, `NotificationService`, `APIService`).
- **`retry_stack`**: Stack tracking retry loop attempts, start IPs, and max attempt limits.
- **`trace`**: Structured list of `TraceStep` records capturing step-by-step execution history.

---

## 2. Instruction Execution Semantics

| Opcode Category | Instruction | Execution Behavior |
|---|---|---|
| **Event Ingestion** | `EVENT domain.action` | Initializes event domain in runtime environment |
| **Data Extraction** | `EXTRACT var FROM src` | Extracts property from event payload into `environment[var]` |
| **State Mutation** | `SET var = val` | Computes value expression and updates `environment[var]` |
| **Data Transfer** | `LOAD temp, var` / `STORE var, temp` | Moves values between temporaries and variables |
| **Validation** | `VALIDATE entity` | Asserts entity existence and schema compliance |
| **Comparison** | `COMPARE_GT t0, v1, v2` | Evaluates relational operator and stores boolean in temporary |
| **Control Flow** | `JUMP label` | Sets `ip` to label index in `label_map` |
| **Branching** | `JUMP_IF_FALSE t0, label` | Jumps to target label if temporary condition is `false` |
| **Service Call** | `CALL service_name` | Dispatches service call via `ServiceRegistry` |
| **Persistence** | `SAVE entity TO db` | Records database save operation in `DatabaseService` |
| **Notification** | `NOTIFY channel` | Dispatches message via `NotificationService` |
| **Delay** | `WAIT duration unit` | Advances `simulated_time += duration` without thread sleeping |
| **Resilience** | `RETRY_BEGIN count` / `RETRY_END` | Manages retry loop iterations; resets IP on service failure |
| **Concurrency** | `PARALLEL_START` / `PARALLEL_END` | Simulates parallel branch execution deterministically |
| **Termination** | `END` / `HALT` | Sets status to `SUCCESS` and terminates VM execution |

---

## 3. Resilience & Failure Recovery (`RETRY`)

When a service call inside a `RETRY` block encounters a `MockServiceError`:
1. The VM inspects the current top of `retry_stack`.
2. If `attempt < max_attempts`, `attempt` is incremented, and `ip` is reset to `start_ip + 1` (re-executing the block).
3. If `attempt >= max_attempts`, the VM raises a `VMRuntimeError("RETRY_EXHAUSTION")` and halts execution.

---

## 4. Execution Trace & Logging Model

Every executed step records a structured `TraceStep` containing:
- `step`: Global step sequence index
- `ip`: Instruction pointer at execution start
- `opcode`: Opcode executed
- `operands`: Formatted argument string
- `result`: Result target identifier
- `simulated_time`: Current clock reading
- `env_snapshot`: Complete snapshot of `environment` variables
- `status`: `SUCCESS` or `FAILED`
- `error`: Error message string if step failed
