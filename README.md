# Agentic Ops Assistant

Agentic Ops Assistant is a local-first operations triage service. It combines service status, operational knowledge, deterministic policy, and optional local language models to produce a concise investigation report for an operator.

## Capabilities

- Load knowledge articles and service statuses from JSON.
- Search knowledge with deterministic keyword ranking.
- Perform semantic retrieval with local Ollama embeddings.
- Build an investigation report from service status and retrieved evidence.
- Propose actions through deterministic policy rules.
- Require explicit approval for actions that need it.
- Generate validated, structured local-model summaries of investigations.
- Expose the workflow through CLI commands and a FastAPI application.

## Safety model

The language model is limited to summarization. It has no tools, production credentials, or action-execution capability.

Action proposals and policy decisions are deterministic Python code. Approval records model a human decision, but there is intentionally no executor that can alter an external system.

## Requirements

- Python 3.13 or 3.14
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) for semantic search and local summaries

Install dependencies:

```bash
uv sync
```

Pull the local models used by the examples:

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

## CLI

Search the knowledge base:

```bash
uv run ops-search --knowledge-file examples/knowledge.json "database timeout"
```

Search by semantic similarity:

```bash
uv run ops-semantic-search --knowledge-file examples/knowledge.json "connection pool exhausted"
```

Evaluate semantic retrieval against expected articles:

```bash
uv run ops-evaluate-retrieval \
  --knowledge-file examples/knowledge.json \
  --evaluation-file examples/retrieval_evaluation.json
```

Create an investigation with semantic retrieval enabled:

```bash
uv run ops-investigate \
  --knowledge-file examples/knowledge.json \
  --status-file examples/service_statuses.json \
  --semantic-search \
  payments-api "connection pool exhausted"
```

Generate a validated local-model summary:

```bash
uv run ops-summarize \
  --knowledge-file examples/knowledge.json \
  --status-file examples/service_statuses.json \
  --semantic-search \
  payments-api "connection pool exhausted"
```

Read a service availability status from Prometheus:

```bash
uv run ops-prometheus-status \
  --prometheus-url http://localhost:9090 \
  payments-api
```

The command queries `up{job="payments-api"}`. It assumes the Prometheus `job` label matches the service name.

## HTTP API

Set the local data sources and start the application:

```powershell
$env:OPS_KNOWLEDGE_FILE = "examples/knowledge.json"
$env:OPS_SERVICE_STATUS_FILE = "examples/service_statuses.json"

uv run uvicorn "agentic_ops_assistant.api:create_app_from_environment" --factory --reload
```

The API is then available at `http://127.0.0.1:8000`.

- `GET /health`
- `POST /investigations`
- `POST /investigation-summaries`
- `POST /approvals/{approval_id}/decisions`

Example investigation request:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/investigations" `
  -ContentType "application/json" `
  -Body '{"service":"payments-api","query":"database timeout","limit":3}'
```

## Development

```bash
uv run pytest
uv run pre-commit run --all-files
```

The pre-commit hooks apply Ruff formatting and safe lint fixes automatically. If a hook changes staged files, stage them again before repeating the commit.

## Project layout

```text
src/agentic_ops_assistant/  Application package
examples/                   Local sample knowledge and status data
tests/                      Automated tests
docs/                       Public architecture decisions
```
