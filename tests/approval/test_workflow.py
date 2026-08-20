from uuid import UUID

import pytest

from agentic_ops_assistant.actions.models import (
    ActionType,
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)
from agentic_ops_assistant.approval.models import ApprovalStatus
from agentic_ops_assistant.approval.store import InMemoryApprovalStore
from agentic_ops_assistant.approval.workflow import (
    ApprovalNotFoundError,
    ApprovalService,
)


def approval_required_action() -> tuple[ProposedAction, PolicyDecision]:
    action = ProposedAction(
        service="payments-api",
        action_type=ActionType.RESTART_SERVICE,
        rationale="Service outage reported.",
    )
    decision = PolicyDecision(
        status=PolicyStatus.REQUIRES_APPROVAL,
        reason="Service restart requires human approval.",
    )

    return action, decision


def test_service_creates_and_decides_approval_request() -> None:
    action, decision = approval_required_action()
    service = ApprovalService(InMemoryApprovalStore())

    request = service.create(action, decision)
    approved_request = service.decide(request.id, approved=True)

    assert request.status is ApprovalStatus.PENDING
    assert approved_request.status is ApprovalStatus.APPROVED


def test_service_rejects_unknown_approval_request() -> None:
    service = ApprovalService(InMemoryApprovalStore())

    with pytest.raises(ApprovalNotFoundError, match="Approval request not found"):
        service.decide(
            UUID("00000000-0000-0000-0000-000000000001"),
            approved=True,
        )
