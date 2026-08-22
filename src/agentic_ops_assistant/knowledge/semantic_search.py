from collections.abc import Sequence

from agentic_ops_assistant.embeddings.client import TextEmbedder
from agentic_ops_assistant.embeddings.similarity import cosine_similarity
from agentic_ops_assistant.knowledge.models import (
    KnowledgeArticle,
    SemanticKnowledgeMatch,
)


def search_semantically(
    query: str,
    articles: Sequence[KnowledgeArticle],
    embedder: TextEmbedder,
    *,
    limit: int | None = None,
    minimum_similarity: float = 0.0,
) -> list[SemanticKnowledgeMatch]:
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    if not -1.0 <= minimum_similarity <= 1.0:
        raise ValueError("Minimum similarity must be between -1.0 and 1.0.")

    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError("Query must not be empty.")

    query_embedding = embedder.embed(normalized_query)
    matches: list[SemanticKnowledgeMatch] = []

    for article in articles:
        similarity = cosine_similarity(
            query_embedding,
            embedder.embed(_article_text(article)),
        )

        if similarity >= minimum_similarity:
            matches.append(
                SemanticKnowledgeMatch(
                    article=article,
                    similarity=similarity,
                ),
            )

    matches.sort(key=lambda match: match.similarity, reverse=True)

    if limit is None:
        return matches

    return matches[:limit]


def _article_text(article: KnowledgeArticle) -> str:
    return "\n".join(
        (
            article.title,
            article.content,
            *article.tags,
        ),
    )
