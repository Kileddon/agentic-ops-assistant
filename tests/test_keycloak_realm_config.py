import json
from pathlib import Path


def test_imported_keycloak_realm_defines_api_client_and_roles() -> None:
    realm_file = Path("examples/keycloak-realm.json")

    realm = json.loads(realm_file.read_text(encoding="utf-8"))

    assert realm["realm"] == "ops"
    assert {role["name"] for role in realm["roles"]["realm"]} == {
        "operator",
        "approver",
        "auditor",
    }

    api_client = next(client for client in realm["clients"] if client["clientId"] == "ops-api")

    assert api_client["publicClient"] is True
    assert api_client["directAccessGrantsEnabled"] is True
    assert api_client["protocolMappers"][0]["config"]["included.client.audience"] == "ops-api"
