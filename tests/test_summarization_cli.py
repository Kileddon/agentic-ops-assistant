from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.summarization_cli import main


class FakeSummaryClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def summarize(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "The payments API is degraded because of database timeouts."


def test_main_prints_summary_from_local_model_client(
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
    client = FakeSummaryClient()

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
        client=client,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ("The payments API is degraded because of database timeouts.\n")
    assert len(client.prompts) == 1
    assert "payments-api" in client.prompts[0]
    assert "Database timeout" in client.prompts[0]
