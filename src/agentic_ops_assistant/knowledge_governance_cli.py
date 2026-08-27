import argparse
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check knowledge article ownership and review dates."
    )
    parser.add_argument("--knowledge-file", type=Path, required=True)
    parser.add_argument("--max-review-age-days", type=int, default=180)
    parsed = parser.parse_args(arguments)
    if parsed.max_review_age_days <= 0:
        print("Error: --max-review-age-days must be positive.")
        return 2
    try:
        articles = load_articles(parsed.knowledge_file)
    except KnowledgeLoadError as error:
        print(f"Error: {error}")
        return 2

    cutoff = date.today() - timedelta(days=parsed.max_review_age_days)
    issues = 0
    for article in articles:
        if article.owner == "unassigned":
            print(f"[ISSUE] {article.id}: owner is unassigned")
            issues += 1
        if article.last_reviewed is None or article.last_reviewed < cutoff:
            print(f"[ISSUE] {article.id}: review is missing or stale")
            issues += 1
    print(f"Knowledge governance: {len(articles)} articles, {issues} issues")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
