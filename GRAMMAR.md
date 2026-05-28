# AI Workflow DSL Grammar

This project implements an **AI Workflow DSL** that is compiled into a Pascal-like core language and then passed through the full compiler pipeline.

## Purpose
The DSL is designed for describing common AI/ML pipeline actions in a compact domain-specific form:
- dataset registration
- model registration
- parameter setting
- training
- evaluation
- prediction
- deployment
- monitoring
- logging

## High-level pipeline

```text
AI Workflow DSL -> Lowering/Transpilation -> Core Compiler -> AST -> TAC -> Assembly -> Runtime Output
```

## EBNF Grammar

```ebnf
program        ::= pipeline_decl statement* endpipeline
pipeline_decl  ::= 'PIPELINE' IDENT
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
endpipeline    ::= 'ENDPIPELINE'
```

## Lexical conventions
- `IDENT` is an identifier made of letters, digits, and underscores, starting with a letter or underscore.
- `NUMBER` is an integer literal.
- `STRING` is a single-quoted string literal, for example `'classification'`.
- Keywords are case-insensitive in the parser implementation.
- One statement is expected per line in the surface DSL.

## Semantics of each command
- `PIPELINE name` starts a new AI workflow.
- `DATASET ds FROM 'path'` registers a dataset source.
- `MODEL m TASK 'task_name'` registers a model and task type.
- `SET x = 10` stores an integer pipeline parameter.
- `TRAIN m ON ds EPOCHS 12` trains a model on a known dataset.
- `EVALUATE m` evaluates a model.
- `PREDICT m INPUT 25 INTO out` generates a prediction and stores it.
- `DEPLOY m TO 'target'` marks the model as deployed.
- `MONITOR m` prints deployment and accuracy information.
- `LOG 'message'` prints a message.
- `ENDPIPELINE` closes the pipeline.

## Valid example

```text
PIPELINE CustomerChurn
DATASET customers FROM 'customers.csv'
MODEL churn_model TASK 'classification'
SET batch_size = 32
TRAIN churn_model ON customers EPOCHS 10
EVALUATE churn_model
PREDICT churn_model INPUT 25 INTO score
DEPLOY churn_model TO 'staging'
MONITOR churn_model
LOG 'Customer churn pipeline completed'
ENDPIPELINE
```

## Lowered core-language sketch
This DSL is translated into a Pascal-like core program such as:

```text
program CustomerChurn;

var
    accuracy_churnmodel, batchsize, dataset_customers, deployed_churnmodel,
    model_churnmodel, prediction_churnmodel, trained_churnmodel : integer;

begin
    write('Starting AI pipeline: CustomerChurn');
    dataset_customers := 1;
    write('Loaded dataset customers from customers.csv');
    model_churnmodel := 1;
    write('Registered model churn_model for task classification');
    batchsize := 32;
    write('Set batch_size = ', batchsize);
    trained_churnmodel := 1;
    accuracy_churnmodel := 80;
    write('Training model churn_model on dataset customers for 10 epochs');
    write('Evaluation accuracy for churn_model = ', accuracy_churnmodel);
    score := 25 + accuracy_churnmodel;
    write('Prediction from churn_model = ', score);
    deployed_churnmodel := 1;
    write('Deployed model churn_model to staging');
    write('Monitoring churn_model: accuracy=', accuracy_churnmodel, ', deployed=', deployed_churnmodel);
    write('Customer churn pipeline completed');
    write('Pipeline completed: CustomerChurn');
end.
```

## Notes for presentation
You can describe the project as:

> An AI Workflow DSL compiler that translates high-level ML pipeline commands into a core procedural language and then performs lexical analysis, parsing, semantic analysis, intermediate code generation, code generation, and runtime execution.


## Runtime Notes

- `DATASET name FROM 'path.csv'` loads a real CSV file at runtime.
- For classification/regression tasks, the runtime infers the target column using `target`, `label`, `class`, `y`, or the last column.
- `PREDICT model INPUT n INTO out` interprets `n` as a dataset row index from the model's training dataset.
