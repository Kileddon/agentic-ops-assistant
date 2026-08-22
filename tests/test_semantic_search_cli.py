from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.semantic_search_cli import main


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if text == "connection pool exhausted":
            return (1.0, 0.0)

        if "Database timeout" in text:
            return (1.0, 0.0)

        raise AssertionError(f"Unexpected text: {text}")


def test_main_prints_semantic_search_result(
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

    exit_code = main(
        [
            "--knowledge-file",
            str(knowledge_file),
            "connection",
            "pool",
            "exhausted",
        ],
        embedder=FakeEmbedder(),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "[similarity=1.000] Database timeout\n"
