import argparse
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.audit.store import AuditStoreError
from agentic_ops_assistant.audit.transfer import copy_verified_audit_log


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify and back up a local audit archive.")
    parser.add_argument("--archive-file", type=Path, required=True)
    parser.add_argument("--backup-directory", type=Path, required=True)
    parsed = parser.parse_args(arguments)
    target = parsed.backup_directory / parsed.archive_file.name

    try:
        copy_verified_audit_log(source=parsed.archive_file, target=target)
    except AuditStoreError as error:
        print(f"Error: {error}")
        return 1

    print(f"Backed up audit archive to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
