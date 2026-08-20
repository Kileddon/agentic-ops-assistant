import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.investigation import InvestigationReport, investigate
from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
from agentic_ops_assistant.operations.status_loader import (
    ServiceStatusLoadError,
    load_service_statuses,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Investigate an operational issue using local data sources.",
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
        "--limit",
        type=_positive_int,
        default=5,
        help="Maximum number of knowledge matches. Default: 5.",
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

    report = investigate(
        query=query,
        service=arguments.service,
        articles=articles,
        statuses=statuses,
        limit=arguments.limit,
    )
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
        return

    print("Knowledge matches:")

    for match in report.knowledge_matches:
        print(f"[score={match.score}] {match.article.title}")


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)

    if value <= 0:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.")

    return value


if __name__ == "__main__":
    raise SystemExit(main())
