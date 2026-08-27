from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True, slots=True)
class KnowledgeArticle:
    id: str
    title: str
    content: str
    tags: tuple[str, ...] = ()
    source: str = "local"
    owner: str = "unassigned"
    last_reviewed: date | None = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"


@dataclass(frozen=True, slots=True)
class KnowledgeMatch:
    article: KnowledgeArticle
    score: int


@dataclass(frozen=True, slots=True)
class SemanticKnowledgeMatch:
    article: KnowledgeArticle
    similarity: float
