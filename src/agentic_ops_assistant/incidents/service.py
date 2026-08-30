from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from agentic_ops_assistant.embeddings.client import TextEmbedder
from agentic_ops_assistant.incidents.models import IncidentSignal
from agentic_ops_assistant.investigation import InvestigationReport, investigate
from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.operations.provider import ServiceStatusProvider


@dataclass(frozen=True, slots=True)
class DetectedIncident:
    signal: IncidentSignal
    investigation: InvestigationReport


class IncidentDetector(Protocol):
    def detect(self, service: str) -> tuple[IncidentSignal, ...]: ...


class IncidentInvestigationService:
    """Turns deterministic monitoring signals into read-only investigations."""

    def __init__(
        self,
        *,
        detector: IncidentDetector,
        articles: Sequence[KnowledgeArticle],
        status_provider: ServiceStatusProvider,
        semantic_embedder: TextEmbedder | None = None,
    ) -> None:
        self._detector = detector
        self._articles = articles
        self._status_provider = status_provider
        self._semantic_embedder = semantic_embedder

    def investigate(
        self, service: str, *, semantic_search: bool = False
    ) -> tuple[DetectedIncident, ...]:
        embedder = self._semantic_embedder if semantic_search else None

        return tuple(
            DetectedIncident(
                signal=signal,
                investigation=investigate(
                    query=signal.investigation_query,
                    service=signal.service,
                    articles=self._articles,
                    semantic_embedder=embedder,
                    status_provider=self._status_provider,
                ),
            )
            for signal in self._detector.detect(service)
        )
