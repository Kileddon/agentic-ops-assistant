import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Protocol
from uuid import UUID

from agentic_ops_assistant.audit.models import AuditEvent, AuditEventType


class AuditStoreError(RuntimeError):
    """Raised when the audit store cannot persist or read an event."""


class AuditStore(Protocol):
    def append(self, event: AuditEvent) -> None: ...

    def list_events(self, limit: int) -> tuple[AuditEvent, ...]: ...


class InMemoryAuditStore:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list_events(self, limit: int) -> tuple[AuditEvent, ...]:
        _validate_limit(limit)
        return tuple(reversed(self._events[-limit:]))


class JsonlAuditStore:
    """Append-only JSON Lines audit store with a flush and fsync per event."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()

    def append(self, event: AuditEvent) -> None:
        payload = {
            "id": str(event.id),
            "occurred_at": event.occurred_at.isoformat(),
            "event_type": event.event_type.value,
            "service": event.service,
            "details": dict(event.details),
        }

        try:
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as audit_file:
                    audit_file.write(json.dumps(payload, sort_keys=True) + "\n")
                    audit_file.flush()
                    os.fsync(audit_file.fileno())
        except OSError as error:
            raise AuditStoreError("Audit event could not be persisted.") from error

    def list_events(self, limit: int) -> tuple[AuditEvent, ...]:
        _validate_limit(limit)

        if not self._path.exists():
            return ()

        try:
            with self._lock:
                lines = self._path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise AuditStoreError("Audit events could not be read.") from error

        events = tuple(_parse_event(line) for line in lines)
        return tuple(reversed(events[-limit:]))


def _validate_limit(limit: int) -> None:
    if limit <= 0:
        raise ValueError("Audit event limit must be positive.")


def _parse_event(line: str) -> AuditEvent:
    try:
        payload: object = json.loads(line)
    except json.JSONDecodeError as error:
        raise AuditStoreError("Audit event log contains invalid JSON.") from error

    if not isinstance(payload, dict):
        raise AuditStoreError("Audit event log contains an invalid event.")

    event = {str(key): value for key, value in payload.items()}

    try:
        event_id = UUID(_required_text(event, "id"))
        occurred_at = datetime.fromisoformat(_required_text(event, "occurred_at"))
        event_type = AuditEventType(_required_text(event, "event_type"))
    except (ValueError, TypeError) as error:
        raise AuditStoreError("Audit event log contains invalid event metadata.") from error

    if occurred_at.tzinfo is None:
        raise AuditStoreError("Audit event timestamp must include a timezone.")

    return AuditEvent(
        id=event_id,
        occurred_at=occurred_at,
        event_type=event_type,
        service=_required_text(event, "service"),
        details=_details(event.get("details")),
    )


def _required_text(event: dict[str, object], field_name: str) -> str:
    value = event.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise AuditStoreError(f"Audit event field '{field_name}' must be non-empty text.")

    return value


def _details(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise AuditStoreError("Audit event details must be an object.")

    details: dict[str, str] = {}

    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise AuditStoreError("Audit event details must contain text values.")

        details[key] = item

    return details
