import pytest

from agentic_ops_assistant.knowledge.models import KnowledgeArticle, KnowledgeMatch
from agentic_ops_assistant.knowledge.search import search_knowledge


def test_search_is_case_insensitive() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
    )

    matches = search_knowledge("DATABASE", [article])

    assert matches == [KnowledgeMatch(article=article, score=1)]


def test_search_orders_results_by_score() -> None:
    one_word_match = KnowledgeArticle(
        id="database",
        title="Database alerts",
        content="Review alert settings.",
    )
    two_word_match = KnowledgeArticle(
        id="timeout",
        title="Database timeout",
        content="Check the connection pool.",
    )

    matches = search_knowledge(
        "database timeout",
        [one_word_match, two_word_match],
    )

    assert [match.article.id for match in matches] == ["timeout", "database"]
    assert [match.score for match in matches] == [2, 1]


def test_search_returns_empty_list_when_nothing_matches() -> None:
    article = KnowledgeArticle(
        id="cache",
        title="Cache eviction",
        content="Review cache configuration.",
    )

    matches = search_knowledge("database", [article])

    assert matches == []


@pytest.mark.parametrize("query", ["", "   \t\n"])
def test_search_rejects_blank_query(query: str) -> None:
    with pytest.raises(ValueError, match="Query must not be empty"):
        search_knowledge(query, [])
