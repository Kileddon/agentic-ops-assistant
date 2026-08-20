import json
from pathlib import Path

from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


class ServiceStatusLoadError(ValueError):
    """Raised when a service status file cannot be loaded or validated."""


def load_service_statuses(path: Path) -> tuple[ServiceStatus, ...]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ServiceStatusLoadError(
            f"Cannot read service status file: {path}",
        ) from error
    except json.JSONDecodeError as error:
        raise ServiceStatusLoadError(
            f"Service status file is not valid JSON: {path}",
        ) from error

    if not isinstance(payload, list):
        raise ServiceStatusLoadError("Service status file must contain a JSON array.")

    statuses = tuple(_parse_status(raw_status) for raw_status in payload)
    _validate_unique_services(statuses)

    return statuses


def _parse_status(raw_status: object) -> ServiceStatus:
    if not isinstance(raw_status, dict):
        raise ServiceStatusLoadError("Each service status must be a JSON object.")

    record = {str(key): value for key, value in raw_status.items()}
    health = _parse_health(record)

    return ServiceStatus(
        service=_required_text(record, "service"),
        health=health,
        summary=_required_text(record, "summary"),
    )


def _parse_health(record: dict[str, object]) -> ServiceHealth:
    raw_health = _required_text(record, "status")

    try:
        return ServiceHealth(raw_health)
    except ValueError as error:
        raise ServiceStatusLoadError(
            f"Unsupported service health value: {raw_health}",
        ) from error


def _required_text(record: dict[str, object], field_name: str) -> str:
    value = record.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise ServiceStatusLoadError(
            f"Service status field '{field_name}' must be non-empty text.",
        )

    return value


def _validate_unique_services(statuses: tuple[ServiceStatus, ...]) -> None:
    seen_services: set[str] = set()

    for status in statuses:
        normalized_service = status.service.casefold()

        if normalized_service in seen_services:
            raise ServiceStatusLoadError(
                f"Service status file contains duplicate service: {status.service}",
            )

        seen_services.add(normalized_service)
