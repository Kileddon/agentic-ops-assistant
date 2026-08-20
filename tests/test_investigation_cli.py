from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.investigation_cli import main


def test_main_prints_investigation_report(
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
    status_file = tmp_path / "service_statuses.json"
    status_file.write_text(
        """
        [
          {
            "service": "payments-api",
            "status": "degraded",
            "summary": "Elevated database timeout rate."
          }
        ]
        """,
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--knowledge-file",
            str(knowledge_file),
            "--status-file",
            str(status_file),
            "payments-api",
            "database",
            "timeout",
        ],
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output == (
        "Service: payments-api\n"
        "Status: degraded\n"
        "Summary: Elevated database timeout rate.\n"
        "Knowledge matches:\n"
        "[score=6] Database timeout\n"
    )
