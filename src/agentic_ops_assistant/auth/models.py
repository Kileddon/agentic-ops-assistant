from dataclasses import dataclass
from enum import StrEnum


class ApiRole(StrEnum):
    OPERATOR = "operator"
    APPROVER = "approver"
    AUDITOR = "auditor"


@dataclass(frozen=True, slots=True)
class Principal:
    role: ApiRole
