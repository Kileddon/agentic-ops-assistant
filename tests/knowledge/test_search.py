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

    assert matches == [KnowledgeMatch(article=article, score=3)]


def test_search_prefers_title_then_tags_then_content() -> None:
    title_match = KnowledgeArticle(
        id="title",
        title="Database maintenance",
        content="Run the scheduled maintenance task.",
    )
    tag_match = KnowledgeArticle(
        id="tag",
        title="Maintenance",
        content="Run the scheduled maintenance task.",
        tags=("database",),
    )
    content_match = KnowledgeArticle(
        id="content",
        title="Maintenance",
        content="Review database connection limits.",
    )

    matches = search_knowledge(
        "database",
        [content_match, tag_match, title_match],
    )

    assert [match.article.id for match in matches] == ["title", "tag", "content"]
    assert [match.score for match in matches] == [3, 2, 1]

    def test_search_limits_results() -> None:
        articles = [
            KnowledgeArticle(
                id="first",
                title="Database primary",
                content="Primary database maintenance.",
            ),
            KnowledgeArticle(
                id="second",
                title="Database replica",
                content="Replica database maintenance.",
            ),
            KnowledgeArticle(
                id="third",
                title="Database backup",
                content="Backup database maintenance.",
            ),
        ]

        matches = search_knowledge("database", articles, limit=2)

        assert [match.article.id for match in matches] == ["first", "second"]

    def test_search_rejects_non_positive_limit() -> None:
        with pytest.raises(ValueError, match="Limit must be positive"):
            search_knowledge("database", [], limit=0)


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


def test_search_ignores_punctuation() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout,",
        content="Check the connection pool.",
    )

    matches = search_knowledge("database timeout!", [article])

    assert matches == [KnowledgeMatch(article=article, score=6)]
