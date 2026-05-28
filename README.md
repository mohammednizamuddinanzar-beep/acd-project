# AI Workflow DSL Compiler — LangGraph Agentic Debugging Engine

A production-style AI workflow compiler that converts high-level machine learning pipeline DSL code into validated compiler artifacts, executes supported ML workflows, and uses a LangGraph-based agent layer to diagnose errors, explain failures, suggest fixes, and generate developer-friendly debugging reports.

## What is this project?

This project is an AI-agent-enhanced compiler for machine learning workflow automation.

In simple words:

Imagine a data scientist or ML engineer wants to define an ML pipeline using simple commands such as:

- Load a dataset
- Define a model
- Set training parameters
- Train the model
- Evaluate the model
- Run prediction
- Deploy the model
- Monitor the model
- Log execution status

Normally, this requires writing scattered Python scripts, validation code, training code, configuration files, and debugging logic.

This project solves that by creating a custom AI Workflow DSL.

A user can write:

```text
PIPELINE CustomerChurnOps
DATASET customers FROM 's3://ml-bucket/customer_churn.csv'
MODEL churn_model TASK 'classification'
SET batch_size = 64
SET learning_rate = 1
TRAIN churn_model ON customers EPOCHS 12
EVALUATE churn_model
PREDICT churn_model INPUT 25 INTO churn_score
DEPLOY churn_model TO 'staging'
MONITOR churn_model
LOG 'Pipeline executed successfully'
ENDPIPELINE
```

The compiler processes this program and produces:

- Tokens
- AST
- Semantic validation
- Intermediate representation
- Three-Address Code
- Pseudo-assembly
- Runtime output
- AI Agent Report
- Error explanation
- Suggested fixes

The project combines classical compiler engineering with modern AI agent orchestration.

## Why this project matters

Modern ML pipelines are difficult to manage because they involve many moving parts:

- Dataset loading
- Model configuration
- Training order
- Evaluation logic
- Prediction handling
- Deployment readiness
- Monitoring requirements
- Runtime failures
- Debugging across multiple files

A normal compiler only gives a syntax or semantic error.

This project goes further.

It uses an AI agent layer to understand the compiler state and explain what went wrong in a human-readable way.

The goal is not to replace the compiler.

The compiler remains deterministic.

The agent works as an intelligent debugging assistant around the compiler.

This makes the system closer to real AI developer tooling used in production engineering environments.

## Core idea

```text
AI Workflow DSL Code
        ↓
Lexer
        ↓
Parser
        ↓
Semantic Analyzer
        ↓
IR / TAC Generator
        ↓
Pseudo Assembly Generator
        ↓
Runtime Executor
        ↓
LangGraph Agentic Debugger
        ↓
AI Agent Report
```

The compiler handles the deterministic transformation of source code.

The agent handles explanation, diagnosis, workflow validation, and fix suggestions.

## Architecture

```text
                         [ User DSL Program ]
                                  │
                                  ▼
                         [ CLI / Web IDE ]
                                  │
                                  ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                     Compiler Core                            │
 │                                                              │
 │  ┌──────────────┐                                            │
 │  │ Lexer        │  Converts source code into tokens           │
 │  └──────┬───────┘                                            │
 │         ▼                                                    │
 │  ┌──────────────┐                                            │
 │  │ Parser       │  Builds AST from token stream               │
 │  └──────┬───────┘                                            │
 │         ▼                                                    │
 │  ┌─────────────────────┐                                     │
 │  │ Semantic Analyzer   │  Validates symbols and workflow use  │
 │  └──────┬──────────────┘                                     │
 │         ▼                                                    │
 │  ┌─────────────────────┐                                     │
 │  │ IR / TAC Generator  │  Produces intermediate code          │
 │  └──────┬──────────────┘                                     │
 │         ▼                                                    │
 │  ┌─────────────────────┐                                     │
 │  │ Code Generator      │  Produces pseudo-assembly output     │
 │  └──────┬──────────────┘                                     │
 │         ▼                                                    │
 │  ┌─────────────────────┐                                     │
 │  │ Runtime Executor    │  Executes supported AI workflows      │
 │  └─────────────────────┘                                     │
 └──────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                 Agentic Debugging Layer                      │
 │                                                              │
 │  observe                                                     │
 │     ↓                                                        │
 │  deterministic_diagnose                                      │
 │     ↓                                                        │
 │  optional_llm_review                                         │
 │     ↓                                                        │
 │  synthesize                                                  │
 │                                                              │
 └──────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                         [ AI Agent Report ]
```

## How LangGraph is used

LangGraph is used as the orchestration layer for the AI debugging workflow.

It does not replace the compiler.

It controls the agent reasoning steps after the compiler produces output or errors.

The LangGraph flow is:

```text
observe → deterministic_diagnose → optional_llm_review → synthesize
```

### 1. observe

The observe node collects compiler context.

It receives:

- Source code
- Tokens
- AST summary
- TAC output
- Assembly output
- Runtime output
- Syntax errors
- Semantic errors
- Runtime errors
- Failed line number
- Failed source line
- Selected agent backend

Purpose:

```text
Understand what happened during compilation.
```

### 2. deterministic_diagnose

This node runs the local rule-based debugging agent.

It checks for workflow mistakes such as:

- Missing dataset declaration
- Missing model declaration
- Training before dataset loading
- Evaluation before training
- Prediction before training
- Deployment without evaluation
- Monitoring without deployment
- Unsupported task type
- Missing hyperparameters

Purpose:

```text
Provide reliable compiler diagnosis without depending on external LLM APIs.
```

### 3. optional_llm_review

This node runs only when LLM support is enabled and an API key is available.

It can use:

- LangChain
- OpenAI
- Gemini
- User-selected LLM model

Purpose:

```text
Generate a more human-readable explanation of compiler errors and workflow issues.
```

If no key is available, the system safely falls back to the deterministic agent.

### 4. synthesize

This node combines all debugging outputs into one final report.

It merges:

- Deterministic diagnosis
- Optional LLM explanation
- Workflow graph
- Error explanation
- Fix suggestions
- Production-readiness score
- Final compiler status

Purpose:

```text
Produce the AI Agent Report shown in the CLI and Web IDE.
```

## What the AI agent does

The AI agent works like an intelligent compiler assistant.

It does not mutate the source code automatically.

It does not change the compiler output.

It observes the compiler and explains the result.

The agent can:

- Explain compiler errors in simple language
- Suggest fixes for invalid DSL programs
- Validate ML workflow order
- Detect missing pipeline stages
- Generate workflow graphs
- Produce a production-readiness score
- Generate a structured AI Agent Report
- Use optional LLM reasoning when enabled
- Fall back safely when LLM packages or API keys are missing

Example:

If the user writes:

```text
PIPELINE BrokenPipeline
MODEL fraud_model TASK 'classification'
TRAIN fraud_model ON transactions EPOCHS 10
DATASET transactions FROM 's3://fintech-data/transactions.csv'
ENDPIPELINE
```

The compiler detects the issue.

The agent explains:

```text
The model is being trained on dataset 'transactions' before the dataset is declared.
Move the DATASET declaration before the TRAIN step.
```

Correct version:

```text
PIPELINE FixedPipeline
DATASET transactions FROM 's3://fintech-data/transactions.csv'
MODEL fraud_model TASK 'classification'
TRAIN fraud_model ON transactions EPOCHS 10
ENDPIPELINE
```

## Technical stack

| Area | Technology |
|---|---|
| Language | Python |
| Compiler Stages | Lexer, Parser, Semantic Analyzer, IR, TAC, Code Generation |
| AI DSL | Custom ML Workflow DSL |
| Agent Orchestration | LangGraph |
| LLM Integration | LangChain, OpenAI, Gemini |
| ML Runtime | pandas, scikit-learn |
| Web IDE | HTML, CSS, JavaScript, Flask-style server |
| CLI | Python argparse |
| Outputs | Tokens, AST, TAC, pseudo-assembly, listing, runtime logs, agent reports |
| Testing | Python demo scripts and sample DSL programs |

## Project features

### 1. AI Workflow DSL

The project supports high-level ML pipeline commands:

```text
PIPELINE
DATASET
MODEL
SET
TRAIN
EVALUATE
PREDICT
DEPLOY
MONITOR
LOG
ENDPIPELINE
```

This allows users to describe ML workflows in a readable DSL instead of writing full Python scripts manually.

### 2. Compiler pipeline

The project includes a full compiler-style pipeline:

```text
Source Code → Tokens → AST → Semantic Analysis → TAC → Assembly → Runtime Output
```

This demonstrates strong compiler engineering fundamentals.

### 3. AI DSL lowering

The AI Workflow DSL is lowered into the internal compiler representation.

This allows the system to preserve the existing compiler architecture while extending it with AI workflow semantics.

### 4. Semantic validation

The compiler validates whether the program is structurally correct.

Examples of validation:

- Dataset must be declared before training
- Model must exist before training
- Model should be trained before evaluation
- Evaluation should happen before deployment
- Prediction should use an existing model

### 5. Runtime execution

For supported workflows, the runtime layer can use:

- pandas for CSV loading
- scikit-learn for model training
- local sample data for demo execution

This makes the project more than a syntax-only compiler.

### 6. LangGraph agentic debugging

The LangGraph layer turns compiler debugging into a multi-step agent workflow.

It observes compiler state, diagnoses the issue, optionally calls an LLM, and synthesizes a final report.

### 7. Optional LLM layer

The project can run with or without LLM APIs.

Supported modes:

```text
deterministic
llm
langgraph
langgraph-llm
auto
```

This design is important because the project remains usable even without external API keys.

### 8. Web IDE

The project includes a browser-based IDE that can display:

- Program output
- Tokens
- AST
- TAC
- Assembly
- Errors
- Lowered core code
- AI Agent Report

### 9. Error report generation

The agent report is generated even when the compiler fails.

This means invalid DSL programs still produce useful debugging output instead of only crashing.


## AI Workflow DSL Grammar

The project includes a compact domain-specific language for describing AI and ML workflows. The grammar is written in an EBNF-style format so recruiters, reviewers, and engineers can quickly understand what the compiler accepts.

```ebnf
program        ::= pipeline_decl statement* endpipeline

pipeline_decl  ::= 'PIPELINE' IDENT
endpipeline    ::= 'ENDPIPELINE'

statement      ::= dataset_decl
                 | model_decl
                 | set_stmt
                 | train_stmt
                 | evaluate_stmt
                 | predict_stmt
                 | deploy_stmt
                 | monitor_stmt
                 | log_stmt

dataset_decl   ::= 'DATASET' IDENT 'FROM' STRING
model_decl     ::= 'MODEL' IDENT 'TASK' STRING
set_stmt       ::= 'SET' IDENT '=' NUMBER
train_stmt     ::= 'TRAIN' IDENT 'ON' IDENT 'EPOCHS' NUMBER
evaluate_stmt  ::= 'EVALUATE' IDENT
predict_stmt   ::= 'PREDICT' IDENT 'INPUT' NUMBER ('INTO' IDENT)?
deploy_stmt    ::= 'DEPLOY' IDENT 'TO' STRING
monitor_stmt   ::= 'MONITOR' IDENT
log_stmt       ::= 'LOG' STRING
```

### Lexical rules

```text
IDENT   = letter_or_underscore followed by letters, digits, or underscores
NUMBER  = integer literal
STRING  = single-quoted string literal
COMMENT = line starting with #
```

Examples:

```text
IDENT   -> churn_model, customers, fraud_detector
NUMBER  -> 10, 25, 128
STRING  -> 'classification', 's3://bucket/data.csv', 'staging'
```

### Statement meaning

| DSL statement | Meaning |
|---|---|
| `PIPELINE name` | Starts a new AI workflow block. |
| `DATASET ds FROM 'path'` | Registers a dataset source such as a local CSV path or cloud URI. |
| `MODEL m TASK 'classification'` | Defines a model and its ML task type. |
| `SET key = value` | Stores a numeric workflow parameter such as batch size or learning rate. |
| `TRAIN m ON ds EPOCHS n` | Trains a declared model on a declared dataset. |
| `EVALUATE m` | Evaluates a trained model. |
| `PREDICT m INPUT n INTO output` | Runs prediction using a numeric input or row index and stores the result. |
| `DEPLOY m TO 'target'` | Marks the model for deployment to an environment. |
| `MONITOR m` | Emits monitoring information for the model. |
| `LOG 'message'` | Writes a workflow log message. |
| `ENDPIPELINE` | Closes the workflow block. |

### Valid workflow order

The compiler and agent both expect the pipeline to follow a safe ML workflow order:

```text
PIPELINE
  DATASET
  MODEL
  SET
  TRAIN
  EVALUATE
  PREDICT
  DEPLOY
  MONITOR
  LOG
ENDPIPELINE
```

Not every statement is mandatory, but critical dependencies must be respected:

```text
DATASET must be declared before TRAIN
MODEL must be declared before TRAIN, EVALUATE, PREDICT, DEPLOY, or MONITOR
TRAIN should happen before EVALUATE or PREDICT
EVALUATE should happen before DEPLOY in production-style workflows
```

### Example accepted program

```text
PIPELINE CustomerChurnOps
DATASET customers FROM 's3://ml-bucket/customer_churn.csv'
MODEL churn_model TASK 'classification'
SET batch_size = 64
SET learning_rate = 1
TRAIN churn_model ON customers EPOCHS 12
EVALUATE churn_model
PREDICT churn_model INPUT 25 INTO churn_score
DEPLOY churn_model TO 'staging'
MONITOR churn_model
LOG 'Pipeline executed successfully'
ENDPIPELINE
```

### Example rejected program

```text
PIPELINE BrokenFraudPipeline
MODEL fraud_model TASK 'classification'
TRAIN fraud_model ON transactions EPOCHS 10
DATASET transactions FROM 's3://fintech-data/transactions.csv'
ENDPIPELINE
```

Why it fails:

```text
The TRAIN statement uses dataset transactions before the DATASET statement declares it.
```

The LangGraph agentic debugger converts this compiler failure into a human-readable diagnosis and a suggested fix.

### Lowering into core compiler representation

The AI DSL is not only interpreted as text. It is lowered into a Pascal-like core compiler representation before passing through the existing compiler stages.

Example DSL:

```text
TRAIN churn_model ON customers EPOCHS 12
```

Lowered compiler-style representation:

```text
trained_churn_model := 1;
accuracy_churn_model := 80;
write('Training model churn_model on dataset customers for 12 epochs');
```

This gives the project two layers:

```text
AI Workflow DSL Grammar
        ↓
AI DSL Lowering Layer
        ↓
Core Compiler Grammar
        ↓
Lexer → Parser → Semantic Analyzer → TAC → Assembly → Runtime Output
```

## Sample DSL programs

### Customer churn pipeline

```text
PIPELINE CustomerChurnOps
DATASET customers FROM 's3://ml-bucket/customer_churn.csv'
MODEL churn_model TASK 'classification'
SET batch_size = 64
SET learning_rate = 1
TRAIN churn_model ON customers EPOCHS 12
EVALUATE churn_model
PREDICT churn_model INPUT 25 INTO churn_score
DEPLOY churn_model TO 'staging'
MONITOR churn_model
LOG 'Pipeline executed successfully'
ENDPIPELINE
```

### Fraud detection pipeline

```text
PIPELINE FraudDetectionOps
DATASET transactions FROM 's3://fintech-data/transactions.csv'
MODEL fraud_model TASK 'classification'
SET batch_size = 128
SET learning_rate = 0.01
SET threshold = 0.85
TRAIN fraud_model ON transactions EPOCHS 20
EVALUATE fraud_model
PREDICT fraud_model INPUT 1001 INTO fraud_risk_score
DEPLOY fraud_model TO 'production'
MONITOR fraud_model
LOG 'Fraud detection pipeline completed successfully'
ENDPIPELINE
```

### Broken pipeline for testing agent debugging

```text
PIPELINE BrokenFraudPipeline
MODEL fraud_model TASK 'classification'
TRAIN fraud_model ON transactions EPOCHS 10
EVALUATE fraud_model
DATASET transactions FROM 's3://fintech-data/transactions.csv'
DEPLOY fraud_model TO 'staging'
MONITOR fraud_model
ENDPIPELINE
```

Expected agent explanation:

```text
The model is being trained on dataset 'transactions' before the dataset is declared.
Move the DATASET declaration before the TRAIN step.
```

## Repository structure

```text
ai-workflow-dsl-compiler/
│
├── README.md
├── requirements.txt
├── requirements-agent.txt
├── server.py
│
├── src/
│   ├── lexer.py
│   ├── parser.py
│   ├── ast_nodes.py
│   ├── symbol_table.py
│   ├── icg.py
│   ├── codegen.py
│   ├── listing.py
│   ├── interpreter.py
│   ├── ai_dsl.py
│   ├── ai_runtime.py
│   ├── agentic_debugger.py
│   ├── llm_layer.py
│   ├── langgraph_layer.py
│   ├── agent_orchestrator.py
│   └── main.py
│
├── examples/
│   ├── healthcare.aidl
│   ├── finance.aidl
│   ├── nlp.aidl
│   └── real_training.aidl
│
├── tests/
│   ├── ai_sample.aidl
│   ├── ai_error.aidl
│   ├── sample.pas
│   ├── error_test.pas
│   └── run_agent_demo.py
│
├── data/
│   └── customers.csv
│
├── web_demo/
│   ├── server.py
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
│
└── output/
```

## How to run locally on Windows

### Step 1: Clone the repository

```bash
git clone https://github.com/vedantjhunjhunwal/agentic-ai-dsl-workflow-compiler
cd gentic-ai-dsl-workflow-compiler
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install core dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Run the normal compiler

```bash
python src/main.py examples/real_training.aidl -o output
```

### Step 5: Run with deterministic AI agent report

```bash
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend deterministic
```

### Step 6: Run with LangGraph

```bash
pip install -r requirements-agent.txt
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend langgraph
```

### Step 7: Run the Web IDE

```bash
python server.py
```

Open:

```text
http://127.0.0.1:5000
```

## How to run locally on macOS / Linux

```bash
git clone https://github.com/YOUR_USERNAME/ai-workflow-dsl-compiler.git
cd ai-workflow-dsl-compiler

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

python3 src/main.py examples/real_training.aidl -o output --agent-report --agent-backend deterministic
```

To run with LangGraph:

```bash
pip install -r requirements-agent.txt
python3 src/main.py examples/real_training.aidl -o output --agent-report --agent-backend langgraph
```

To run the Web IDE:

```bash
python3 server.py
```

Open:

```text
http://127.0.0.1:5000
```

## Running with LangGraph and LLM

The project can optionally call an LLM through LangChain.

### OpenAI example on Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
python src/main.py examples/real_training.aidl -o output --agent-report --agent-backend langgraph-llm --llm-provider openai --llm-model gpt-4o-mini
```

### OpenAI example on macOS / Linux

```bash
export OPENAI_API_KEY="your_api_key_here"
python3 src/main.py examples/real_training.aidl -o output --agent-report --agent-backend langgraph-llm --llm-provider openai --llm-model gpt-4o-mini
```

If the API key is missing, the system falls back to the deterministic agent.

## Running the error-report demo

Use this command to test whether the AI agent reports errors correctly:

```bash
python src/main.py tests/ai_error.aidl -o output --agent-report --agent-backend langgraph
```

Expected behavior:

- Compiler detects the error
- Agent observes the failed state
- Agent explains the issue
- Agent suggests a fix
- CLI or Web IDE shows the AI Agent Report

## Generated outputs

A successful run can produce:

```text
output/<program>.lst
output/<program>.asm
AI Agent Report
Runtime Output
Compiler Diagnostics
```

The most important outputs are:

- Listing file
- Assembly file
- Agent report
- Runtime output
- Error explanation

## Example workflow output

```text
load_source → Source file loaded
lex → Tokens generated
parse → AST generated
semantic_check → Symbols and workflow order validated
generate_tac → Three-Address Code generated
generate_assembly → Pseudo assembly generated
execute_runtime → Supported workflow executed
observe → Agent collected compiler state
deterministic_diagnose → Agent analyzed workflow issues
optional_llm_review → Optional LLM review completed or skipped
synthesize → Final AI Agent Report generated
```

Final status:

```text
completed
```

For a broken workflow:

```text
compile_failed
agent_report_generated
fix_suggestions_available
```

## Why this is more than a basic AI project

A basic AI project usually works like this:

```text
Prompt → LLM → Answer
```

This project works like this:

```text
DSL Program
→ Lexer
→ Parser
→ Semantic Analyzer
→ TAC Generator
→ Runtime Executor
→ LangGraph Agent
→ Optional LLM Review
→ AI Agent Report
```

This makes it a real AI systems project because it includes:

- Deterministic compiler pipeline
- Custom DSL design
- Semantic validation
- Intermediate code generation
- Runtime execution
- Agent orchestration
- Optional LLM reasoning
- Error diagnosis
- Workflow validation
- Human-readable debugging reports

## Design principles

### 1. Deterministic compiler first

The compiler is the source of truth.

The AI agent does not replace lexical analysis, parsing, semantic validation, or code generation.

### 2. Agent as a debugging assistant

The agent explains what happened and suggests how to fix it.

It does not blindly rewrite the program.

### 3. Safe LLM fallback

The project works without API keys.

LLM support is optional.

This makes the system reliable for local demos and recruiter review.

### 4. Error-aware reporting

The agent report is generated even when compilation fails.

This is important because debugging support is most useful when something goes wrong.

### 5. Developer-friendly output

The project produces both compiler artifacts and readable explanations.

This helps bridge low-level compiler internals and practical ML workflow development.

## project summary

This project demonstrates the intersection of compiler engineering, AI agent orchestration, and ML workflow automation.

It shows the ability to design a custom DSL, implement deterministic compiler stages, integrate runtime execution, and add a LangGraph-based agent layer that diagnoses errors and improves developer experience.

The core engineering idea is simple:

```text
Keep the compiler reliable.
Use the agent for reasoning, explanation, validation, and debugging.
```



## License

This project is intended for educational, research, and portfolio purposes.


## Google Cloud Run Deployment

This repository includes deployment files for Google Cloud Run:

- `Dockerfile`
- `.dockerignore`
- `.gcloudignore`
- `cloudbuild.yaml`
- `DEPLOYMENT_GCP.md`

Deploy directly from source:

```bash
gcloud run deploy ai-workflow-compiler-agent \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --concurrency 15 \
  --min-instances 0 \
  --max-instances 30 \
  --timeout 300
```

Or deploy with Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml
```

Recommended settings for a 500-user demo are 1 vCPU, 1 GiB memory, concurrency 15, min instances 0, and max instances 30. See `DEPLOYMENT_GCP.md` for the full guide.
