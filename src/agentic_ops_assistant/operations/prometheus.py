import json
from collections.abc import Sequence

import httpx2

from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


class PrometheusStatusError(RuntimeError):
    """Raised when Prometheus cannot provide a valid service status."""


class PrometheusStatusProvider:
    """Reads service availability from Prometheus without changing remote state."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        client: httpx2.Client | None = None,
    ) -> None:
        normalized_url = base_url.strip().rstrip("/")

        if not normalized_url:
            raise ValueError("Prometheus URL must not be blank.")

        if timeout_seconds <= 0:
            raise ValueError("Prometheus timeout must be positive.")

        self._base_url = normalized_url
        self._client = (
            httpx2.Client(timeout=timeout_seconds, trust_env=False) if client is None else client
        )

    def get_status(self, service: str) -> ServiceStatus | None:
        normalized_service = service.strip()

        if not normalized_service:
            raise ValueError("Service name must not be empty.")

        try:
            response = self._client.get(
                f"{self._base_url}/api/v1/query",
                params={"query": _availability_query(normalized_service)},
            )
            response.raise_for_status()
        except httpx2.HTTPError as error:
            raise PrometheusStatusError(
                "Prometheus availability query failed.",
            ) from error

        try:
            payload: object = response.json()
        except ValueError as error:
            raise PrometheusStatusError(
                "Prometheus returned invalid JSON.",
            ) from error

        availability_values = _parse_availability_values(payload)

        if not availability_values:
            return None

        return _to_service_status(normalized_service, availability_values)


def _availability_query(service: str) -> str:
    return f"up{{job={json.dumps(service)}}}"


def _parse_availability_values(payload: object) -> tuple[float, ...]:
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise PrometheusStatusError("Prometheus returned an unsuccessful response.")

    data = payload.get("data")

    if not isinstance(data, dict) or data.get("resultType") != "vector":
        raise PrometheusStatusError(
            "Prometheus response must contain an instant vector result.",
        )

    result = data.get("result")

    if not isinstance(result, list):
        raise PrometheusStatusError("Prometheus result must be an array.")

    return tuple(_parse_availability_value(sample) for sample in result)


def _parse_availability_value(sample: object) -> float:
    if not isinstance(sample, dict):
        raise PrometheusStatusError("Prometheus result sample must be an object.")

    value = sample.get("value")

    if not isinstance(value, list) or len(value) != 2 or not isinstance(value[1], str):
        raise PrometheusStatusError(
            "Prometheus result sample must contain a string value.",
        )

    try:
        availability = float(value[1])
    except ValueError as error:
        raise PrometheusStatusError(
            "Prometheus availability value must be numeric.",
        ) from error

    if availability not in (0.0, 1.0):
        raise PrometheusStatusError(
            "Prometheus availability value must be 0 or 1.",
        )

    return availability


def _to_service_status(
    service: str,
    availability_values: Sequence[float],
) -> ServiceStatus:
    up_targets = sum(value == 1.0 for value in availability_values)
    total_targets = len(availability_values)

    if up_targets == total_targets:
        return ServiceStatus(
            service=service,
            health=ServiceHealth.HEALTHY,
            summary=f"Prometheus reports all {total_targets} targets up.",
        )

    if up_targets == 0:
        return ServiceStatus(
            service=service,
            health=ServiceHealth.OUTAGE,
            summary=f"Prometheus reports all {total_targets} targets down.",
        )

    return ServiceStatus(
        service=service,
        health=ServiceHealth.DEGRADED,
        summary=(f"Prometheus reports {up_targets} of {total_targets} targets up."),
    )
