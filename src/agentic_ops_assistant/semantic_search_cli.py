import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.embeddings.client import (
    EmbeddingGenerationError,
    OllamaEmbeddingClient,
    TextEmbedder,
)
from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
from agentic_ops_assistant.knowledge.semantic_search import search_semantically


def main(
    argv: Sequence[str] | None = None,
    embedder: TextEmbedder | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Search the local knowledge base by semantic similarity.",
    )
    parser.add_argument(
        "--knowledge-file",
        type=Path,
        required=True,
        help="Path to a JSON knowledge file.",
    )
    parser.add_argument(
        "--model",
        default="nomic-embed-text",
        help="Local Ollama embedding model. Default: nomic-embed-text.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=5,
        help="Maximum number of results to return. Default: 5.",
    )
    parser.add_argument(
        "--minimum-similarity",
        type=float,
        default=0.58,
        help="Minimum semantic similarity to include. Default: 0.58.",
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="Operational issue description.",
    )
    arguments = parser.parse_args(argv)
    query = " ".join(arguments.query)

    try:
        articles = load_articles(arguments.knowledge_file)
    except KnowledgeLoadError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    search_embedder = embedder
    if search_embedder is None:
        search_embedder = OllamaEmbeddingClient(model=arguments.model)

    try:
        matches = search_semantically(
            query,
            articles,
            search_embedder,
            limit=arguments.limit,
            minimum_similarity=arguments.minimum_similarity,
        )
    except EmbeddingGenerationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if not matches:
        print("No knowledge articles available.")
        return 0

    for match in matches:
        print(f"[similarity={match.similarity:.3f}] {match.article.title}")

    return 0


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)

    if value <= 0:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.")

    return value


if __name__ == "__main__":
    raise SystemExit(main())
