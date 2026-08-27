import pytest

from agentic_ops_assistant.diagnostics.docker import DiagnosticsError, DockerDiagnosticsCollector


def test_collector_rejects_a_container_outside_the_allowlist() -> None:
    collector = DockerDiagnosticsCollector(allowed_container="demo-api")

    with pytest.raises(DiagnosticsError, match="allowlist"):
        collector.collect("database")


def test_collector_rejects_more_than_one_hundred_log_lines() -> None:
    with pytest.raises(ValueError, match="between 1 and 100"):
        DockerDiagnosticsCollector(allowed_container="demo-api", log_line_limit=101)


def test_collector_uses_only_read_only_docker_commands() -> None:
    commands: list[tuple[str, ...]] = []

    def runner(arguments: tuple[str, ...]) -> str:
        commands.append(arguments)
        return {
            "inspect": "running",
            "stats": "0.50% 12MiB / 128MiB",
            "logs": "token=secret-value\nsecond line\n",
        }[arguments[0]]

    diagnostics = DockerDiagnosticsCollector(
        allowed_container="demo-api",
        runner=runner,
    ).collect("demo-api")

    assert diagnostics.status == "running"
    assert diagnostics.resource_usage == "0.50% 12MiB / 128MiB"
    assert diagnostics.recent_logs == ("token=[REDACTED]", "second line")
    assert commands == [
        ("inspect", "--format={{.State.Status}}", "demo-api"),
        ("stats", "--no-stream", "--format={{.CPUPerc}} {{.MemUsage}}", "demo-api"),
        ("logs", "--tail", "100", "demo-api"),
    ]
