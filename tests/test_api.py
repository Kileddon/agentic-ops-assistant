from pathlib import Path

from fastapi.testclient import TestClient

from agentic_ops_assistant.api import create_app, create_app_from_environment
from agentic_ops_assistant.audit.store import InMemoryAuditStore
from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.operations.prometheus import PrometheusStatusError
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus
from agentic_ops_assistant.summarization.models import GeneratedSummary


class FakeSummaryClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def summarize(self, prompt: str) -> GeneratedSummary:
        self.prompts.append(prompt)
        return GeneratedSummary(
            summary="The payments API is degraded because of database timeouts.",
            possible_cause=None,
            uncertainty="The report does not confirm a root cause.",
        )


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if "connection pool" in text:
            return (1.0, 0.0)

        return (0.0, 1.0)


class FakeStatusProvider:
    def __init__(self, status: ServiceStatus | None) -> None:
        self._status = status

    def get_status(self, service: str) -> ServiceStatus | None:
        return self._status


class FailingStatusProvider:
    def get_status(self, service: str) -> ServiceStatus | None:
        raise PrometheusStatusError("Prometheus availability query failed.")


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
        "semantic_matches": [],
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


def test_create_investigation_returns_semantic_matches_when_requested() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )
    client = TestClient(
        create_app(
            articles=[article],
            semantic_embedder=FakeEmbedder(),
        ),
    )

    response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "connection pool exhausted",
            "semantic_search": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["semantic_matches"] == [
        {
            "id": "database-timeout",
            "title": "Database timeout",
            "content": "Check the connection pool.",
            "tags": ["database", "timeout"],
            "similarity": 1.0,
        },
    ]


def test_create_investigation_requires_configured_embedder() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "connection pool exhausted",
            "semantic_search": True,
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Local semantic search is not configured.",
    }


def test_create_investigation_uses_injected_status_provider() -> None:
    status = ServiceStatus(
        service="payments-api",
        health=ServiceHealth.OUTAGE,
        summary="Prometheus reports all 1 targets down.",
    )
    client = TestClient(
        create_app(
            status_provider=FakeStatusProvider(status),
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
    assert response.json()["service_status"]["health"] == "outage"
    assert response.json()["proposed_action"]["action_type"] == "restart_service"


def test_create_investigation_returns_503_when_status_provider_fails() -> None:
    client = TestClient(create_app(status_provider=FailingStatusProvider()))

    response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "database timeout",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Prometheus availability query failed.",
    }


def test_api_records_and_lists_investigation_and_approval_events() -> None:
    status = ServiceStatus(
        service="payments-api",
        health=ServiceHealth.OUTAGE,
        summary="Service is not responding.",
    )
    audit_store = InMemoryAuditStore()
    client = TestClient(create_app(statuses=[status], audit_store=audit_store))

    investigation_response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "database timeout",
        },
    )
    approval_id = investigation_response.json()["approval_request"]["id"]
    decision_response = client.post(
        f"/approvals/{approval_id}/decisions",
        json={"approved": True},
    )
    events_response = client.get("/audit-events")

    assert investigation_response.status_code == 200
    assert decision_response.status_code == 200
    assert events_response.status_code == 200
    assert [event["event_type"] for event in events_response.json()] == [
        "approval_decided",
        "investigation_created",
        "approval_created",
    ]
    assert events_response.json()[1]["details"] == {
        "keyword_match_count": "0",
        "semantic_match_count": "0",
        "policy_status": "requires_approval",
    }


def test_api_records_status_provider_failure() -> None:
    audit_store = InMemoryAuditStore()
    client = TestClient(
        create_app(
            status_provider=FailingStatusProvider(),
            audit_store=audit_store,
        ),
    )

    investigation_response = client.post(
        "/investigations",
        json={
            "service": "payments-api",
            "query": "database timeout",
        },
    )
    events_response = client.get("/audit-events")

    assert investigation_response.status_code == 503
    assert events_response.json()[0]["event_type"] == "status_provider_failed"
    assert events_response.json()[0]["details"] == {"provider": "prometheus"}


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
                "OPS_AUDIT_LOG_FILE": str(tmp_path / "audit-events.jsonl"),
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


def test_create_investigation_summary_returns_local_model_response() -> None:
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
    summary_client = FakeSummaryClient()
    client = TestClient(
        create_app(
            articles=[article],
            statuses=[status],
            summary_client=summary_client,
            semantic_embedder=FakeEmbedder(),
        ),
    )

    response = client.post(
        "/investigation-summaries",
        json={
            "service": "payments-api",
            "query": "connection pool exhausted",
            "semantic_search": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "service": "payments-api",
        "summary": (
            "Summary: The payments API is degraded because of database timeouts.\n"
            "Possible cause: Not established.\n"
            "Uncertainty: The report does not confirm a root cause."
        ),
    }
    assert len(summary_client.prompts) == 1
    assert "Database timeout" in summary_client.prompts[0]
    assert "Semantic knowledge matches:" in summary_client.prompts[0]
