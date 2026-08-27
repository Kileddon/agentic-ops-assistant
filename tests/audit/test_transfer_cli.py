from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pytest import CaptureFixture

from agentic_ops_assistant.audit.models import AuditEvent, AuditEventType
from agentic_ops_assistant.audit.store import JsonlAuditStore
from agentic_ops_assistant.audit_backup_cli import main as backup_main
from agentic_ops_assistant.audit_restore_cli import main as restore_main


def _write_verified_archive(path: Path) -> None:
    JsonlAuditStore(path).append(
        AuditEvent(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            occurred_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
            event_type=AuditEventType.INVESTIGATION_CREATED,
            service="payments-api",
            details={},
        ),
    )


def test_backup_main_copies_a_verified_archive(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    archive_file = tmp_path / "archive" / "audit.jsonl"
    _write_verified_archive(archive_file)
    backup_directory = tmp_path / "backup"

    exit_code = backup_main(
        ["--archive-file", str(archive_file), "--backup-directory", str(backup_directory)],
    )

    assert exit_code == 0
    assert (backup_directory / "audit.jsonl").read_text(encoding="utf-8") == archive_file.read_text(
        encoding="utf-8",
    )
    assert capsys.readouterr().out.startswith("Backed up audit archive to ")


def test_restore_main_requires_confirmation(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    archive_file = tmp_path / "archive" / "audit.jsonl"
    _write_verified_archive(archive_file)

    exit_code = restore_main(
        ["--archive-file", str(archive_file), "--restore-file", str(tmp_path / "restored.jsonl")],
    )

    assert exit_code == 2
    assert capsys.readouterr().out == "Refusing to restore without --confirm-restore.\n"


def test_restore_main_rejects_tampered_archive(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    archive_file = tmp_path / "archive" / "audit.jsonl"
    _write_verified_archive(archive_file)
    archive_file.write_text(
        archive_file.read_text(encoding="utf-8").replace("payments-api", "catalog-api"),
        encoding="utf-8",
    )
    restore_file = tmp_path / "restored.jsonl"

    exit_code = restore_main(
        [
            "--archive-file",
            str(archive_file),
            "--restore-file",
            str(restore_file),
            "--confirm-restore",
        ],
    )

    assert exit_code == 1
    assert "broken integrity chain" in capsys.readouterr().out
    assert not restore_file.exists()
