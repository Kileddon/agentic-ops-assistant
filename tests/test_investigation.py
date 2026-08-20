from agentic_ops_assistant.investigation import investigate
from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


def test_investigate_combines_service_status_and_knowledge_matches() -> None:
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

    report = investigate(
        query="database timeout",
        service="payments-api",
        articles=[article],
        statuses=[status],
    )

    assert report.service == "payments-api"
    assert report.service_status == status
    assert [match.article.id for match in report.knowledge_matches] == [
        "database-timeout",
    ]


def test_investigate_returns_none_for_unknown_service() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
    )

    report = investigate(
        query="database",
        service="unknown-api",
        articles=[article],
        statuses=[],
    )

    assert report.service_status is None
    assert [match.article.id for match in report.knowledge_matches] == [
        "database-timeout",
    ]
