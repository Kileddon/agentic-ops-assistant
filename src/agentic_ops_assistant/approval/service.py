from dataclasses import replace
from uuid import UUID, uuid4

from agentic_ops_assistant.actions.models import PolicyDecision, PolicyStatus, ProposedAction
from agentic_ops_assistant.approval.models import ApprovalRequest, ApprovalStatus


def create_approval_request(
    action: ProposedAction,
    policy_decision: PolicyDecision,
    approval_id: UUID | None = None,
) -> ApprovalRequest:
    if policy_decision.status is not PolicyStatus.REQUIRES_APPROVAL:
        raise ValueError("Only approval-required actions can create approval requests.")

    return ApprovalRequest(
        id=uuid4() if approval_id is None else approval_id,
        action=action,
        status=ApprovalStatus.PENDING,
    )


def decide_approval(
    approval_request: ApprovalRequest,
    approved: bool,
) -> ApprovalRequest:
    if approval_request.status is not ApprovalStatus.PENDING:
        raise ValueError("Only pending approval requests can be decided.")

    status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED

    return replace(approval_request, status=status)
