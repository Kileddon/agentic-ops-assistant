from pytest import CaptureFixture

from agentic_ops_assistant.operations.prometheus import PrometheusStatusError
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus
from agentic_ops_assistant.prometheus_status_cli import main


class FakeStatusProvider:
    def __init__(self, status: ServiceStatus | None) -> None:
        self._status = status

    def get_status(self, service: str) -> ServiceStatus | None:
        return self._status


class FailingStatusProvider:
    def get_status(self, service: str) -> ServiceStatus | None:
        raise PrometheusStatusError("Prometheus availability query failed.")


def test_main_prints_prometheus_service_status(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = main(
        ["--prometheus-url", "http://prometheus.example", "payments-api"],
        status_provider=FakeStatusProvider(
            ServiceStatus(
                service="payments-api",
                health=ServiceHealth.HEALTHY,
                summary="Prometheus reports all 1 targets up.",
            ),
        ),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ("payments-api: healthy\nPrometheus reports all 1 targets up.\n")
    assert captured.err == ""


def test_main_reports_prometheus_error(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = main(
        ["--prometheus-url", "http://prometheus.example", "payments-api"],
        status_provider=FailingStatusProvider(),
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "Error: Prometheus availability query failed.\n"
