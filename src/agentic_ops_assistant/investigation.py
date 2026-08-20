from collections.abc import Sequence
from dataclasses import dataclass

from agentic_ops_assistant.actions.models import PolicyDecision, ProposedAction
from agentic_ops_assistant.actions.policy import evaluate_action
from agentic_ops_assistant.actions.proposer import propose_action
from agentic_ops_assistant.knowledge.models import KnowledgeArticle, KnowledgeMatch
from agentic_ops_assistant.knowledge.search import search_knowledge
from agentic_ops_assistant.operations.status import ServiceStatus, get_service_status


@dataclass(frozen=True, slots=True)
class InvestigationReport:
    service: str
    service_status: ServiceStatus | None
    knowledge_matches: tuple[KnowledgeMatch, ...]
    proposed_action: ProposedAction | None
    policy_decision: PolicyDecision | None


def investigate(
    query: str,
    service: str,
    articles: Sequence[KnowledgeArticle],
    statuses: Sequence[ServiceStatus],
    limit: int = 5,
) -> InvestigationReport:
    service_status = get_service_status(service, statuses)
    knowledge_matches = tuple(search_knowledge(query, articles, limit=limit))
    proposed_action = propose_action(service_status)
    policy_decision = evaluate_action(proposed_action) if proposed_action is not None else None

    return InvestigationReport(
        service=service,
        service_status=service_status,
        knowledge_matches=knowledge_matches,
        proposed_action=proposed_action,
        policy_decision=policy_decision,
    )
