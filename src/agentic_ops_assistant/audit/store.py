import hashlib
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

    def prune_before(self, cutoff: datetime) -> int: ...


class InMemoryAuditStore:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list_events(self, limit: int) -> tuple[AuditEvent, ...]:
        _validate_limit(limit)
        return tuple(reversed(self._events[-limit:]))

    def prune_before(self, cutoff: datetime) -> int:
        _validate_cutoff(cutoff)
        retained_events = [event for event in self._events if event.occurred_at >= cutoff]
        removed_count = len(self._events) - len(retained_events)
        self._events = retained_events
        return removed_count


class JsonlAuditStore:
    """Append-only JSON Lines audit store with a hash chain and fsync per event."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()

    def append(self, event: AuditEvent) -> None:
        try:
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                previous_hash = _verify_event_chain(_read_lines(self._path))
                payload = _event_payload(event)
                payload["previous_hash"] = previous_hash
                payload["event_hash"] = _event_hash(payload)
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
                lines = _read_lines(self._path)
        except OSError as error:
            raise AuditStoreError("Audit events could not be read.") from error

        _verify_event_chain(lines)
        events = tuple(_parse_event(line) for line in lines)
        return tuple(reversed(events[-limit:]))

    def prune_before(self, cutoff: datetime) -> int:
        _validate_cutoff(cutoff)

        try:
            with self._lock:
                lines = _read_lines(self._path)
                _verify_event_chain(lines)
                events = tuple(_parse_event(line) for line in lines)
                retained_events = tuple(event for event in events if event.occurred_at >= cutoff)
                removed_count = len(events) - len(retained_events)

                if removed_count:
                    _replace_events(self._path, retained_events)
        except OSError as error:
            raise AuditStoreError("Audit event retention could not be applied.") from error

        return removed_count


def _validate_limit(limit: int) -> None:
    if limit <= 0:
        raise ValueError("Audit event limit must be positive.")


def _validate_cutoff(cutoff: datetime) -> None:
    if cutoff.tzinfo is None:
        raise ValueError("Audit retention cutoff must include a timezone.")


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


def _event_payload(event: AuditEvent) -> dict[str, object]:
    return {
        "id": str(event.id),
        "occurred_at": event.occurred_at.isoformat(),
        "event_type": event.event_type.value,
        "service": event.service,
        "details": dict(event.details),
    }


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []

    return path.read_text(encoding="utf-8").splitlines()


def _verify_event_chain(lines: list[str]) -> str | None:
    previous_hash: str | None = None
    integrity_started = False

    for line in lines:
        payload = _json_object(line)
        event_hash = payload.pop("event_hash", None)
        stored_previous_hash = payload.pop("previous_hash", None)

        if event_hash is None and stored_previous_hash is None:
            if integrity_started:
                raise AuditStoreError("Audit event log has a broken integrity chain.")
            continue

        integrity_started = True
        if not isinstance(event_hash, str) or not isinstance(
            stored_previous_hash, (str, type(None))
        ):
            raise AuditStoreError("Audit event log has invalid integrity metadata.")

        if stored_previous_hash != previous_hash or event_hash != _event_hash(
            {**payload, "previous_hash": stored_previous_hash},
        ):
            raise AuditStoreError("Audit event log has a broken integrity chain.")

        previous_hash = event_hash

    return previous_hash


def _event_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _replace_events(path: Path, events: tuple[AuditEvent, ...]) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    previous_hash: str | None = None

    with temporary_path.open("w", encoding="utf-8") as audit_file:
        for event in events:
            payload = _event_payload(event)
            payload["previous_hash"] = previous_hash
            event_hash = _event_hash(payload)
            payload["event_hash"] = event_hash
            audit_file.write(json.dumps(payload, sort_keys=True) + "\n")
            previous_hash = event_hash
        audit_file.flush()
        os.fsync(audit_file.fileno())

    temporary_path.replace(path)


def _json_object(line: str) -> dict[str, object]:
    try:
        payload: object = json.loads(line)
    except json.JSONDecodeError as error:
        raise AuditStoreError("Audit event log contains invalid JSON.") from error

    if not isinstance(payload, dict):
        raise AuditStoreError("Audit event log contains an invalid event.")

    return {str(key): value for key, value in payload.items()}


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
