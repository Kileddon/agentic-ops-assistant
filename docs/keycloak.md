# Local Keycloak

This configuration provides a local OIDC issuer for the API. It is for development only: Keycloak and the API bind to loopback addresses, and no passwords are committed.

Start Keycloak after choosing a local administrator password:

```powershell
$env:KEYCLOAK_ADMIN = "admin"
$env:KEYCLOAK_ADMIN_PASSWORD = "choose-a-local-password"
docker compose -f docker-compose.keycloak.yml up -d
```

The `ops` realm, `ops-api` client, its access-token audience mapper, and the
`operator`, `approver`, and `auditor` realm roles are imported automatically from
`examples/keycloak-realm.json` on the first start. No browser configuration is
needed for those resources.

Open `http://127.0.0.1:8080`, sign in as the administrator, select realm `ops`,
then create a user, set a non-temporary password, and assign exactly one realm
role: `operator`, `approver`, or `auditor`. A user and password remain local
identity data and are intentionally not part of the imported realm file.

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

## Containerized API

When the API runs through `docker-compose.application.yml`, it cannot use the
host's loopback address to fetch Keycloak signing keys. The example environment
therefore keeps the public token issuer as `http://127.0.0.1:8080/realms/ops`
and sets `OPS_KEYCLOAK_JWKS_URL` to the container-reachable
`host.docker.internal` certificate endpoint. This separates strict JWT issuer
validation from the internal network route used for JWKS retrieval.

```powershell
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8080/realms/ops/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body @{ client_id = "ops-api"; grant_type = "password"; username = $env:OPS_KEYCLOAK_TEST_USERNAME; password = $env:OPS_KEYCLOAK_TEST_PASSWORD }).access_token
```
