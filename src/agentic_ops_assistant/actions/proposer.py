from agentic_ops_assistant.actions.models import ActionType, ProposedAction
from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus


def propose_action(service_status: ServiceStatus | None) -> ProposedAction | None:
    if service_status is None or service_status.health is ServiceHealth.HEALTHY:
        return None

    if service_status.health is ServiceHealth.DEGRADED:
        return ProposedAction(
            service=service_status.service,
            action_type=ActionType.COLLECT_DIAGNOSTICS,
            rationale=f"Service status is degraded: {service_status.summary}",
        )

    return ProposedAction(
        service=service_status.service,
        action_type=ActionType.RESTART_SERVICE,
        rationale=f"Service outage reported: {service_status.summary}",
    )
