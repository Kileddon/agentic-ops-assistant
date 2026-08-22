import pytest

from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.knowledge.semantic_search import search_semantically


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if text == "connection pool exhausted":
            return (1.0, 0.0)

        if "Database timeout" in text:
            return (1.0, 0.0)

        if "Cache eviction" in text:
            return (0.0, 1.0)

        raise AssertionError(f"Unexpected text: {text}")


def test_search_semantically_ranks_article_with_similar_meaning_first() -> None:
    database_article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )
    cache_article = KnowledgeArticle(
        id="cache-eviction",
        title="Cache eviction",
        content="Inspect cache memory usage.",
        tags=("cache",),
    )

    matches = search_semantically(
        "connection pool exhausted",
        [cache_article, database_article],
        FakeEmbedder(),
    )

    assert [match.article.id for match in matches] == [
        "database-timeout",
        "cache-eviction",
    ]
    assert matches[0].similarity == 1.0
    assert matches[1].similarity == 0.0


def test_search_semantically_applies_limit() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )

    matches = search_semantically(
        "connection pool exhausted",
        [article],
        FakeEmbedder(),
        limit=1,
    )

    assert len(matches) == 1


def test_search_semantically_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="Query must not be empty"):
        search_semantically("   ", [], FakeEmbedder())


def test_search_semantically_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="Limit must be positive"):
        search_semantically(
            "connection pool exhausted",
            [],
            FakeEmbedder(),
            limit=0,
        )


def test_search_semantically_filters_low_similarity_matches() -> None:
    database_article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )
    cache_article = KnowledgeArticle(
        id="cache-eviction",
        title="Cache eviction",
        content="Inspect cache memory usage.",
        tags=("cache",),
    )

    matches = search_semantically(
        "connection pool exhausted",
        [database_article, cache_article],
        FakeEmbedder(),
        minimum_similarity=0.5,
    )

    assert [match.article.id for match in matches] == ["database-timeout"]


def test_search_semantically_rejects_invalid_minimum_similarity() -> None:
    with pytest.raises(
        ValueError,
        match="Minimum similarity must be between -1.0 and 1.0",
    ):
        search_semantically(
            "connection pool exhausted",
            [],
            FakeEmbedder(),
            minimum_similarity=1.1,
        )
