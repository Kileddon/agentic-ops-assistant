# Local Infrastructure

Start Redis and Prometheus:

```powershell
New-Item -ItemType Directory -Force var
Set-Content -NoNewline var/prometheus-scrape-token "choose-a-local-scrape-token"
docker compose -f docker-compose.infrastructure.yml up -d
```

Start the API with the same token and Redis URL:

```powershell
$env:OPS_REDIS_URL = "redis://127.0.0.1:6379/0"
$env:OPS_PROMETHEUS_SCRAPE_TOKEN = "choose-a-local-scrape-token"
```

Prometheus is available at `http://127.0.0.1:9090`. The API must be reachable from Docker at port 8000 for the configured `host.docker.internal:8000` target.

Archive a verified audit log locally:

```powershell
uv run ops-archive-audit --audit-file var/audit-events.jsonl --archive-directory var/audit-archive
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
