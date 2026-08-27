from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pytest import CaptureFixture

from agentic_ops_assistant.audit.models import AuditEvent, AuditEventType
from agentic_ops_assistant.audit.store import JsonlAuditStore
from agentic_ops_assistant.audit_archive_cli import main


def test_main_archives_a_verified_audit_log(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    audit_file = tmp_path / "events.jsonl"
    event = AuditEvent(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        occurred_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
        event_type=AuditEventType.INVESTIGATION_CREATED,
        service="payments-api",
        details={},
    )
    JsonlAuditStore(audit_file).append(event)
    archive_directory = tmp_path / "archive"

    exit_code = main(
        ["--audit-file", str(audit_file), "--archive-directory", str(archive_directory)],
    )

    archived_files = tuple(archive_directory.glob("audit-*.jsonl"))
    assert exit_code == 0
    assert capsys.readouterr().out.startswith("Archived audit log to ")
    assert len(archived_files) == 1
    assert archived_files[0].read_text(encoding="utf-8") == audit_file.read_text(
        encoding="utf-8",
    )


def test_main_refuses_to_archive_an_invalid_audit_log(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    audit_file = tmp_path / "events.jsonl"
    audit_file.write_text("not-json\n", encoding="utf-8")
    archive_directory = tmp_path / "archive"

    exit_code = main(
        ["--audit-file", str(audit_file), "--archive-directory", str(archive_directory)],
    )

    assert exit_code == 1
    assert "Audit event log contains invalid JSON" in capsys.readouterr().out
    assert not archive_directory.exists()
