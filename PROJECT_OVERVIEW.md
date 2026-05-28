# Project Overview

## Title
AI Workflow DSL Compiler with Web IDE

## What this project does
This project builds a small domain-specific language for AI/ML workflows and compiles it through a full compiler chain.

## Features
- AI-specific DSL syntax
- lexical analysis
- parser and AST generation
- semantic validation
- three-address code generation
- simple assembly-like code generation
- runtime execution with program output
- line-wise compile and runtime error reporting
- web frontend for interaction and demonstration

## How to run
```bash
python server.py
```

Then open the localhost URL shown in the terminal.

## Web IDE views
- Program Output
- Errors
- Listing
- Tokens
- AST
- TAC
- Assembly
- Lowered Core Code

## Sample AI DSL
```text
PIPELINE FraudCheck
DATASET transactions FROM 'bank_data.csv'
MODEL fraud_net TASK 'classification'
TRAIN fraud_net ON transactions EPOCHS 8
PREDICT fraud_net INPUT 999 INTO fraud_score
LOG 'Fraud detection completed'
ENDPIPELINE
```


This upgraded version performs **real CSV ingestion and real model training** for AI DSL programs using pandas and scikit-learn while preserving the compiler pipeline for lexing, parsing, semantic checking, TAC, and pseudo-assembly generation.
