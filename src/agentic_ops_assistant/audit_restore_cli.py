import argparse
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.audit.store import AuditStoreError
from agentic_ops_assistant.audit.transfer import copy_verified_audit_log


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify and restore a local audit archive.")
    parser.add_argument("--archive-file", type=Path, required=True)
    parser.add_argument("--restore-file", type=Path, required=True)
    parser.add_argument("--confirm-restore", action="store_true")
    parsed = parser.parse_args(arguments)

    if not parsed.confirm_restore:
        print("Refusing to restore without --confirm-restore.")
        return 2

    try:
        copy_verified_audit_log(source=parsed.archive_file, target=parsed.restore_file)
    except AuditStoreError as error:
        print(f"Error: {error}")
        return 1

    print(f"Restored verified audit archive to {parsed.restore_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
