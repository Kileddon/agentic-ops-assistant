from agentic_ops_assistant.incidents.models import IncidentKind, IncidentSeverity
from agentic_ops_assistant.incidents.prometheus import PrometheusIncidentDetector
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


class FakeStatusProvider:
    def __init__(self, status: ServiceStatus | None) -> None:
        self._status = status

    def get_status(self, service: str) -> ServiceStatus | None:
        return self._status


class FakeQueryClient:
    def __init__(self, values: tuple[float | None, ...]) -> None:
        self._values = iter(values)

    def query_scalar(self, query: str) -> float | None:
        return next(self._values)


def test_detector_creates_outage_error_and_latency_signals() -> None:
    detector = PrometheusIncidentDetector(
        status_provider=FakeStatusProvider(
            ServiceStatus(
                service="agentic-ops-assistant",
                health=ServiceHealth.OUTAGE,
                summary="Prometheus reports all 1 targets down.",
            ),
        ),
        query_client=FakeQueryClient((3.0, 1_250.0)),
    )

    signals = detector.detect("agentic-ops-assistant")

    assert [signal.kind for signal in signals] == [
        IncidentKind.TARGET_DOWN,
        IncidentKind.HTTP_5XX,
        IncidentKind.HIGH_LATENCY,
    ]
    assert signals[0].severity is IncidentSeverity.CRITICAL
    assert signals[1].observed_value == 3.0
    assert signals[2].observed_value == 1_250.0


def test_detector_returns_no_signal_for_healthy_service_without_metric_breach() -> None:
    detector = PrometheusIncidentDetector(
        status_provider=FakeStatusProvider(
            ServiceStatus(
                service="agentic-ops-assistant",
                health=ServiceHealth.HEALTHY,
                summary="Prometheus reports all 1 targets up.",
            ),
        ),
        query_client=FakeQueryClient((0.0, 200.0)),
    )

    assert detector.detect("agentic-ops-assistant") == ()
