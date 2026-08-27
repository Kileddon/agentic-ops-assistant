# HTTPS Deployment

This guide exposes the HTTP API through Caddy while keeping Uvicorn reachable only from the local machine. It is a small deployment baseline, not a substitute for centralized identity, monitoring, backups, or a distributed rate limiter.

## Prerequisites

- A public DNS name that resolves to the host running Caddy.
- External access to TCP ports 80 and 443.
- Caddy installed as the public-facing process.
- API-key environment variables available to the Uvicorn process, never in the Caddyfile or repository.

## Run the application on loopback

Start Uvicorn so that it accepts connections only from the local machine:

```powershell
uv run uvicorn "agentic_ops_assistant.api:create_app_from_environment" --factory --host 127.0.0.1 --port 8000
```

Do not expose port 8000 through the host firewall or a cloud security group.

## Configure Caddy

Create a Caddyfile outside this repository and replace the hostname:

```caddyfile
ops.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Validate and load the Caddy configuration using the process-management method for the host. Caddy obtains and renews certificates for a public hostname and redirects HTTP to HTTPS when its DNS record points to the host and ports 80 and 443 reach Caddy.

`X-API-Key` is forwarded to the application by default, so clients continue to send it over the HTTPS connection to `https://ops.example.com`.

## Verification

Check the public health endpoint:

```powershell
Invoke-RestMethod -Uri "https://ops.example.com/health"
```

Then call a protected endpoint with an API key. A missing key must return `401`; an incorrect role must return `403`; requests above the configured limit must return `429` with `Retry-After`.

## Boundaries

- The application's in-memory rate limiter applies per application process, role, and endpoint. Run a shared limiter at the proxy or platform layer before scaling to multiple application instances.
- Do not configure client-IP trust or use forwarded client-IP headers until the proxy chain and trusted proxy addresses are explicitly defined.
- Use a managed secret store and centralized identity before a broader deployment. Static environment keys are appropriate only for this local deployment boundary.
