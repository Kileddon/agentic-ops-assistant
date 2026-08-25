import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.embeddings.client import (
    EmbeddingGenerationError,
    OllamaEmbeddingClient,
    TextEmbedder,
)
from agentic_ops_assistant.investigation import InvestigationReport, investigate
from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
from agentic_ops_assistant.operations.prometheus import (
    PrometheusStatusError,
    PrometheusStatusProvider,
)
from agentic_ops_assistant.operations.provider import ServiceStatusProvider
from agentic_ops_assistant.operations.status import ServiceStatus
from agentic_ops_assistant.operations.status_loader import (
    ServiceStatusLoadError,
    load_service_statuses,
)


def main(
    argv: Sequence[str] | None = None,
    semantic_embedder: TextEmbedder | None = None,
    status_provider: ServiceStatusProvider | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Investigate an operational issue using local data sources.",
    )
    parser.add_argument(
        "--knowledge-file",
        type=Path,
        required=True,
        help="Path to a JSON knowledge file.",
    )
    status_source = parser.add_mutually_exclusive_group(required=True)
    status_source.add_argument(
        "--status-file",
        type=Path,
        help="Path to a JSON service status file.",
    )
    status_source.add_argument(
        "--prometheus-url",
        help="Base URL of the Prometheus server.",
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
    except KnowledgeLoadError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    statuses: tuple[ServiceStatus, ...] = ()
    provider = status_provider

    if arguments.status_file is not None:
        try:
            statuses = load_service_statuses(arguments.status_file)
        except ServiceStatusLoadError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2
    elif provider is None:
        prometheus_url = arguments.prometheus_url

        if prometheus_url is None:
            print("Error: Prometheus URL is required.", file=sys.stderr)
            return 2

        try:
            provider = PrometheusStatusProvider(prometheus_url)
        except ValueError as error:
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
            status_provider=provider,
        )
    except (EmbeddingGenerationError, PrometheusStatusError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    _print_report(report)
    return 0


def _print_report(report: InvestigationReport) -> None:
    print(f"Service: {report.service}")

    if report.service_status is None:
        print("Status: unknown")
    else:
        print(f"Status: {report.service_status.health.value}")
        print(f"Summary: {report.service_status.summary}")

    if not report.knowledge_matches:
        print("Knowledge matches: none")
    else:
        print("Knowledge matches:")

        for match in report.knowledge_matches:
            print(f"[score={match.score}] {match.article.title}")

    if report.semantic_matches:
        print("Semantic knowledge matches:")

        for semantic_match in report.semantic_matches:
            print(
                f"[similarity={semantic_match.similarity:.3f}] {semantic_match.article.title}",
            )


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)

    if value <= 0:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.")

    return value


if __name__ == "__main__":
    raise SystemExit(main())
