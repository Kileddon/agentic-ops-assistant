from pathlib import Path

from fastapi.testclient import TestClient

from agentic_ops_assistant.api import create_app, create_app_from_environment
from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


def test_health_check_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_investigation_returns_structured_report() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )
    status = ServiceStatus(
        service="payments-api",
        health=ServiceHealth.DEGRADED,
        summary="Elevated database timeout rate.",
    )
    client = TestClient(create_app(articles=[article], statuses=[status]))

    response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "database timeout",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "service": "payments-api",
        "service_status": {
            "service": "payments-api",
            "health": "degraded",
            "summary": "Elevated database timeout rate.",
        },
        "knowledge_matches": [
            {
                "id": "database-timeout",
                "title": "Database timeout",
                "content": "Check the connection pool.",
                "tags": ["database", "timeout"],
                "score": 6,
            },
        ],
        "proposed_action": {
            "service": "payments-api",
            "action_type": "collect_diagnostics",
            "rationale": "Service status is degraded: Elevated database timeout rate.",
        },
        "policy_decision": {
            "status": "allowed",
            "reason": "Read-only diagnostic collection is allowed.",
        },
        "approval_request": None,
    }


def test_create_investigation_rejects_blank_query() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "   ",
        },
    )

    assert response.status_code == 422


def test_create_app_from_environment_loads_application_data(
    tmp_path: Path,
) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.write_text(
        """
        [
          {
            "id": "database-timeout",
            "title": "Database timeout",
            "content": "Check the connection pool.",
            "tags": ["database", "timeout"]
          }
        ]
        """,
        encoding="utf-8",
    )
    status_file = tmp_path / "service_statuses.json"
    status_file.write_text(
        """
        [
          {
            "service": "payments-api",
            "status": "degraded",
            "summary": "Elevated database timeout rate."
          }
        ]
        """,
        encoding="utf-8",
    )

    client = TestClient(
        create_app_from_environment(
            {
                "OPS_KNOWLEDGE_FILE": str(knowledge_file),
                "OPS_SERVICE_STATUS_FILE": str(status_file),
            },
        ),
    )

    response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "database timeout",
        },
    )

    assert response.status_code == 200
    assert response.json()["service_status"]["health"] == "degraded"
    assert response.json()["knowledge_matches"][0]["id"] == "database-timeout"


def test_outage_creates_pending_approval_and_accepts_decision() -> None:
    status = ServiceStatus(
        service="payments-api",
        health=ServiceHealth.OUTAGE,
        summary="Service is not responding.",
    )
    client = TestClient(create_app(statuses=[status]))

    investigation_response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "database timeout",
        },
    )

    assert investigation_response.status_code == 200

    report = investigation_response.json()
    approval_request = report["approval_request"]

    assert report["policy_decision"]["status"] == "requires_approval"
    assert approval_request["status"] == "pending"
    assert approval_request["action"]["action_type"] == "restart_service"

    decision_response = client.post(
        f"/approvals/{approval_request['id']}/decisions",
        json={"approved": True},
    )

    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"
