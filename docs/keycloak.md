# Local Keycloak

This configuration provides a local OIDC issuer for the API. It is for development only: Keycloak and the API bind to loopback addresses, and no passwords are committed.

Start Keycloak after choosing a local administrator password:

```powershell
$env:KEYCLOAK_ADMIN = "admin"
$env:KEYCLOAK_ADMIN_PASSWORD = "choose-a-local-password"
docker compose -f docker-compose.keycloak.yml up -d
```

Open `http://127.0.0.1:8080`, sign in as the administrator, then open realm `ops`. Create a user, set a non-temporary password, and assign exactly one realm role: `operator`, `approver`, or `auditor`.

Start the API with Keycloak authentication enabled:

```powershell
$env:OPS_KEYCLOAK_ISSUER = "http://127.0.0.1:8080/realms/ops"
$env:OPS_KEYCLOAK_AUDIENCE = "ops-api"
uv run uvicorn "agentic_ops_assistant.api:create_app_from_environment" --factory --host 127.0.0.1 --port 8000
```

Request an access token for the local user and use it as a bearer credential:

```powershell
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8080/realms/ops/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "client_id=ops-api&grant_type=password&username=YOUR_USER&password=YOUR_PASSWORD").access_token

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/investigations" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"service":"payments-api","query":"database timeout"}'
```

When Keycloak settings are present, static API keys are ignored. In a public deployment, place Keycloak and the API behind HTTPS and do not use the password grant shown here; it is only a convenient local verification path.
