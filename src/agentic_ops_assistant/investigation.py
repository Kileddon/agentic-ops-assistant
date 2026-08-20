from collections.abc import Sequence
from dataclasses import dataclass

from agentic_ops_assistant.knowledge.models import KnowledgeArticle, KnowledgeMatch
from agentic_ops_assistant.knowledge.search import search_knowledge
from agentic_ops_assistant.operations.status import ServiceStatus, get_service_status


@dataclass(frozen=True, slots=True)
class InvestigationReport:
    service: str
    service_status: ServiceStatus | None
    knowledge_matches: tuple[KnowledgeMatch, ...]


def investigate(
    query: str,
    service: str,
    articles: Sequence[KnowledgeArticle],
    statuses: Sequence[ServiceStatus],
    limit: int = 5,
) -> InvestigationReport:
    service_status = get_service_status(service, statuses)
    knowledge_matches = tuple(search_knowledge(query, articles, limit=limit))

    return InvestigationReport(
        service=service,
        service_status=service_status,
        knowledge_matches=knowledge_matches,
    )
