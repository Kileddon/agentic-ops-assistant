import re
from collections.abc import Sequence

from agentic_ops_assistant.knowledge.models import KnowledgeArticle, KnowledgeMatch

_WORD_PATTERN = re.compile(r"\w+")

_TITLE_MATCH_WEIGHT = 3
_TAG_MATCH_WEIGHT = 2
_CONTENT_MATCH_WEIGHT = 1


def search_knowledge(
    query: str,
    articles: Sequence[KnowledgeArticle],
    limit: int | None = None,
) -> list[KnowledgeMatch]:
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    if not query.strip():
        raise ValueError("Query must not be empty.")

    query_words = _tokenize(query)

    if not query_words:
        raise ValueError("Query must contain at least one word.")

    matches: list[KnowledgeMatch] = []

    for article in articles:
        score = _score_article(query_words, article)

        if score > 0:
            matches.append(KnowledgeMatch(article=article, score=score))

    matches.sort(key=lambda match: match.score, reverse=True)

    if limit is not None:
        return matches[:limit]

    return matches


def _score_article(
    query_words: set[str],
    article: KnowledgeArticle,
) -> int:
    title_words = _tokenize(article.title)
    tag_words = _tokenize(" ".join(article.tags))
    content_words = _tokenize(article.content)

    score = 0

    for word in query_words:
        if word in title_words:
            score += _TITLE_MATCH_WEIGHT
        elif word in tag_words:
            score += _TAG_MATCH_WEIGHT
        elif word in content_words:
            score += _CONTENT_MATCH_WEIGHT

    return score


def _tokenize(text: str) -> set[str]:
    return set(_WORD_PATTERN.findall(text.casefold()))
