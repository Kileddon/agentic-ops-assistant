from agentic_ops_assistant.actions.models import (
    ActionType,
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)
from agentic_ops_assistant.investigation import investigate
from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


def test_investigate_proposes_allowed_diagnostics_for_degraded_service() -> None:
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

    assert report.service_status == status
    assert report.proposed_action == ProposedAction(
        service="payments-api",
        action_type=ActionType.COLLECT_DIAGNOSTICS,
        rationale="Service status is degraded: Elevated database timeout rate.",
    )
    assert report.policy_decision == PolicyDecision(
        status=PolicyStatus.ALLOWED,
        reason="Read-only diagnostic collection is allowed.",
    )


def test_investigate_returns_no_action_for_unknown_service() -> None:
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
    assert report.proposed_action is None
    assert report.policy_decision is None


def test_investigate_requires_approval_for_outage_restart() -> None:
    status = ServiceStatus(
        service="payments-api",
        health=ServiceHealth.OUTAGE,
        summary="Service is not responding.",
    )

    report = investigate(
        query="database",
        service="payments-api",
        articles=[],
        statuses=[status],
    )

    assert report.proposed_action == ProposedAction(
        service="payments-api",
        action_type=ActionType.RESTART_SERVICE,
        rationale="Service outage reported: Service is not responding.",
    )
    assert report.policy_decision == PolicyDecision(
        status=PolicyStatus.REQUIRES_APPROVAL,
        reason="Service restart requires human approval.",
    )


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if text == "backend connections exhausted":
            return (1.0, 0.0)

        if "Database timeout" in text:
            return (1.0, 0.0)

        raise AssertionError(f"Unexpected text: {text}")


def test_investigate_includes_semantic_matches_when_embedder_is_provided() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )

    report = investigate(
        query="backend connections exhausted",
        service="payments-api",
        articles=[article],
        statuses=[],
        semantic_embedder=FakeEmbedder(),
    )

    assert [match.article.id for match in report.semantic_matches] == [
        "database-timeout",
    ]
    assert report.semantic_matches[0].similarity == 1.0
