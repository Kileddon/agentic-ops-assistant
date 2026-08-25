from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.investigation_cli import main
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


class FakeStatusProvider:
    def get_status(self, service: str) -> ServiceStatus | None:
        return ServiceStatus(
            service=service,
            health=ServiceHealth.OUTAGE,
            summary="Prometheus reports all 1 targets down.",
        )


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


class FakeEmbedder:
    def embed(self, text: str) -> tuple[float, ...]:
        if text == "backend connections exhausted":
            return (1.0, 0.0)

        if "Database timeout" in text:
            return (1.0, 0.0)

        raise AssertionError(f"Unexpected text: {text}")


def test_main_prints_semantic_matches_when_enabled(
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
            "--semantic-search",
            "payments-api",
            "backend",
            "connections",
            "exhausted",
        ],
        semantic_embedder=FakeEmbedder(),
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output == (
        "Service: payments-api\n"
        "Status: degraded\n"
        "Summary: Elevated database timeout rate.\n"
        "Knowledge matches: none\n"
        "Semantic knowledge matches:\n"
        "[similarity=1.000] Database timeout\n"
    )


def test_main_uses_prometheus_status_provider(
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
            "--prometheus-url",
            "http://prometheus.example",
            "payments-api",
            "database",
        ],
        status_provider=FakeStatusProvider(),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        "Service: payments-api\n"
        "Status: outage\n"
        "Summary: Prometheus reports all 1 targets down.\n"
        "Knowledge matches:\n"
        "[score=3] Database timeout\n"
    )
