from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pytest import CaptureFixture

from agentic_ops_assistant.audit.models import AuditEvent, AuditEventType
from agentic_ops_assistant.audit.store import JsonlAuditStore
from agentic_ops_assistant.audit_backup_latest_cli import main


def test_main_backs_up_the_latest_archive(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    archive_directory = tmp_path / "archives"
    archive_file = archive_directory / "audit-20260827T120000Z.jsonl"
    JsonlAuditStore(archive_file).append(
        AuditEvent(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            occurred_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
            event_type=AuditEventType.INVESTIGATION_CREATED,
            service="payments-api",
            details={},
        ),
    )
    backup_directory = tmp_path / "backup"

    exit_code = main(
        environment={
            "OPS_AUDIT_ARCHIVE_DIRECTORY": str(archive_directory),
            "OPS_AUDIT_BACKUP_DIRECTORY": str(backup_directory),
        },
    )

    assert exit_code == 0
    assert (backup_directory / archive_file.name).is_file()
    assert capsys.readouterr().out.startswith("Backed up latest audit archive to ")
