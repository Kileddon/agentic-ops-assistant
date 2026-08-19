import argparse
from collections.abc import Sequence

from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.knowledge.search import search_knowledge

_DEMO_ARTICLES: tuple[KnowledgeArticle, ...] = (
    KnowledgeArticle(
        id="database-timeout",
        title="Database timeout",
        content="Check the connection pool and active database connections.",
        tags=("database", "timeout"),
    ),
    KnowledgeArticle(
        id="cache-eviction",
        title="Cache eviction",
        content="Review cache capacity and eviction rate.",
        tags=("cache",),
    ),
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Search the local operations knowledge base.",
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="Words to search for.",
    )
    arguments = parser.parse_args(argv)
    query = " ".join(arguments.query)

    matches = search_knowledge(query, _DEMO_ARTICLES)

    if not matches:
        print("No matching articles found.")
        return 0

    for match in matches:
        print(f"[score={match.score}] {match.article.title}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
