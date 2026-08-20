import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
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

    matches = search_knowledge(query, articles)

    if not matches:
        print("No matching articles found.")
        return 0

    for match in matches:
        print(f"[score={match.score}] {match.article.title}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
