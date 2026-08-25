import httpx2
import pytest

from agentic_ops_assistant.operations.prometheus import (
    PrometheusStatusError,
    PrometheusStatusProvider,
)
from agentic_ops_assistant.operations.status import ServiceHealth


def test_prometheus_provider_returns_healthy_status_for_up_target() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/query"
        assert request.url.params["query"] == 'up{job="payments-api"}'

        return _success_response(["1"])

    provider = PrometheusStatusProvider(
        "http://prometheus.example",
        client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )

    status = provider.get_status("payments-api")

    assert status is not None
    assert status.health is ServiceHealth.HEALTHY
    assert status.summary == "Prometheus reports all 1 targets up."


def test_prometheus_provider_returns_degraded_status_for_mixed_targets() -> None:
    provider = PrometheusStatusProvider(
        "http://prometheus.example",
        client=httpx2.Client(
            transport=httpx2.MockTransport(
                lambda request: _success_response(["1", "0", "1"]),
            ),
        ),
    )

    status = provider.get_status("payments-api")

    assert status is not None
    assert status.health is ServiceHealth.DEGRADED
    assert status.summary == "Prometheus reports 2 of 3 targets up."


def test_prometheus_provider_returns_none_when_no_target_matches() -> None:
    provider = PrometheusStatusProvider(
        "http://prometheus.example",
        client=httpx2.Client(
            transport=httpx2.MockTransport(lambda request: _success_response([])),
        ),
    )

    assert provider.get_status("payments-api") is None


def test_prometheus_provider_raises_error_for_http_failure() -> None:
    provider = PrometheusStatusProvider(
        "http://prometheus.example",
        client=httpx2.Client(
            transport=httpx2.MockTransport(
                lambda request: httpx2.Response(503),
            ),
        ),
    )

    with pytest.raises(PrometheusStatusError, match="availability query failed"):
        provider.get_status("payments-api")


def test_prometheus_provider_raises_error_for_invalid_availability_value() -> None:
    provider = PrometheusStatusProvider(
        "http://prometheus.example",
        client=httpx2.Client(
            transport=httpx2.MockTransport(
                lambda request: _success_response(["0.5"]),
            ),
        ),
    )

    with pytest.raises(PrometheusStatusError, match="must be 0 or 1"):
        provider.get_status("payments-api")


def _success_response(values: list[str]) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"job": "payments-api"},
                        "value": ["1724419200", value],
                    }
                    for value in values
                ],
            },
        },
    )
