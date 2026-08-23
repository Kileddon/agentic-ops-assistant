from pathlib import Path

import pytest

from agentic_ops_assistant.knowledge.evaluation import (
    RetrievalEvaluationCase,
    RetrievalEvaluationLoadError,
    evaluate_semantic_retrieval,
    load_retrieval_evaluation_cases,
)
from agentic_ops_assistant.knowledge.models import KnowledgeArticle


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if text == "connection pool exhausted" or "Database timeout" in text:
            return (1.0, 0.0)

        if text == "cache keeps removing entries" or "Cache eviction" in text:
            return (0.0, 1.0)

        raise AssertionError(f"Unexpected text: {text}")


def test_load_retrieval_evaluation_cases_reads_valid_json_file(tmp_path: Path) -> None:
    evaluation_file = tmp_path / "evaluation.json"
    evaluation_file.write_text(
        """
        [
          {
            "query": "connection pool exhausted",
            "expected_article_id": "database-timeout"
          }
        ]
        """,
        encoding="utf-8",
    )

    cases = load_retrieval_evaluation_cases(evaluation_file)

    assert cases == (
        RetrievalEvaluationCase(
            query="connection pool exhausted",
            expected_article_id="database-timeout",
        ),
    )


def test_load_retrieval_evaluation_cases_rejects_empty_file(tmp_path: Path) -> None:
    evaluation_file = tmp_path / "evaluation.json"
    evaluation_file.write_text("[]", encoding="utf-8")

    with pytest.raises(
        RetrievalEvaluationLoadError,
        match="must contain at least one case",
    ):
        load_retrieval_evaluation_cases(evaluation_file)


def test_evaluate_semantic_retrieval_reports_hit_rate_and_rank() -> None:
    database_article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )
    cache_article = KnowledgeArticle(
        id="cache-eviction",
        title="Cache eviction",
        content="Review cache capacity.",
        tags=("cache",),
    )
    cases = (
        RetrievalEvaluationCase(
            query="connection pool exhausted",
            expected_article_id="database-timeout",
        ),
        RetrievalEvaluationCase(
            query="cache keeps removing entries",
            expected_article_id="cache-eviction",
        ),
    )

    report = evaluate_semantic_retrieval(
        cases,
        [database_article, cache_article],
        FakeEmbedder(),
        minimum_similarity=0.5,
    )

    assert report.total_cases == 2
    assert report.passed_cases == 2
    assert report.hit_rate == 1.0
    assert [result.expected_rank for result in report.results] == [1, 1]


def test_evaluate_semantic_retrieval_rejects_unknown_expected_article() -> None:
    article = KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool.",
        tags=("database", "timeout"),
    )

    with pytest.raises(ValueError, match="unknown knowledge article: cache-eviction"):
        evaluate_semantic_retrieval(
            [
                RetrievalEvaluationCase(
                    query="connection pool exhausted",
                    expected_article_id="cache-eviction",
                ),
            ],
            [article],
            FakeEmbedder(),
        )
