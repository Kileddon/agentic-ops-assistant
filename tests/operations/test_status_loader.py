from pathlib import Path

import pytest

from agentic_ops_assistant.operations.status import ServiceHealth, ServiceStatus
from agentic_ops_assistant.operations.status_loader import (
    ServiceStatusLoadError,
    load_service_statuses,
)


def test_load_service_statuses_reads_valid_json_file(tmp_path: Path) -> None:
    status_file = tmp_path / "service_statuses.json"
    status_file.write_text(
        """
        [
          {
            "service": "payments-api",
            "status": "degraded",
            "summary": "Elevated database timeout rate."
          }
        ]
        """,
        encoding="utf-8",
    )

    statuses = load_service_statuses(status_file)

    assert statuses == (
        ServiceStatus(
            service="payments-api",
            health=ServiceHealth.DEGRADED,
            summary="Elevated database timeout rate.",
        ),
    )


def test_load_service_statuses_rejects_unknown_health_value(tmp_path: Path) -> None:
    status_file = tmp_path / "service_statuses.json"
    status_file.write_text(
        """
        [
          {
            "service": "payments-api",
            "status": "unstable",
            "summary": "Elevated database timeout rate."
          }
        ]
        """,
        encoding="utf-8",
    )

    with pytest.raises(ServiceStatusLoadError, match="Unsupported service health"):
        load_service_statuses(status_file)
