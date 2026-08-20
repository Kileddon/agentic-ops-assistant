import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
from agentic_ops_assistant.knowledge.models import KnowledgeMatch
from agentic_ops_assistant.knowledge.search import search_knowledge


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Search the local operations knowledge base.",
    )
    parser.add_argument(
        "--knowledge-file",
        type=Path,
        required=True,
        help="Path to a JSON knowledge file.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=5,
        help="Maximum number of results to return. Default: 5.",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="Words to search for.",
    )
    arguments = parser.parse_args(argv)
    query = " ".join(arguments.query)

    try:
        articles = load_articles(arguments.knowledge_file)
    except KnowledgeLoadError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    matches = search_knowledge(query, articles, limit=arguments.limit)

    if arguments.output == "json":
        _print_json(matches)
        return 0

    if not matches:
        print("No matching articles found.")
        return 0

    for match in matches:
        print(f"[score={match.score}] {match.article.title}")

    return 0


def _print_json(matches: Sequence[KnowledgeMatch]) -> None:
    results = [
        {
            "id": match.article.id,
            "title": match.article.title,
            "content": match.article.content,
            "tags": list(match.article.tags),
            "score": match.score,
        }
        for match in matches
    ]

    print(json.dumps(results, ensure_ascii=False))


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)

    if value <= 0:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.")

    return value


if __name__ == "__main__":
    raise SystemExit(main())
