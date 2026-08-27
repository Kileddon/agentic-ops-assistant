import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from agentic_ops_assistant.embeddings.client import TextEmbedder
from agentic_ops_assistant.knowledge.models import (
    KnowledgeArticle,
    SemanticKnowledgeMatch,
)
from agentic_ops_assistant.knowledge.semantic_search import search_semantically


class RetrievalEvaluationLoadError(ValueError):
    """Raised when a retrieval evaluation file cannot be loaded or validated."""


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    query: str
    expected_article_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationResult:
    case: RetrievalEvaluationCase
    expected_rank: int | None
    matches: tuple[SemanticKnowledgeMatch, ...]

    @property
    def passed(self) -> bool:
        if not self.case.expected_article_ids:
            return not self.matches

        return self.expected_rank is not None


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationReport:
    results: tuple[RetrievalEvaluationResult, ...]

    @property
    def passed_cases(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def positive_results(self) -> tuple[RetrievalEvaluationResult, ...]:
        return tuple(result for result in self.results if result.case.expected_article_ids)

    @property
    def negative_results(self) -> tuple[RetrievalEvaluationResult, ...]:
        return tuple(result for result in self.results if not result.case.expected_article_ids)

    @property
    def recall_at_1(self) -> float:
        if not self.positive_results:
            return 0.0

        return sum(result.expected_rank == 1 for result in self.positive_results) / len(
            self.positive_results,
        )

    @property
    def recall_at_limit(self) -> float:
        if not self.positive_results:
            return 0.0

        return sum(result.passed for result in self.positive_results) / len(
            self.positive_results,
        )

    @property
    def false_positive_rate(self) -> float:
        if not self.negative_results:
            return 0.0

        return sum(bool(result.matches) for result in self.negative_results) / len(
            self.negative_results,
        )


def load_retrieval_evaluation_cases(
    path: Path,
) -> tuple[RetrievalEvaluationCase, ...]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RetrievalEvaluationLoadError(
            f"Cannot read retrieval evaluation file: {path}",
        ) from error
    except json.JSONDecodeError as error:
        raise RetrievalEvaluationLoadError(
            "Retrieval evaluation file is not valid JSON.",
        ) from error

    if not isinstance(payload, list):
        raise RetrievalEvaluationLoadError(
            "Retrieval evaluation file must contain a JSON array.",
        )

    cases = tuple(_parse_case(raw_case) for raw_case in payload)

    if not cases:
        raise RetrievalEvaluationLoadError(
            "Retrieval evaluation file must contain at least one case.",
        )

    return cases


def evaluate_semantic_retrieval(
    cases: Sequence[RetrievalEvaluationCase],
    articles: Sequence[KnowledgeArticle],
    embedder: TextEmbedder,
    *,
    limit: int = 3,
    minimum_similarity: float = 0.58,
) -> RetrievalEvaluationReport:
    article_ids = {article.id for article in articles}

    for case in cases:
        for expected_article_id in case.expected_article_ids:
            if expected_article_id not in article_ids:
                raise ValueError(
                    "Evaluation case references an unknown knowledge article: "
                    f"{expected_article_id}",
                )

    results = tuple(
        _evaluate_case(
            case,
            articles,
            embedder,
            limit=limit,
            minimum_similarity=minimum_similarity,
        )
        for case in cases
    )

    return RetrievalEvaluationReport(results=results)


def _parse_case(raw_case: object) -> RetrievalEvaluationCase:
    if not isinstance(raw_case, dict):
        raise RetrievalEvaluationLoadError(
            "Each retrieval evaluation case must be a JSON object.",
        )

    case = {str(key): value for key, value in raw_case.items()}

    return RetrievalEvaluationCase(
        query=_required_text(case, "query"),
        expected_article_ids=_expected_article_ids(case),
    )


def _required_text(case: dict[str, object], field_name: str) -> str:
    value = case.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise RetrievalEvaluationLoadError(
            f"Evaluation case field '{field_name}' must be non-empty text.",
        )

    return value


def _expected_article_ids(case: dict[str, object]) -> tuple[str, ...]:
    value = case.get("expected_article_ids")

    if not isinstance(value, list):
        raise RetrievalEvaluationLoadError(
            "Evaluation case field 'expected_article_ids' must be an array.",
        )

    article_ids: list[str] = []

    for article_id in value:
        if not isinstance(article_id, str) or not article_id.strip():
            raise RetrievalEvaluationLoadError(
                "Every expected article id must be non-empty text.",
            )

        article_ids.append(article_id)

    if len(set(article_ids)) != len(article_ids):
        raise RetrievalEvaluationLoadError(
            "Evaluation case must not contain duplicate expected article ids.",
        )

    return tuple(article_ids)


def _evaluate_case(
    case: RetrievalEvaluationCase,
    articles: Sequence[KnowledgeArticle],
    embedder: TextEmbedder,
    *,
    limit: int,
    minimum_similarity: float,
) -> RetrievalEvaluationResult:
    matches = tuple(
        search_semantically(
            case.query,
            articles,
            embedder,
            limit=limit,
            minimum_similarity=minimum_similarity,
        ),
    )
    expected_rank = next(
        (
            rank
            for rank, match in enumerate(matches, start=1)
            if match.article.id in case.expected_article_ids
        ),
        None,
    )

    return RetrievalEvaluationResult(
        case=case,
        expected_rank=expected_rank,
        matches=matches,
    )
