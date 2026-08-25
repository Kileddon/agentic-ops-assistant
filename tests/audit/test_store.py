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


def test_jsonl_audit_store_rejects_corrupted_event_log(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    store = JsonlAuditStore(path)

    with pytest.raises(AuditStoreError, match="invalid JSON"):
        store.list_events(10)
