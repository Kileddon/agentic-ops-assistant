from typing import Protocol

from agentic_ops_assistant.operations.status import ServiceStatus


class ServiceStatusProvider(Protocol):
    def get_status(self, service: str) -> ServiceStatus | None: ...
