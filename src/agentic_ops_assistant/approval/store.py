from typing import Protocol
from uuid import UUID

from agentic_ops_assistant.approval.models import ApprovalRequest


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
