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
