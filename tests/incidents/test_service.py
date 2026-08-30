from agentic_ops_assistant.incidents.models import (
    IncidentKind,
    IncidentSeverity,
    IncidentSignal,
)
from agentic_ops_assistant.incidents.notifications import format_incident_notification
from agentic_ops_assistant.incidents.service import IncidentInvestigationService
from agentic_ops_assistant.knowledge.models import KnowledgeArticle
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


class FakeDetector:
    def detect(self, service: str) -> tuple[IncidentSignal, ...]:
        return (
            IncidentSignal(
                service=service,
                kind=IncidentKind.HTTP_5XX,
                severity=IncidentSeverity.WARNING,
                summary="Prometheus reports 2 HTTP 5xx responses in five minutes.",
                investigation_query="HTTP 5xx errors gateway upstream",
                evidence_query="example-query",
                observed_value=2.0,
            ),
        )


class FakeStatusProvider:
    def get_status(self, service: str) -> ServiceStatus:
        return ServiceStatus(
            service=service,
            health=ServiceHealth.DEGRADED,
            summary="Prometheus reports 1 of 2 targets up.",
        )


def test_service_investigates_signal_and_formats_operator_notification() -> None:
    service = IncidentInvestigationService(
        detector=FakeDetector(),
        articles=(
            KnowledgeArticle(
                id="http-5xx",
                title="HTTP 5xx errors",
                content="Check upstream health.",
                tags=("http", "5xx"),
            ),
        ),
        status_provider=FakeStatusProvider(),
    )

    incident = service.investigate("gateway-api")[0]

    assert incident.investigation.knowledge_matches[0].article.id == "http-5xx"
    assert format_incident_notification(incident) == (
        "Incident detected: http_5xx (warning)\n"
        "Service: gateway-api\n"
        "Evidence: Prometheus reports 2 HTTP 5xx responses in five minutes.\n"
        "Potential causes: HTTP 5xx errors\n"
        "Recommended step: Propose collect_diagnostics. "
        "Read-only diagnostic collection is allowed."
    )
