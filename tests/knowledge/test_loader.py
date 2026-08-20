from pathlib import Path

import pytest

from agentic_ops_assistant.knowledge.loader import KnowledgeLoadError, load_articles
from agentic_ops_assistant.knowledge.models import KnowledgeArticle


def test_load_articles_reads_valid_json_file(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.write_text(
        """
        [
          {
            "id": "database-timeout",
            "title": "Database timeout",
            "content": "Check the connection pool.",
            "tags": ["database", "timeout"]
          }
        ]
        """,
        encoding="utf-8",
    )

    articles = load_articles(knowledge_file)

    assert articles == (
        KnowledgeArticle(
            id="database-timeout",
            title="Database timeout",
            content="Check the connection pool.",
            tags=("database", "timeout"),
        ),
    )


def test_load_articles_rejects_invalid_json(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.write_text("{not valid json}", encoding="utf-8")

    with pytest.raises(KnowledgeLoadError, match="not valid JSON"):
        load_articles(knowledge_file)
