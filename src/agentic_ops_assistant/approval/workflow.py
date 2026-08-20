from uuid import UUID

from agentic_ops_assistant.actions.models import PolicyDecision, ProposedAction
from agentic_ops_assistant.approval.models import ApprovalRequest
from agentic_ops_assistant.approval.service import (
    create_approval_request,
    decide_approval,
)
from agentic_ops_assistant.approval.store import ApprovalStore


class ApprovalNotFoundError(LookupError):
    """Raised when an approval request does not exist."""


class ApprovalService:
    def __init__(self, store: ApprovalStore) -> None:
        self._store = store

    def create(
        self,
        action: ProposedAction,
        policy_decision: PolicyDecision,
    ) -> ApprovalRequest:
        approval_request = create_approval_request(action, policy_decision)
        self._store.save(approval_request)

        return approval_request

    def decide(
        self,
        approval_id: UUID,
        approved: bool,
    ) -> ApprovalRequest:
        approval_request = self._store.get(approval_id)

        if approval_request is None:
            raise ApprovalNotFoundError(f"Approval request not found: {approval_id}")

        decided_request = decide_approval(approval_request, approved)
        self._store.save(decided_request)

        return decided_request
