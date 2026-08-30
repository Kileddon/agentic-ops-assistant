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
- Authenticate API callers with local Keycloak OIDC access tokens.
- Record correlation IDs, with optional Redis-backed shared limits and API metrics.
- Detect availability, HTTP 5xx, and latency incidents from Prometheus evidence.
- Expose the workflow through CLI commands and a FastAPI application.

## Safety model

The language model is limited to summarization. It has no tools, production credentials, or action-execution capability.

Action proposals and policy decisions are deterministic Python code. Approval records model a human decision, but there is intentionally no executor that can alter an external system.

The HTTP application writes a hash-chained local audit trail for investigations, approval events, and status-provider failures. It records operational metadata, not raw queries or LLM prompts.

The environment-based HTTP application can use separate API keys for operator, approver,
and auditor roles, or Keycloak OIDC access tokens when Keycloak settings are configured.
Deploy it behind HTTPS and a managed identity boundary outside local use.

## Requirements

- Python 3.13 or 3.14
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) for semantic search and local summaries
- Docker Desktop for the optional Redis, Prometheus, and diagnostics examples

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

The report shows `Recall@1`, `Recall@k`, and the false-positive rate. Evaluation cases can accept one or more relevant article IDs, or an empty list when no article should be returned.

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

`ops-investigate` and `ops-summarize` accept the same `--prometheus-url` option instead of `--status-file` when live status should be used.

## HTTP API

Set the local data sources and start the application:

```powershell
$env:OPS_KNOWLEDGE_FILE = "examples/knowledge.json"
$env:OPS_SERVICE_STATUS_FILE = "examples/service_statuses.json"
$env:OPS_AUDIT_LOG_FILE = "var/audit-events.jsonl"
$env:OPS_OPERATOR_API_KEY = "replace-with-operator-secret"
$env:OPS_APPROVER_API_KEY = "replace-with-approver-secret"
$env:OPS_AUDITOR_API_KEY = "replace-with-auditor-secret"

uv run uvicorn "agentic_ops_assistant.api:create_app_from_environment" --factory --reload
```

JSON is the default status source. To use Prometheus instead, set `OPS_STATUS_SOURCE=prometheus` and `OPS_PROMETHEUS_URL` before starting the application; `OPS_SERVICE_STATUS_FILE` is then not required.

`OPS_AUDIT_LOG_FILE` is optional and defaults to `var/audit-events.jsonl`. The `var/` directory is excluded from Git.

The three current API keys are required and must be distinct. Send them through `X-API-Key`; never commit them or include them in an audit record.

For a no-downtime key replacement, temporarily set the optional matching variable, such as `OPS_OPERATOR_NEXT_API_KEY`. The API accepts both keys for that role. Replace the current variable with the new value, remove the `NEXT` variable, and restart the application. Rotation keys must also be distinct from every other role key.

The API is then available at `http://127.0.0.1:8000`.

Protected endpoints use a fixed-window limit of 60 requests per 60 seconds for each role and endpoint. Adjust it with `OPS_RATE_LIMIT_REQUESTS` and `OPS_RATE_LIMIT_WINDOW_SECONDS`. Set `OPS_REDIS_URL` to share this limit and API metrics across local API processes; without it, both remain process-local.

- `GET /health`
- `POST /investigations`
- `POST /investigation-summaries`
- `POST /incident-detections`
- `POST /approvals/{approval_id}/decisions`
- `GET /audit-events`
- `GET /metrics`
- `GET /metrics/prometheus`

`/health` is public. Investigations and summaries require the operator role, approval decisions require the approver role, and audit events and metrics require the auditor role. `/metrics/prometheus` uses its own bearer scrape credential, set through `OPS_PROMETHEUS_SCRAPE_TOKEN`, rather than a user credential.

Example investigation request:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/investigations" `
  -Headers @{ "X-API-Key" = $env:OPS_OPERATOR_API_KEY } `
  -ContentType "application/json" `
  -Body '{"service":"payments-api","query":"database timeout","limit":3}'
```

Detect Prometheus incidents for a monitored service. `notify` sends a concise
evidence-based Telegram report; retrieved knowledge articles remain possible
causes to investigate rather than confirmed root causes.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/incident-detections" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"service":"agentic-ops-assistant","notify":true}'
```

For a public HTTPS deployment with Caddy while keeping Uvicorn on loopback, see [HTTPS deployment](docs/deployment.md).

For local OIDC authentication with Keycloak, see [Local Keycloak](docs/keycloak.md).

For local Redis, Prometheus, audit archive, and diagnostics setup, see [Local infrastructure](docs/infrastructure.md).

For a production-like local Docker topology with separate API and alert-relay
containers, copy `.env.local.example` to the ignored `.env.local` file and
follow [Local infrastructure](docs/infrastructure.md).

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
