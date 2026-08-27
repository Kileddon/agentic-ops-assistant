import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from agentic_ops_assistant.diagnostics.logs import redact_log_line


class DiagnosticsError(RuntimeError):
    """Raised when read-only Docker diagnostics cannot be collected."""


@dataclass(frozen=True, slots=True)
class ContainerDiagnostics:
    container: str
    status: str
    resource_usage: str
    recent_logs: tuple[str, ...]

    def telegram_summary(self) -> str:
        return (
            f"Diagnostics collected for {self.container}\n"
            f"Status: {self.status}\n"
            f"Usage: {self.resource_usage}\n"
            f"Log lines collected: {len(self.recent_logs)}"
        )


class DiagnosticsCollector(Protocol):
    def collect(self, container: str) -> ContainerDiagnostics: ...


class DockerDiagnosticsCollector:
    def __init__(
        self,
        *,
        allowed_container: str,
        log_line_limit: int = 100,
        runner: Callable[[tuple[str, ...]], str] | None = None,
    ) -> None:
        if not allowed_container.strip():
            raise ValueError("Allowed diagnostic container must not be blank.")
        if log_line_limit <= 0 or log_line_limit > 100:
            raise ValueError("Diagnostic log line limit must be between 1 and 100.")

        self._allowed_container = allowed_container
        self._log_line_limit = log_line_limit
        self._runner = self._run if runner is None else runner

    def collect(self, container: str) -> ContainerDiagnostics:
        if container != self._allowed_container:
            raise DiagnosticsError("Container is not in the diagnostic allowlist.")

        status = self._runner(("inspect", "--format={{.State.Status}}", container))
        resource_usage = self._runner(
            ("stats", "--no-stream", "--format={{.CPUPerc}} {{.MemUsage}}", container)
        )
        logs = self._runner(("logs", "--tail", str(self._log_line_limit), container))

        return ContainerDiagnostics(
            container=container,
            status=status,
            resource_usage=resource_usage,
            recent_logs=tuple(redact_log_line(line) for line in logs.splitlines() if line),
        )

    def _run(self, arguments: tuple[str, ...]) -> str:
        try:
            result = subprocess.run(
                ("docker", *arguments),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise DiagnosticsError("Docker diagnostics could not be collected.") from error

        return result.stdout.strip()
