import argparse
from collections.abc import Mapping, Sequence

from agentic_ops_assistant.audit.store import AuditStoreError
from agentic_ops_assistant.audit.transfer import copy_verified_audit_log
from agentic_ops_assistant.settings import SettingsError, load_audit_backup_settings


def main(
    arguments: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Back up the latest verified audit archive.")
    parser.parse_args(() if arguments is None else arguments)

    try:
        settings = load_audit_backup_settings(environment)
    except SettingsError as error:
        print(f"Error: {error}")
        return 2

    archives = tuple(settings.archive_directory.glob("audit-*.jsonl"))
    if not archives:
        print("Error: No audit archives were found.")
        return 1

    source = max(archives, key=lambda path: path.stat().st_mtime)
    target = settings.backup_directory / source.name
    try:
        copy_verified_audit_log(source=source, target=target)
    except AuditStoreError as error:
        print(f"Error: {error}")
        return 1

    print(f"Backed up latest audit archive to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
