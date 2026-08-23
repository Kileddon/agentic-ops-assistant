from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.retrieval_evaluation_cli import main


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if text == "connection pool exhausted" or "Database timeout" in text:
            return (1.0, 0.0)

        raise AssertionError(f"Unexpected text: {text}")


def test_main_prints_retrieval_evaluation_report(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
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
    evaluation_file = tmp_path / "evaluation.json"
    evaluation_file.write_text(
        """
        [
          {
            "query": "connection pool exhausted",
            "expected_article_id": "database-timeout"
          }
        ]
        """,
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--knowledge-file",
            str(knowledge_file),
            "--evaluation-file",
            str(evaluation_file),
            "--minimum-similarity",
            "0.5",
        ],
        embedder=FakeEmbedder(),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        '[PASS] query="connection pool exhausted" expected=database-timeout '
        "rank=1 similarity=1.000\n"
        "Hit rate: 1/1 (100.0%)\n"
    )
