from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.cli import main


def write_knowledge_file(path: Path) -> None:
    path.write_text(
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


def test_main_prints_matching_article(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    write_knowledge_file(knowledge_file)

    exit_code = main(
        ["--knowledge-file", str(knowledge_file), "database", "timeout"],
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "[score=6] Database timeout" in output


def test_main_reports_empty_result(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    write_knowledge_file(knowledge_file)

    exit_code = main(["--knowledge-file", str(knowledge_file), "cache"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output == "No matching articles found.\n"


def test_main_reports_invalid_knowledge_file(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.write_text("{invalid json}", encoding="utf-8")

    exit_code = main(["--knowledge-file", str(knowledge_file), "database"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "Error: Knowledge file is not valid JSON" in captured.err
