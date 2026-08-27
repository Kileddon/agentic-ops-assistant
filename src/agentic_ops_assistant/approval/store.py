import sqlite3
from pathlib import Path
from typing import Protocol
from uuid import UUID

from agentic_ops_assistant.actions.models import ActionType, ProposedAction
from agentic_ops_assistant.approval.models import ApprovalRequest, ApprovalStatus


class ApprovalStore(Protocol):
    def get(self, approval_id: UUID) -> ApprovalRequest | None: ...

    def save(self, approval_request: ApprovalRequest) -> None: ...


class InMemoryApprovalStore:
    def __init__(self) -> None:
        self._requests: dict[UUID, ApprovalRequest] = {}

    def get(self, approval_id: UUID) -> ApprovalRequest | None:
        return self._requests.get(approval_id)

    def save(self, approval_request: ApprovalRequest) -> None:
        self._requests[approval_request.id] = approval_request


class SqliteApprovalStore:
    def __init__(self, path: str) -> None:
        self._path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """,
            )

    def get(self, approval_id: UUID) -> ApprovalRequest | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, service, action_type, rationale, status "
                "FROM approval_requests WHERE id = ?",
                (str(approval_id),),
            ).fetchone()

        if row is None:
            return None

        return ApprovalRequest(
            id=UUID(row[0]),
            action=ProposedAction(
                service=row[1],
                action_type=ActionType(row[2]),
                rationale=row[3],
            ),
            status=ApprovalStatus(row[4]),
        )

    def save(self, approval_request: ApprovalRequest) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approval_requests (id, service, action_type, rationale, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET status = excluded.status
                """,
                (
                    str(approval_request.id),
                    approval_request.action.service,
                    approval_request.action.action_type.value,
                    approval_request.action.rationale,
                    approval_request.status.value,
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)
