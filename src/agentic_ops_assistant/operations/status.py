from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class ServiceHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OUTAGE = "outage"


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service: str
    health: ServiceHealth
    summary: str


def get_service_status(
    service: str,
    statuses: Sequence[ServiceStatus],
) -> ServiceStatus | None:
    normalized_service = service.strip().casefold()

    if not normalized_service:
        raise ValueError("Service name must not be empty.")

    for status in statuses:
        if status.service.casefold() == normalized_service:
            return status

    return None
