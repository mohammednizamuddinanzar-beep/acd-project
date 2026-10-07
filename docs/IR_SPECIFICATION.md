# Business Automation Workflow Intermediate Representation (IR) — Specification

> **Version**: 2.0  
> **Status**: Formal Specification  
> **Target System**: Business Automation Workflow IR / Three-Address Code (TAC) Engine  

---

## 1. Overview & Objectives

The **Workflow Intermediate Representation (IR)** is a linear, deterministic Three-Address Code (TAC) instruction stream generated from the Abstract Syntax Tree (AST) or decorated Business Workflow DSL source.

It decouples declarative workflow syntax from final execution targets (VMs, cloud runtimes, orchestration engines), explicitly encoding control flow, state operations, resilience blocks, and source code locations.

$$\text{Source DSL} \longrightarrow \text{Lexer/Parser} \longrightarrow \text{AST} \longrightarrow \text{Semantics} \longrightarrow \text{Workflow IR (TAC)} \longrightarrow \text{CFG / CodeGen}$$

---

## 2. IR Instruction Schema

Each IR instruction in the workflow compiler pipeline contains the following mandatory fields:

- `opcode`: Uppercase instruction type (e.g., `EVENT`, `EXTRACT`, `COMPARE_GT`, `JUMP_IF_FALSE`).
- `result`: Optional target variable or destination label receiving the result.
- `arg1`: Primary operand or source argument.
- `arg2`: Secondary operand or parameter.
- `line`: Source line number for diagnostic traceability.
- `column`: Source column position.

---

## 3. Supported IR Opcodes

The Business Workflow IR defines the following core opcodes:

| Opcode | Operands | Description |
|---|---|---|
| `EVENT` | `arg1 = domain.action` | Registers event trigger entry point |
| `EXTRACT` | `result = var, arg1 = src` | Extracts data field from event payload |
| `SET` | `result = var, arg1 = val` | Assigns typed value or variable state |
| `LOAD` | `result = temp, arg1 = src` | Loads variable value into temporary operand |
| `STORE` | `result = dest, arg1 = val` | Stores operand value into variable storage |
| `VALIDATE` | `arg1 = entity` | Asserts entity schema integrity |
| `COMPARE` | `result = temp, arg1 = val1, arg2 = val2` | Evaluates comparison (`COMPARE_GT`, `COMPARE_EQ`, etc.) |
| `JUMP` | `result = label` | Unconditional jump to target label |
| `JUMP_IF_FALSE` | `result = label, arg1 = temp` | Jumps to label if boolean operand is false |
| `JUMP_IF_TRUE` | `result = label, arg1 = temp` | Jumps to label if boolean operand is true |
| `CALL` | `arg1 = service, arg2 = args` | Invokes external service function |
| `SAVE` | `arg1 = entity, arg2 = dest` | Persists entity to specified database table |
| `NOTIFY` | `arg1 = recipient` | Transmits notification message |
| `WAIT` | `arg1 = duration, arg2 = unit` | Pauses execution for specified duration |
| `RETRY_BEGIN` | `arg1 = count` | Marks start of a retry resilience block |
| `RETRY_END` | — | Marks end of a retry resilience block |
| `PARALLEL_START`| — | Marks start of a concurrent execution block |
| `PARALLEL_END` | — | Marks end of a concurrent execution block |
| `END` | — | Terminates workflow execution |

---

## 4. Deterministic Lowering Example

### Input Source DSL:
```bdsl
WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE invoice TO database
}
```

### Generated Workflow IR Instruction Stream:
```tac
 0  EVENT        email.received
 1  t0         = EXTRACT      amount FROM email
 2  t1         = LOAD_CONST   50000
 3  t2         = COMPARE_GT   t0, t1
 4  JUMP_IF_FALSE t2  GOTO  L1
 5  NOTIFY       finance
 6  L1:
 7  SAVE         invoice TO database
 8  END
```

---

## 5. Properties & Guarantees

1. **Determinism**: Identical DSL input produces identical IR instructions across platforms.
2. **Control Flow Explicit**: All branching (`IF`/`ELSE`), looping (`RETRY`), and concurrency (`PARALLEL`) are lowered to explicit labels and jumps.
3. **Source Traceability**: Every instruction preserves line and column metadata for error reporting and agentic debugging.
4. **Platform Independence**: Can be rendered to assembly, executed in a VM, or exported as JSON/DOT.
