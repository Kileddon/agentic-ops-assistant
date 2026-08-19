from collections.abc import Sequence

from agentic_ops_assistant.knowledge.models import KnowledgeArticle, KnowledgeMatch


def search_knowledge(
    query: str,
    articles: Sequence[KnowledgeArticle],
) -> list[KnowledgeMatch]:
    normalized_query = query.strip().casefold()

    if not normalized_query:
        raise ValueError("Query must not be empty.")

    query_words = set(normalized_query.split())
    matches: list[KnowledgeMatch] = []

    for article in articles:
        searchable_text = " ".join(
            (article.title, article.content, *article.tags),
        ).casefold()
        article_words = set(searchable_text.split())
        score = len(query_words & article_words)

        if score > 0:
            matches.append(KnowledgeMatch(article=article, score=score))

    matches.sort(key=lambda match: match.score, reverse=True)

    return matches
