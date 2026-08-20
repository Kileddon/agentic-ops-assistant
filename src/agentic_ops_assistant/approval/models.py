from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from agentic_ops_assistant.actions.models import ProposedAction


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    id: UUID
    action: ProposedAction
    status: ApprovalStatus
