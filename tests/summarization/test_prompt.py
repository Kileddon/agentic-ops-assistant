from agentic_ops_assistant.actions.models import (
    ActionType,
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)
from agentic_ops_assistant.investigation import InvestigationReport
from agentic_ops_assistant.knowledge.models import (
    KnowledgeArticle,
    KnowledgeMatch,
    SemanticKnowledgeMatch,
)
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus
from agentic_ops_assistant.summarization.prompt import build_summary_prompt


def test_build_summary_prompt_includes_investigation_data() -> None:
    report = InvestigationReport(
        service="payments-api",
        service_status=ServiceStatus(
            service="payments-api",
            health=ServiceHealth.DEGRADED,
            summary="Elevated database timeout rate.",
        ),
        knowledge_matches=(
            KnowledgeMatch(
                article=KnowledgeArticle(
                    id="database-timeout",
                    title="Database timeout",
                    content="Check the connection pool.",
                    tags=("database", "timeout"),
                ),
                score=6,
            ),
        ),
        proposed_action=ProposedAction(
            service="payments-api",
            action_type=ActionType.COLLECT_DIAGNOSTICS,
            rationale="The service is degraded.",
        ),
        policy_decision=PolicyDecision(
            status=PolicyStatus.ALLOWED,
            reason="Collecting diagnostics is read-only.",
        ),
        semantic_matches=(
            SemanticKnowledgeMatch(
                article=KnowledgeArticle(
                    id="connection-pool",
                    title="Connection pool exhaustion",
                    content="Inspect active database connections.",
                ),
                similarity=0.722,
            ),
        ),
    )

    prompt = build_summary_prompt(report)

    assert "payments-api" in prompt
    assert "degraded" in prompt
    assert "Database timeout" in prompt
    assert "collect_diagnostics" in prompt
    assert "Do not propose new actions." in prompt
    assert "Semantic knowledge matches:" in prompt
    assert "Connection pool exhaustion" in prompt
    assert "Similarity: 0.722" in prompt
