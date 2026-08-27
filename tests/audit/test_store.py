from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from agentic_ops_assistant.audit.models import AuditEvent, AuditEventType
from agentic_ops_assistant.audit.store import AuditStoreError, JsonlAuditStore


def test_jsonl_audit_store_persists_and_reads_events(tmp_path: Path) -> None:
    path = tmp_path / "audit" / "events.jsonl"
    store = JsonlAuditStore(path)
    event = AuditEvent(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        occurred_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        event_type=AuditEventType.INVESTIGATION_CREATED,
        service="payments-api",
        details={"keyword_match_count": "1"},
    )

    store.append(event)

    assert store.list_events(10) == (event,)
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_jsonl_audit_store_rejects_tampered_hash_chained_event(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    store = JsonlAuditStore(path)
    event = AuditEvent(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        occurred_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        event_type=AuditEventType.INVESTIGATION_CREATED,
        service="payments-api",
        details={"keyword_match_count": "1"},
    )
    store.append(event)
    path.write_text(
        path.read_text(encoding="utf-8").replace("payments-api", "catalog-api"),
        encoding="utf-8",
    )

    with pytest.raises(AuditStoreError, match="broken integrity chain"):
        store.list_events(10)


def test_jsonl_audit_store_prunes_old_events_and_keeps_a_valid_chain(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    store = JsonlAuditStore(path)
    old_event = AuditEvent(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        occurred_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        event_type=AuditEventType.INVESTIGATION_CREATED,
        service="payments-api",
        details={},
    )
    retained_event = AuditEvent(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        occurred_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        event_type=AuditEventType.APPROVAL_DECIDED,
        service="payments-api",
        details={},
    )
    store.append(old_event)
    store.append(retained_event)

    removed_count = store.prune_before(datetime(2026, 8, 20, 12, 0, tzinfo=UTC))

    assert removed_count == 1
    assert store.list_events(10) == (retained_event,)


def test_jsonl_audit_store_rejects_corrupted_event_log(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    store = JsonlAuditStore(path)

    with pytest.raises(AuditStoreError, match="invalid JSON"):
        store.list_events(10)
