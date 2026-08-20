from uuid import UUID

from agentic_ops_assistant.actions.models import ActionType, ProposedAction
from agentic_ops_assistant.approval.models import ApprovalRequest, ApprovalStatus
from agentic_ops_assistant.approval.store import InMemoryApprovalStore


def test_store_returns_saved_approval_request() -> None:
    approval_id = UUID("00000000-0000-0000-0000-000000000001")
    request = ApprovalRequest(
        id=approval_id,
        action=ProposedAction(
            service="payments-api",
            action_type=ActionType.RESTART_SERVICE,
            rationale="Service outage reported.",
        ),
        status=ApprovalStatus.PENDING,
    )
    store = InMemoryApprovalStore()

    store.save(request)

    assert store.get(approval_id) == request


def test_store_returns_none_for_unknown_approval_request() -> None:
    store = InMemoryApprovalStore()

    request = store.get(UUID("00000000-0000-0000-0000-000000000001"))

    assert request is None
