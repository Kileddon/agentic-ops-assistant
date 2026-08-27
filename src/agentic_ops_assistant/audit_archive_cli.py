import argparse
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from agentic_ops_assistant.audit.store import AuditStoreError, JsonlAuditStore


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify and archive a local audit log.")
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--archive-directory", type=Path, required=True)
    parsed = parser.parse_args(arguments)
    try:
        JsonlAuditStore(parsed.audit_file).list_events(1_000_000)
    except AuditStoreError as error:
        print(f"Error: {error}")
        return 1
    if not parsed.audit_file.exists():
        print("Error: Audit file does not exist.")
        return 1

    try:
        parsed.archive_directory.mkdir(parents=True, exist_ok=True)
        archive_name = datetime.now(UTC).strftime("audit-%Y%m%dT%H%M%SZ.jsonl")
        target = parsed.archive_directory / archive_name
        shutil.copy2(parsed.audit_file, target)
    except OSError as error:
        print(f"Error: Audit log could not be archived: {error}")
        return 1

    print(f"Archived audit log to {target}")
    return 0
