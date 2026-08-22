import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.embeddings.client import (
    EmbeddingGenerationError,
    OllamaEmbeddingClient,
    TextEmbedder,
)
from agentic_ops_assistant.investigation import investigate
from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
from agentic_ops_assistant.operations.status_loader import (
    ServiceStatusLoadError,
    load_service_statuses,
)
from agentic_ops_assistant.summarization.client import (
    OllamaSummaryClient,
    SummaryGenerationError,
)
from agentic_ops_assistant.summarization.service import (
    InvestigationSummaryService,
    SummaryClient,
)


def main(
    argv: Sequence[str] | None = None,
    client: SummaryClient | None = None,
    semantic_embedder: TextEmbedder | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize an operational investigation with a local language model.",
    )
    parser.add_argument(
        "--knowledge-file",
        type=Path,
        required=True,
        help="Path to a JSON knowledge file.",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        required=True,
        help="Path to a JSON service status file.",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:3b",
        help="Local Ollama model name. Default: qwen2.5:3b.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=5,
        help="Maximum number of knowledge matches. Default: 5.",
    )
    parser.add_argument(
        "--semantic-search",
        action="store_true",
        help="Include matches found by local semantic search.",
    )
    parser.add_argument(
        "service",
        help="Service to investigate.",
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
        statuses = load_service_statuses(arguments.status_file)
    except (KnowledgeLoadError, ServiceStatusLoadError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    embedder = None
    if arguments.semantic_search:
        embedder = semantic_embedder or OllamaEmbeddingClient(
            model="nomic-embed-text",
        )

    try:
        report = investigate(
            query=query,
            service=arguments.service,
            articles=articles,
            statuses=statuses,
            limit=arguments.limit,
            semantic_embedder=embedder,
        )
    except EmbeddingGenerationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    summary_client = client
    if summary_client is None:
        summary_client = OllamaSummaryClient(model=arguments.model)

    try:
        summary = InvestigationSummaryService(summary_client).summarize(report)
    except SummaryGenerationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(summary)
    return 0


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)

    if value <= 0:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.")

    return value


if __name__ == "__main__":
    raise SystemExit(main())
