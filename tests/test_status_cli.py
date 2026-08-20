from pathlib import Path

from pytest import CaptureFixture

from agentic_ops_assistant.status_cli import main


def write_status_file(path: Path) -> None:
    path.write_text(
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


def test_main_prints_service_status(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    status_file = tmp_path / "service_statuses.json"
    write_status_file(status_file)

    exit_code = main(["--status-file", str(status_file), "payments-api"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output == "payments-api: degraded\nElevated database timeout rate.\n"


def test_main_reports_unknown_service(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    status_file = tmp_path / "service_statuses.json"
    write_status_file(status_file)

    exit_code = main(["--status-file", str(status_file), "catalog-api"])

    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert error_output == "No status found for service: catalog-api\n"
