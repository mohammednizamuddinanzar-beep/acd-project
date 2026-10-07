# Business Automation Workflow DSL — Formal Specification

> **Version**: 2.0  
> **Status**: Formal Specification  
> **Target System**: Business Automation Workflow DSL Compiler  

---

## 1. Purpose & Scope

The **Business Automation Workflow DSL** is a domain-specific programming language engineered for declarative business process automation. It allows developers to express event-driven triggers, data extractions, type-safe state mutations, conditional business rules, entity persistence, notifications, retries, delays, and parallel block execution.

The language is compiled through a formal 5-phase compiler pipeline:
$$\text{Source DSL} \longrightarrow \text{Lexer} \longrightarrow \text{Parser} \longrightarrow \text{AST} \longrightarrow \text{Semantics \& Scopes} \longrightarrow \text{IR (TAC) \& CFG} \longrightarrow \text{Optimizer} \longrightarrow \text{Execution Engine}$$

---

## 2. Language Keywords

The language reserves the following uppercase keywords:

| Keyword | Category | Description |
|---|---|---|
| `WORKFLOW` | Structure | Begins a workflow declaration block |
| `END` | Structure | Terminates a workflow declaration or block |
| `ON` | Event | Declares event trigger (`ON domain.event`) |
| `SET` | Mutation | Declares or updates a typed state variable |
| `EXTRACT` | Data Ingestion | Extracts field from event payload |
| `VALIDATE` | Data Integrity | Asserts entity validity |
| `IF` | Control Flow | Conditional branch header |
| `ELSE` | Control Flow | Alternative branch header |
| `CALL` | Service Call | Invokes external service or function |
| `SAVE` | Persistence | Saves entity to storage destination |
| `NOTIFY` | Communication | Sends notification to recipient |
| `RETRY` | Resilience | Executes block with retry attempt count |
| `WAIT` | Timing | Delays workflow execution |
| `PARALLEL` | Concurrency | Executes concurrent workflow branches |
| `NUMBER` | Type | 64-bit integer type specifier |
| `STRING` | Type | String literal type specifier |
| `BOOLEAN` | Type | Boolean (`true`/`false`) type specifier |
| `OBJECT` | Type | Structured record entity type specifier |
| `LIST` | Type | Collection type specifier |

---

## 3. Tokens, Identifiers, Literals & Operators

### 3.1 Identifiers
- Identifiers must start with an ASCII letter (`A-Z`, `a-z`) or underscore `_`, followed by alphanumeric characters or underscores.
- Case-insensitive matching is supported, but lowercase convention is recommended for variable names.
- Example: `amount`, `vendor_id`, `invoice`, `customer_status`.

### 3.2 Literals
- **NUMBER**: Integer literals matching `-?[0-9]+` (e.g., `50000`, `0`, `-15`).
- **STRING**: Enclosed in double quotes `"..."` or single quotes `'...'` (e.g., `"HIGH"`, `'approved'`).
- **BOOLEAN**: Reserved literal keywords `true` and `false` (case-insensitive).

### 3.3 Operators
- **Assignment**: `=`
- **Comparison**: `>`, `<`, `>=`, `<=`, `==`, `!=`
- **Logical**: `AND`, `OR`, `NOT`
- **Delimiter**: `:`, `.`, `,`, `{`, `}`, `(`, `)`

---

## 4. Static Data Types & Variable Declarations

The static type system supports 5 explicit types:

1. `NUMBER` (Integer values)
2. `STRING` (Textual literals)
3. `BOOLEAN` (True / False)
4. `OBJECT` (Entity payload references)
5. `LIST` (Collections)

### Syntax:
```ebnf
set_statement ::= "SET" identifier [ ":" type_specifier ] "=" expression
type_specifier ::= "NUMBER" | "STRING" | "BOOLEAN" | "OBJECT" | "LIST"
```

### Examples:
```bdsl
SET amount : NUMBER = 50000
SET vendor : STRING = "ABC Corp"
SET approved : BOOLEAN = false
```

---

## 5. Control Flow & Block Constructs

### 5.1 Conditional Branches (`IF` / `ELSE`)
```ebnf
if_statement ::= "IF" condition "{" statement* "}" [ "ELSE" "{" statement* "}" ]
```

### 5.2 Resilience & Retries (`RETRY`)
```ebnf
retry_statement ::= "RETRY" integer_literal "{" statement* "}"
```

### 5.3 Execution Delay (`WAIT`)
```ebnf
wait_statement ::= "WAIT" integer_literal [ identifier ]
```

### 5.4 Concurrency (`PARALLEL`)
```ebnf
parallel_statement ::= "PARALLEL" "{" statement* "}"
```

---

## 6. Formal EBNF Grammar

```ebnf
workflow         ::= "WORKFLOW" identifier "{" statement* "}" [ "END" ]
statement        ::= event_stmt 
                   | extract_stmt 
                   | set_stmt 
                   | validate_stmt 
                   | if_stmt 
                   | call_stmt 
                   | save_stmt 
                   | notify_stmt 
                   | retry_stmt 
                   | wait_stmt 
                   | parallel_stmt 
                   | log_stmt

event_stmt       ::= "ON" identifier "." identifier
extract_stmt     ::= "EXTRACT" identifier "FROM" identifier
set_stmt         ::= "SET" identifier [ ":" type_spec ] "=" expr
validate_stmt    ::= "VALIDATE" identifier
if_stmt          ::= "IF" condition "{" statement* "}" [ "ELSE" "{" statement* "}" ]
call_stmt        ::= "CALL" identifier "(" [ arg_list ] ")"
save_stmt        ::= "SAVE" identifier "TO" identifier
notify_stmt      ::= "NOTIFY" identifier
retry_stmt       ::= "RETRY" NUMBER "{" statement* "}"
wait_stmt        ::= "WAIT" NUMBER [ identifier ]
parallel_stmt    ::= "PARALLEL" "{" statement* "}"
log_stmt         ::= "LOG" STRING

type_spec        ::= "NUMBER" | "STRING" | "BOOLEAN" | "OBJECT" | "LIST"
condition        ::= expr rel_op expr
rel_op           ::= ">" | "<" | ">=" | "<=" | "==" | "!="
expr             ::= identifier | NUMBER | STRING | BOOLEAN
arg_list         ::= expr ( "," expr )*
```

---

## 7. Implementation Status Comparison

| Feature | Status | Implementation Details |
|---|---|---|
| `WORKFLOW` declaration | **Implemented** | Lexer, Parser, AST (`ProgramNode`), Business Semantics |
| `ON domain.event` | **Implemented** | Parsed, validated, lowered, and executed by runtime |
| `EXTRACT var FROM src` | **Implemented** | Type inference, payload ingestion, symbol table registration |
| `SET var : TYPE = val` | **Upgraded** | Explicit static type annotations (`NUMBER`, `STRING`, `BOOLEAN`) added |
| `VALIDATE entity` | **Implemented** | Structural assertion & AST node (`ValidateStmtNode`) |
| `IF / ELSE` | **Implemented** | Scoped AST branching, block symbol tables, IR jump instructions |
| `CALL service(args)` | **Implemented** | Service invocation AST node (`CallStmtNode`) and IR generation |
| `SAVE entity TO dest` | **Implemented** | Entity storage and DB mock execution |
| `NOTIFY recipient` | **Implemented** | Notification routing and event dispatch |
| `RETRY count { ... }` | **Implemented** | Iterative execution IR quadruples (`RETRY_BEGIN` / `RETRY_END`) |
| `WAIT duration unit` | **Implemented** | Delay IR instruction (`WAIT`) and runtime execution logging |
| `PARALLEL { ... }` | **Implemented** | Concurrency IR quadruples (`PARALLEL_START` / `PARALLEL_END`) |
| Static Type Checking | **Upgraded** | Compile-time semantic check for assignment & comparison type mismatches |
| Lexical Scopes | **Upgraded** | Nested scope tree (Global, IF, ELSE, PARALLEL) with block isolation |
| Control Flow Graph | **Added** | Basic Block & Directed Edge generation with Graphviz DOT exporter |

---

## 8. Error Classification & Diagnostics

The compiler enforces strict error reporting categorized into three main error types:

### 8.1 Syntax Errors (`SYNTAX_ERROR`)
- Mismatched or missing block braces `{` / `}`.
- Invalid token sequencing (e.g., `ON` without event name, `EXTRACT` without `FROM`).
- Statements outside of active `WORKFLOW` declaration block.

### 8.2 Semantic Errors (`SEMANTIC_ERROR`)
- **Undefined Variables**: Referencing variables before declaration or referencing variables declared in an inaccessible block scope.
- **Duplicate Declarations**: Re-declaring an identifier within the same lexical scope.
- **Invalid Structure / Event Triggers**: Missing trigger `ON` statement, or invalid event name format (`domain.event`).
- **Unclosed Blocks**: Missing `}` for `WORKFLOW`, `IF`, `ELSE`, `RETRY`, or `PARALLEL` blocks.

### 8.3 Type Errors (`TYPE_ERROR`)
- **Assignment Type Mismatch**: Assigning a value whose type does not match the target variable's declared type (e.g., `SET amount : NUMBER = "hello"` -> `Type Error: Expected NUMBER but found STRING.`).
- **Invalid Relational Comparisons**: Comparing incompatible types (e.g., `IF amount > "hello"` -> `Type Error: Relational operator '>' cannot compare NUMBER with STRING.`).
- **Invalid Equality Comparisons**: Checking equality between string and numeric types.

