# Google Cloud Run Deployment Guide

This project is ready to deploy as a containerized AI Workflow DSL Compiler with LangGraph-based agentic debugging.

## Architecture

```text
Browser Users
   ↓
Google Cloud Run
   ├── Web IDE
   ├── Compiler pipeline
   │   ├── Lexer
   │   ├── Parser
   │   ├── Semantic analyzer
   │   ├── TAC generator
   │   └── Runtime executor
   └── LangGraph agent layer
       ├── observe
       ├── deterministic_diagnose
       ├── optional_llm_review
       └── synthesize
```

## Files added for deployment

- `Dockerfile` — production container definition for Cloud Run
- `.dockerignore` — keeps Docker builds small
- `.gcloudignore` — keeps Cloud Build uploads small
- `cloudbuild.yaml` — one-command Cloud Build + Cloud Run deployment
- `DEPLOYMENT_GCP.md` — this guide

## Local test

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-agent.txt
$env:PORT="8501"
python server.py
```

Open:

```text
http://127.0.0.1:8501
```

## Deploy directly from source

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

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

## Deploy using Cloud Build

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Recommended Cloud Run settings for a 500-user demo

```text
Region: asia-south1
CPU: 1 vCPU
Memory: 1 GiB
Concurrency: 15
Min instances: 0
Max instances: 30
Timeout: 300 seconds
```

This supports horizontal autoscaling. For heavy compile workloads, reduce concurrency to 10 and increase max instances.

## Optional LLM key

Do not commit API keys to GitHub. Use Cloud Run environment variables or Secret Manager.

Simple demo environment variable:

```bash
gcloud run services update ai-workflow-compiler-agent \
  --region asia-south1 \
  --set-env-vars OPENAI_API_KEY=your_key_here
```

Then select `LangGraph + LLM` in the Web IDE.

## Logs

```bash
gcloud run services logs read ai-workflow-compiler-agent --region asia-south1
```

## Health checks

The app exposes:

```text
/healthz
/_ah/health
```
