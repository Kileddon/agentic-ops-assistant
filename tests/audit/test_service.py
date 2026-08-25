from datetime import UTC, datetime

from agentic_ops_assistant.audit.models import AuditEventType
from agentic_ops_assistant.audit.service import AuditService
from agentic_ops_assistant.audit.store import InMemoryAuditStore


def test_audit_service_records_event_with_utc_timestamp() -> None:
    occurred_at = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    store = InMemoryAuditStore()
    service = AuditService(store, clock=lambda: occurred_at)

    event = service.record(
        AuditEventType.INVESTIGATION_CREATED,
        "payments-api",
        {"keyword_match_count": "1"},
    )

    assert event.occurred_at == occurred_at
    assert event.details == {"keyword_match_count": "1"}
    assert service.list_events(1) == (event,)
