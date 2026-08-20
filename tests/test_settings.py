from pathlib import Path

import pytest

from agentic_ops_assistant.settings import SettingsError, load_settings


def test_load_settings_reads_required_file_paths(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.touch()
    status_file = tmp_path / "service_statuses.json"
    status_file.touch()

    settings = load_settings(
        {
            "OPS_KNOWLEDGE_FILE": str(knowledge_file),
            "OPS_SERVICE_STATUS_FILE": str(status_file),
        },
    )

    assert settings.knowledge_file == knowledge_file
    assert settings.service_status_file == status_file


def test_load_settings_rejects_missing_variable(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.touch()

    with pytest.raises(
        SettingsError,
        match="Missing required environment variable: OPS_SERVICE_STATUS_FILE",
    ):
        load_settings(
            {
                "OPS_KNOWLEDGE_FILE": str(knowledge_file),
            },
        )


def test_load_settings_rejects_nonexistent_file() -> None:
    with pytest.raises(
        SettingsError,
        match="OPS_KNOWLEDGE_FILE must reference a file",
    ):
        load_settings(
            {
                "OPS_KNOWLEDGE_FILE": "missing.json",
                "OPS_SERVICE_STATUS_FILE": "also-missing.json",
            },
        )
