# Local Infrastructure

Start Redis, Prometheus, and Alertmanager:

```powershell
New-Item -ItemType Directory -Force var
Set-Content -LiteralPath var/prometheus-scrape-token -NoNewline -Value "choose-a-local-scrape-token"
Set-Content -LiteralPath var/alert-webhook-token -NoNewline -Value "choose-a-local-alert-token"
docker compose -f docker-compose.infrastructure.yml up -d
```

Start the API with the same token and Redis URL:

```powershell
$env:OPS_REDIS_URL = "redis://127.0.0.1:6379/0"
$env:OPS_PROMETHEUS_SCRAPE_TOKEN = "choose-a-local-scrape-token"
$env:OPS_ALERT_WEBHOOK_TOKEN = "choose-a-local-alert-token"
```

Prometheus is available at `http://127.0.0.1:9090`, and Alertmanager at `http://127.0.0.1:9093`. The API must be reachable from Docker at port 8000 for the configured `host.docker.internal:8000` target.

Run the independent relay in a separate terminal. It needs only the alert webhook token and Telegram configuration; it has no access to the API, actions, approvals, or knowledge data:

```powershell
$env:OPS_ALERT_WEBHOOK_TOKEN = "choose-a-local-alert-token"
$env:OPS_TELEGRAM_BOT_TOKEN = Read-Host "Telegram bot token"
$env:OPS_TELEGRAM_CHAT_ID = "your-numeric-chat-id"
uv run uvicorn "agentic_ops_assistant.alert_relay:create_alert_relay_from_environment" --factory --host 0.0.0.0 --port 8001
```

`TargetDown` alerts when the main API cannot be scraped for 30 seconds, and `ApiServerErrors` alerts after HTTP 5xx responses. Since the relay runs independently on port 8001, it can notify Telegram even when the API on port 8000 is unavailable.

The relay sends the first `firing` and matching `resolved` notification for an alert fingerprint. Repeated `firing` payloads are suppressed while that alert remains active.

Archive a verified audit log locally:

```powershell
uv run ops-archive-audit --audit-file var/audit-events.jsonl --archive-directory var/audit-archive
```

Audit retention policy: keep the active audit log for 30 days, retain verified archives for 365 days, and copy every archive to a backup directory on a different volume or managed backup location. The local `var/audit-archive` directory is staging, not a durable backup.

```powershell
uv run ops-prune-audit --audit-file var/audit-events.jsonl --before "2026-07-28T00:00:00+00:00" --confirm-prune
uv run ops-backup-audit --archive-file var/audit-archive/audit-YYYYMMDDTHHMMSSZ.jsonl --backup-directory E:\ops-audit-backup
uv run ops-restore-audit --archive-file E:\ops-audit-backup/audit-YYYYMMDDTHHMMSSZ.jsonl --restore-file var/restore/audit-events.jsonl --confirm-restore
```

Backup and restore both verify the hash-chain before copying. Restore refuses to overwrite an existing file.

Set the backup location once for repeated backups; it should resolve outside the project disk:

```powershell
$env:OPS_AUDIT_BACKUP_DIRECTORY = "E:\ops-audit-backup"
uv run ops-backup-latest-audit
```

Read-only diagnostics remain limited to `demo-api` and the latest 100 log lines:

```powershell
uv run ops-collect-diagnostics demo-api
```

The command prints the status, resource snapshot, and recent logs locally. If both
`OPS_TELEGRAM_BOT_TOKEN` and `OPS_TELEGRAM_CHAT_ID` are set, only its safe summary
is sent to Telegram; log contents are never sent there.

For a safe local check, start the included container that writes harmless heartbeat
messages:

```powershell
docker compose -f docker-compose.diagnostics.yml up -d
uv run ops-collect-diagnostics demo-api
```

The collector has a strict allowlist for this container and invokes only `docker
inspect`, `docker stats --no-stream`, and `docker logs --tail 100`. It never starts,
stops, restarts, removes, or executes commands in a container.

Search the collected log snapshot by terms. The collector redacts common password,
token, secret, API-key, and bearer-credential formats before printing results:

```powershell
uv run ops-collect-diagnostics demo-api --search "database timeout"
```

To include diagnostics in an HTTP investigation, explicitly configure the allowed container on the API process and set `include_diagnostics: true` in the investigation JSON. This records only diagnostic metadata in audit events.

```powershell
$env:OPS_DIAGNOSTIC_CONTAINER = "demo-api"
```

Knowledge articles support `source`, `owner`, `last_reviewed`, and `severity` metadata. Check owners and review age with:

```powershell
uv run ops-check-knowledge-governance --knowledge-file examples/knowledge.json
```

For a production-like local application topology, create a local `.env.local` containing the required runtime variables and start the API and relay as separate containers:

```powershell
docker compose -f docker-compose.application.yml up -d --build
```

`scripts/run-audit-backup.ps1` is the command boundary intended for a Windows Task Scheduler job. It requires `OPS_AUDIT_BACKUP_DIRECTORY` and runs the verified latest-archive backup command.
