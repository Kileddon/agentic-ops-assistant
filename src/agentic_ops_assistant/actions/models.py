from dataclasses import dataclass
from enum import StrEnum


class ActionType(StrEnum):
    COLLECT_DIAGNOSTICS = "collect_diagnostics"
    RESTART_SERVICE = "restart_service"


class PolicyStatus(StrEnum):
    ALLOWED = "allowed"
    REQUIRES_APPROVAL = "requires_approval"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class ProposedAction:
    service: str
    action_type: ActionType
    rationale: str


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    status: PolicyStatus
    reason: str
