from uuid import UUID

import pytest

from agentic_ops_assistant.actions.models import (
    ActionType,
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)
from agentic_ops_assistant.approval.models import ApprovalStatus
from agentic_ops_assistant.approval.service import (
    create_approval_request,
    decide_approval,
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


def test_create_approval_request_for_dangerous_action() -> None:
    action, decision = approval_required_action()

    request = create_approval_request(
        action,
        decision,
        approval_id=UUID("00000000-0000-0000-0000-000000000001"),
    )

    assert request.status is ApprovalStatus.PENDING
    assert request.action == action


def test_decide_approval_returns_new_approved_request() -> None:
    action, decision = approval_required_action()
    request = create_approval_request(action, decision)

    approved_request = decide_approval(request, approved=True)

    assert request.status is ApprovalStatus.PENDING
    assert approved_request.status is ApprovalStatus.APPROVED


def test_deciding_non_pending_request_is_rejected() -> None:
    action, decision = approval_required_action()
    request = create_approval_request(action, decision)
    approved_request = decide_approval(request, approved=True)

    with pytest.raises(ValueError, match="Only pending approval requests"):
        decide_approval(approved_request, approved=False)
