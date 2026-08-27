import shutil
from pathlib import Path

from agentic_ops_assistant.audit.store import AuditStoreError, JsonlAuditStore


def copy_verified_audit_log(*, source: Path, target: Path) -> None:
    if not source.is_file():
        raise AuditStoreError("Audit file does not exist.")

    JsonlAuditStore(source).list_events(1_000_000)

    if target.exists():
        raise AuditStoreError("Audit destination already exists.")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    except OSError as error:
        raise AuditStoreError("Audit log could not be copied.") from error
