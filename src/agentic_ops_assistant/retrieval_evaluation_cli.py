import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.embeddings.client import (
    EmbeddingGenerationError,
    OllamaEmbeddingClient,
    TextEmbedder,
)
from agentic_ops_assistant.knowledge.evaluation import (
    RetrievalEvaluationLoadError,
    RetrievalEvaluationReport,
    evaluate_semantic_retrieval,
    load_retrieval_evaluation_cases,
)
from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles


def main(
    argv: Sequence[str] | None = None,
    embedder: TextEmbedder | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate local semantic retrieval against expected knowledge articles.",
    )
    parser.add_argument(
        "--knowledge-file",
        type=Path,
        required=True,
        help="Path to a JSON knowledge file.",
    )
    parser.add_argument(
        "--evaluation-file",
        type=Path,
        required=True,
        help="Path to a JSON retrieval evaluation file.",
    )
    parser.add_argument(
        "--model",
        default="nomic-embed-text",
        help="Local Ollama embedding model. Default: nomic-embed-text.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=3,
        help="Maximum retrieval results per case. Default: 3.",
    )
    parser.add_argument(
        "--minimum-similarity",
        type=float,
        default=0.6,
        help="Minimum semantic similarity to include. Default: 0.6.",
    )
    arguments = parser.parse_args(argv)

    try:
        articles = load_articles(arguments.knowledge_file)
        cases = load_retrieval_evaluation_cases(arguments.evaluation_file)
    except (KnowledgeLoadError, RetrievalEvaluationLoadError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    evaluation_embedder = embedder
    if evaluation_embedder is None:
        evaluation_embedder = OllamaEmbeddingClient(model=arguments.model)

    try:
        report = evaluate_semantic_retrieval(
            cases,
            articles,
            evaluation_embedder,
            limit=arguments.limit,
            minimum_similarity=arguments.minimum_similarity,
        )
    except (EmbeddingGenerationError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    _print_report(report)
    return 0


def _print_report(report: RetrievalEvaluationReport) -> None:
    for result in report.results:
        expected_rank = result.expected_rank

        if expected_rank is not None:
            match = result.matches[expected_rank - 1]
            print(
                f'[PASS] query="{result.case.query}" '
                f"expected={result.case.expected_article_id} "
                f"rank={expected_rank} "
                f"similarity={match.similarity:.3f}",
            )
            continue

        print(
            f'[MISS] query="{result.case.query}" expected={result.case.expected_article_id}',
        )

    print(
        f"Hit rate: {report.passed_cases}/{report.total_cases} ({report.hit_rate:.1%})",
    )


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)

    if value <= 0:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.")

    return value


if __name__ == "__main__":
    raise SystemExit(main())
