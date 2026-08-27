import argparse
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from agentic_ops_assistant.audit.service import AuditService
from agentic_ops_assistant.audit.store import AuditStoreError, JsonlAuditStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply an explicit audit-log retention cutoff.")
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--before", required=True, help="ISO 8601 timestamp with timezone")
    parser.add_argument("--confirm-prune", action="store_true")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parsed_arguments = build_parser().parse_args(arguments)

    if not parsed_arguments.confirm_prune:
        print("Refusing to prune without --confirm-prune.")
        return 2

    try:
        cutoff = datetime.fromisoformat(parsed_arguments.before)
    except ValueError:
        print("Error: --before must be an ISO 8601 timestamp.")
        return 2

    if cutoff.tzinfo is None:
        print("Error: --before must include a timezone.")
        return 2

    try:
        removed_count = AuditService(JsonlAuditStore(parsed_arguments.audit_file)).prune_before(
            cutoff,
        )
    except (AuditStoreError, ValueError) as error:
        print(f"Error: {error}")
        return 1

    print(f"Removed {removed_count} audit events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
