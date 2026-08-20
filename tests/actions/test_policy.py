from agentic_ops_assistant.actions.models import (
    ActionType,
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)
from agentic_ops_assistant.actions.policy import evaluate_action


def test_diagnostics_action_is_allowed() -> None:
    action = ProposedAction(
        service="payments-api",
        action_type=ActionType.COLLECT_DIAGNOSTICS,
        rationale="Investigate elevated error rate.",
    )

    decision = evaluate_action(action)

    assert decision == PolicyDecision(
        status=PolicyStatus.ALLOWED,
        reason="Read-only diagnostic collection is allowed.",
    )


def test_restart_action_requires_human_approval() -> None:
    action = ProposedAction(
        service="payments-api",
        action_type=ActionType.RESTART_SERVICE,
        rationale="Recover from a persistent outage.",
    )

    decision = evaluate_action(action)

    assert decision == PolicyDecision(
        status=PolicyStatus.REQUIRES_APPROVAL,
        reason="Service restart requires human approval.",
    )


def test_blank_service_is_denied() -> None:
    action = ProposedAction(
        service="   ",
        action_type=ActionType.RESTART_SERVICE,
        rationale="Recover from a persistent outage.",
    )

    decision = evaluate_action(action)

    assert decision.status is PolicyStatus.DENIED
