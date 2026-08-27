import json
from datetime import date
from pathlib import Path
from typing import Literal

from agentic_ops_assistant.knowledge.models import KnowledgeArticle


class KnowledgeLoadError(ValueError):
    """Raised when a knowledge file cannot be loaded or validated."""


def load_articles(path: Path) -> tuple[KnowledgeArticle, ...]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise KnowledgeLoadError(f"Cannot read knowledge file: {path}") from error
    except json.JSONDecodeError as error:
        raise KnowledgeLoadError(f"Knowledge file is not valid JSON: {path}") from error

    if not isinstance(payload, list):
        raise KnowledgeLoadError("Knowledge file must contain a JSON array.")

    articles = tuple(_parse_article(raw_article) for raw_article in payload)
    _validate_unique_article_ids(articles)

    return articles


def _parse_article(raw_article: object) -> KnowledgeArticle:
    if not isinstance(raw_article, dict):
        raise KnowledgeLoadError("Each knowledge article must be a JSON object.")

    article = {str(key): value for key, value in raw_article.items()}

    return KnowledgeArticle(
        id=_required_text(article, "id"),
        title=_required_text(article, "title"),
        content=_required_text(article, "content"),
        tags=_parse_tags(article),
        source=_optional_text(article, "source", default="local"),
        owner=_optional_text(article, "owner", default="unassigned"),
        last_reviewed=_parse_date(article),
        severity=_parse_severity(article),
    )


def _required_text(article: dict[str, object], field_name: str) -> str:
    value = article.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise KnowledgeLoadError(f"Article field '{field_name}' must be non-empty text.")

    return value


def _optional_text(article: dict[str, object], field_name: str, *, default: str) -> str:
    value = article.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeLoadError(f"Article field '{field_name}' must be non-empty text.")
    return value


def _parse_date(article: dict[str, object]) -> date | None:
    value = article.get("last_reviewed")
    if value is None:
        return None
    if not isinstance(value, str):
        raise KnowledgeLoadError("Article field 'last_reviewed' must be an ISO date.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise KnowledgeLoadError("Article field 'last_reviewed' must be an ISO date.") from error


def _parse_severity(
    article: dict[str, object],
) -> Literal["low", "medium", "high", "critical"]:
    value = article.get("severity", "medium")
    if value not in {"low", "medium", "high", "critical"}:
        raise KnowledgeLoadError("Article field 'severity' is invalid.")
    return value


def _parse_tags(article: dict[str, object]) -> tuple[str, ...]:
    raw_tags = article.get("tags", [])

    if not isinstance(raw_tags, list):
        raise KnowledgeLoadError("Article field 'tags' must be an array.")

    tags: list[str] = []

    for tag in raw_tags:
        if not isinstance(tag, str) or not tag.strip():
            raise KnowledgeLoadError("Every tag must be non-empty text.")

        tags.append(tag)

    return tuple(tags)


def _validate_unique_article_ids(
    articles: tuple[KnowledgeArticle, ...],
) -> None:
    seen_ids: set[str] = set()

    for article in articles:
        if article.id in seen_ids:
            raise KnowledgeLoadError(
                f"Knowledge file contains duplicate article id: {article.id}",
            )

        seen_ids.add(article.id)
