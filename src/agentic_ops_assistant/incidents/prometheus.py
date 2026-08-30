import json
from typing import Protocol

import httpx2

from agentic_ops_assistant.incidents.models import (
    IncidentKind,
    IncidentSeverity,
    IncidentSignal,
)
from agentic_ops_assistant.operations.prometheus import PrometheusStatusError
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


class ScalarPrometheusQuery(Protocol):
    def query_scalar(self, query: str) -> float | None: ...


class PrometheusStatusQuery(Protocol):
    def get_status(self, service: str) -> ServiceStatus | None: ...


class PrometheusInstantQueryClient:
    """Executes read-only Prometheus instant queries that yield one scalar value."""

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

    def query_scalar(self, query: str) -> float | None:
        if not query.strip():
            raise ValueError("Prometheus query must not be blank.")

        try:
            response = self._client.get(
                f"{self._base_url}/api/v1/query",
                params={"query": query},
            )
            response.raise_for_status()
        except httpx2.HTTPError as error:
            raise PrometheusStatusError("Prometheus incident query failed.") from error

        try:
            payload: object = response.json()
        except ValueError as error:
            raise PrometheusStatusError("Prometheus returned invalid JSON.") from error

        return _parse_scalar(payload)


class PrometheusIncidentDetector:
    def __init__(
        self,
        *,
        status_provider: PrometheusStatusQuery,
        query_client: ScalarPrometheusQuery,
        latency_threshold_ms: float = 1_000.0,
    ) -> None:
        if latency_threshold_ms <= 0:
            raise ValueError("Latency threshold must be positive.")

        self._status_provider = status_provider
        self._query_client = query_client
        self._latency_threshold_ms = latency_threshold_ms

    def detect(self, service: str) -> tuple[IncidentSignal, ...]:
        normalized_service = service.strip()
        if not normalized_service:
            raise ValueError("Service name must not be blank.")

        signals: list[IncidentSignal] = []
        status = self._status_provider.get_status(normalized_service)

        if status is not None and status.health is ServiceHealth.OUTAGE:
            signals.append(
                IncidentSignal(
                    service=normalized_service,
                    kind=IncidentKind.TARGET_DOWN,
                    severity=IncidentSeverity.CRITICAL,
                    summary=status.summary,
                    investigation_query="service unavailable target down",
                    evidence_query=_availability_query(normalized_service),
                )
            )
        elif status is not None and status.health is ServiceHealth.DEGRADED:
            signals.append(
                IncidentSignal(
                    service=normalized_service,
                    kind=IncidentKind.TARGET_DOWN,
                    severity=IncidentSeverity.WARNING,
                    summary=status.summary,
                    investigation_query="service partially unavailable target down",
                    evidence_query=_availability_query(normalized_service),
                )
            )

        error_count = self._query_client.query_scalar(_http_5xx_query(normalized_service))
        if error_count is not None and error_count > 0:
            signals.append(
                IncidentSignal(
                    service=normalized_service,
                    kind=IncidentKind.HTTP_5XX,
                    severity=IncidentSeverity.WARNING,
                    summary=(
                        f"Prometheus reports {error_count:g} HTTP 5xx responses in five minutes."
                    ),
                    investigation_query="HTTP 5xx errors gateway upstream",
                    evidence_query=_http_5xx_query(normalized_service),
                    observed_value=error_count,
                )
            )

        latency_ms = self._query_client.query_scalar(_latency_query(normalized_service))
        if latency_ms is not None and latency_ms >= self._latency_threshold_ms:
            signals.append(
                IncidentSignal(
                    service=normalized_service,
                    kind=IncidentKind.HIGH_LATENCY,
                    severity=IncidentSeverity.WARNING,
                    summary=(
                        "Prometheus reports average API latency "
                        f"{latency_ms:.0f}ms in five minutes."
                    ),
                    investigation_query="slow API response high latency dependency timeout",
                    evidence_query=_latency_query(normalized_service),
                    observed_value=latency_ms,
                )
            )

        return tuple(signals)


def _availability_query(service: str) -> str:
    return f"up{{job={json.dumps(service)}}}"


def _http_5xx_query(service: str) -> str:
    return (
        "sum(increase(agentic_ops_http_response_status_total"
        f'{{job={json.dumps(service)},status=~"5.."}}[5m]))'
    )


def _latency_query(service: str) -> str:
    return (
        "sum(rate(agentic_ops_http_request_duration_milliseconds_total"
        f"{{job={json.dumps(service)}}}[5m])) / "
        "sum(rate(agentic_ops_http_requests_total"
        f"{{job={json.dumps(service)}}}[5m]))"
    )


def _parse_scalar(payload: object) -> float | None:
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise PrometheusStatusError("Prometheus returned an unsuccessful response.")

    data = payload.get("data")
    if not isinstance(data, dict) or data.get("resultType") != "vector":
        raise PrometheusStatusError("Prometheus response must contain an instant vector result.")

    result = data.get("result")
    if not isinstance(result, list):
        raise PrometheusStatusError("Prometheus result must be an array.")
    if not result:
        return None
    if len(result) != 1 or not isinstance(result[0], dict):
        raise PrometheusStatusError("Prometheus incident query must return one value.")

    value = result[0].get("value")
    if not isinstance(value, list) or len(value) != 2 or not isinstance(value[1], str):
        raise PrometheusStatusError("Prometheus result sample must contain a string value.")

    try:
        return float(value[1])
    except ValueError as error:
        raise PrometheusStatusError("Prometheus incident value must be numeric.") from error
