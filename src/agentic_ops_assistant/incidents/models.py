from dataclasses import dataclass
from enum import StrEnum


class IncidentKind(StrEnum):
    TARGET_DOWN = "target_down"
    HTTP_5XX = "http_5xx"
    HIGH_LATENCY = "high_latency"


class IncidentSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class IncidentSignal:
    service: str
    kind: IncidentKind
    severity: IncidentSeverity
    summary: str
    investigation_query: str
    evidence_query: str
    observed_value: float | None = None
