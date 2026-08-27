from collections.abc import Sequence
from dataclasses import dataclass

from agentic_ops_assistant.actions.models import PolicyDecision, ProposedAction
from agentic_ops_assistant.actions.policy import evaluate_action
from agentic_ops_assistant.actions.proposer import propose_action
from agentic_ops_assistant.diagnostics.docker import ContainerDiagnostics
from agentic_ops_assistant.embeddings.client import TextEmbedder
from agentic_ops_assistant.knowledge.models import (
    KnowledgeArticle,
    KnowledgeMatch,
    SemanticKnowledgeMatch,
)
from agentic_ops_assistant.knowledge.search import search_knowledge
from agentic_ops_assistant.knowledge.semantic_search import search_semantically
from agentic_ops_assistant.operations.provider import ServiceStatusProvider
from agentic_ops_assistant.operations.status import ServiceStatus, get_service_status


@dataclass(frozen=True, slots=True)
class InvestigationReport:
    service: str
    service_status: ServiceStatus | None
    knowledge_matches: tuple[KnowledgeMatch, ...]
    proposed_action: ProposedAction | None
    policy_decision: PolicyDecision | None
    semantic_matches: tuple[SemanticKnowledgeMatch, ...] = ()
    diagnostics: ContainerDiagnostics | None = None


def investigate(
    query: str,
    service: str,
    articles: Sequence[KnowledgeArticle],
    statuses: Sequence[ServiceStatus] = (),
    limit: int = 5,
    semantic_embedder: TextEmbedder | None = None,
    minimum_similarity: float = 0.58,
    status_provider: ServiceStatusProvider | None = None,
) -> InvestigationReport:
    service_status = (
        get_service_status(service, statuses)
        if status_provider is None
        else status_provider.get_status(service)
    )
    knowledge_matches = tuple(search_knowledge(query, articles, limit=limit))
    semantic_matches: tuple[SemanticKnowledgeMatch, ...] = ()

    if semantic_embedder is not None:
        semantic_matches = tuple(
            search_semantically(
                query,
                articles,
                semantic_embedder,
                limit=limit,
                minimum_similarity=minimum_similarity,
            ),
        )

    proposed_action = propose_action(service_status)
    policy_decision = evaluate_action(proposed_action) if proposed_action is not None else None

    return InvestigationReport(
        service=service,
        service_status=service_status,
        knowledge_matches=knowledge_matches,
        proposed_action=proposed_action,
        policy_decision=policy_decision,
        semantic_matches=semantic_matches,
    )
