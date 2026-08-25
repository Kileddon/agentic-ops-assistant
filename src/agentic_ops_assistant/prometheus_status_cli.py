import argparse
import sys
from collections.abc import Sequence

from agentic_ops_assistant.operations.prometheus import (
    PrometheusStatusError,
    PrometheusStatusProvider,
)
from agentic_ops_assistant.operations.provider import ServiceStatusProvider


def main(
    argv: Sequence[str] | None = None,
    status_provider: ServiceStatusProvider | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Get a service availability status from Prometheus.",
    )
    parser.add_argument(
        "--prometheus-url",
        required=True,
        help="Base URL of the Prometheus server.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=_positive_float,
        default=5.0,
        help="HTTP timeout in seconds. Default: 5.",
    )
    parser.add_argument(
        "service",
        help="Service name, matched against the Prometheus job label.",
    )
    arguments = parser.parse_args(argv)

    provider = status_provider
    if provider is None:
        try:
            provider = PrometheusStatusProvider(
                arguments.prometheus_url,
                timeout_seconds=arguments.timeout_seconds,
            )
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2

    try:
        status = provider.get_status(arguments.service)
    except (PrometheusStatusError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if status is None:
        print(
            f"No Prometheus availability status found for service: {arguments.service}",
            file=sys.stderr,
        )
        return 1

    print(f"{status.service}: {status.health.value}")
    print(status.summary)

    return 0


def _positive_float(raw_value: str) -> float:
    value = float(raw_value)

    if value <= 0:
        raise argparse.ArgumentTypeError("Timeout must be a positive number.")

    return value


if __name__ == "__main__":
    raise SystemExit(main())
