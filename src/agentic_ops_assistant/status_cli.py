import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_ops_assistant.operations.status import get_service_status
from agentic_ops_assistant.operations.status_loader import (
    ServiceStatusLoadError,
    load_service_statuses,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Get the status of an operational service.",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        required=True,
        help="Path to a JSON service status file.",
    )
    parser.add_argument(
        "service",
        help="Service name to look up.",
    )
    arguments = parser.parse_args(argv)

    try:
        statuses = load_service_statuses(arguments.status_file)
    except ServiceStatusLoadError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    status = get_service_status(arguments.service, statuses)

    if status is None:
        print(f"No status found for service: {arguments.service}", file=sys.stderr)
        return 1

    print(f"{status.service}: {status.health.value}")
    print(status.summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
