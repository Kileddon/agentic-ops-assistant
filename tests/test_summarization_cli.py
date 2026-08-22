from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.summarization.models import GeneratedSummary
from agentic_ops_assistant.summarization_cli import main


class FakeSummaryClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def summarize(self, prompt: str) -> GeneratedSummary:
        self.prompts.append(prompt)
        return GeneratedSummary(
            summary="The payments API is degraded because of database timeouts.",
            possible_cause=None,
            uncertainty="The report does not confirm a root cause.",
        )


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if text == "backend connections exhausted":
            return (1.0, 0.0)

        if "Database timeout" in text:
            return (1.0, 0.0)

        raise AssertionError(f"Unexpected text: {text}")


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
    assert captured.out == (
        "Summary: The payments API is degraded because of database timeouts.\n"
        "Possible cause: Not established.\n"
        "Uncertainty: The report does not confirm a root cause.\n"
    )
    assert len(client.prompts) == 1
    assert "payments-api" in client.prompts[0]
    assert "Database timeout" in client.prompts[0]


def test_main_adds_semantic_matches_to_summary_prompt(
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
    summary_client = FakeSummaryClient()

    exit_code = main(
        [
            "--knowledge-file",
            str(knowledge_file),
            "--status-file",
            str(status_file),
            "--semantic-search",
            "payments-api",
            "backend",
            "connections",
            "exhausted",
        ],
        client=summary_client,
        semantic_embedder=FakeEmbedder(),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        "Summary: The payments API is degraded because of database timeouts.\n"
        "Possible cause: Not established.\n"
        "Uncertainty: The report does not confirm a root cause.\n"
    )
    assert "Semantic knowledge matches:" in summary_client.prompts[0]
    assert "Database timeout" in summary_client.prompts[0]
