from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from uuid import uuid4

from agentic_ops_assistant.audit.models import AuditEvent, AuditEventType
from agentic_ops_assistant.audit.store import AuditStore


class AuditService:
    def __init__(
        self,
        store: AuditStore,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock or _utc_now

    def record(
        self,
        event_type: AuditEventType,
        service: str,
        details: Mapping[str, str],
    ) -> AuditEvent:
        event = AuditEvent(
            id=uuid4(),
            occurred_at=self._clock(),
            event_type=event_type,
            service=service,
            details=details,
        )
        self._store.append(event)

        return event

    def list_events(self, limit: int) -> tuple[AuditEvent, ...]:
        return self._store.list_events(limit)

    def prune_before(self, cutoff: datetime) -> int:
        return self._store.prune_before(cutoff)


def _utc_now() -> datetime:
    return datetime.now(UTC)
