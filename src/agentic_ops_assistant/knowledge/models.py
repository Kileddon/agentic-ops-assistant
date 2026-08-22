from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeArticle:
    id: str
    title: str
    content: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeMatch:
    article: KnowledgeArticle
    score: int


@dataclass(frozen=True, slots=True)
class SemanticKnowledgeMatch:
    article: KnowledgeArticle
    similarity: float
