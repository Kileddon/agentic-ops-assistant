from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID


class AuditEventType(StrEnum):
    INVESTIGATION_CREATED = "investigation_created"
    APPROVAL_CREATED = "approval_created"
    APPROVAL_DECIDED = "approval_decided"
    STATUS_PROVIDER_FAILED = "status_provider_failed"
    DIAGNOSTICS_COLLECTED = "diagnostics_collected"
    INCIDENT_DETECTED = "incident_detected"
    INCIDENT_NOTIFICATION_SENT = "incident_notification_sent"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: UUID
    occurred_at: datetime
    event_type: AuditEventType
    service: str
    details: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))
