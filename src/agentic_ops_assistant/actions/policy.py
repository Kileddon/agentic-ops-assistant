from agentic_ops_assistant.actions.models import (
    ActionType,
    PolicyDecision,
    PolicyStatus,
    ProposedAction,
)


def evaluate_action(action: ProposedAction) -> PolicyDecision:
    if not action.service.strip():
        return PolicyDecision(
            status=PolicyStatus.DENIED,
            reason="Service name must not be blank.",
        )

    if action.action_type is ActionType.COLLECT_DIAGNOSTICS:
        return PolicyDecision(
            status=PolicyStatus.ALLOWED,
            reason="Read-only diagnostic collection is allowed.",
        )

    return PolicyDecision(
        status=PolicyStatus.REQUIRES_APPROVAL,
        reason="Service restart requires human approval.",
    )
