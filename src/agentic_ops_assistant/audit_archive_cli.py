import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from agentic_ops_assistant.audit.store import AuditStoreError
from agentic_ops_assistant.audit.transfer import copy_verified_audit_log


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify and archive a local audit log.")
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--archive-directory", type=Path, required=True)
    parsed = parser.parse_args(arguments)
    archive_name = datetime.now(UTC).strftime("audit-%Y%m%dT%H%M%SZ.jsonl")
    target = parsed.archive_directory / archive_name

    try:
        copy_verified_audit_log(source=parsed.audit_file, target=target)
    except AuditStoreError as error:
        print(f"Error: {error}")
        return 1

    print(f"Archived audit log to {target}")
    return 0
