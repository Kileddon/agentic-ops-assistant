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


def test_load_settings_uses_default_ollama_model(tmp_path: Path) -> None:
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

    assert settings.ollama_model == "qwen2.5:3b"


def test_load_settings_rejects_blank_ollama_model(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.touch()
    status_file = tmp_path / "service_statuses.json"
    status_file.touch()

    with pytest.raises(
        SettingsError,
        match="Environment variable OPS_OLLAMA_MODEL must not be blank",
    ):
        load_settings(
            {
                "OPS_KNOWLEDGE_FILE": str(knowledge_file),
                "OPS_SERVICE_STATUS_FILE": str(status_file),
                "OPS_OLLAMA_MODEL": "   ",
            },
        )


def test_load_settings_uses_prometheus_status_source(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.touch()

    settings = load_settings(
        {
            "OPS_KNOWLEDGE_FILE": str(knowledge_file),
            "OPS_STATUS_SOURCE": "prometheus",
            "OPS_PROMETHEUS_URL": "http://prometheus.example",
        },
    )

    assert settings.status_source == "prometheus"
    assert settings.service_status_file is None
    assert settings.prometheus_url == "http://prometheus.example"


def test_load_settings_rejects_prometheus_source_without_url(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.touch()

    with pytest.raises(
        SettingsError,
        match="Missing required environment variable: OPS_PROMETHEUS_URL",
    ):
        load_settings(
            {
                "OPS_KNOWLEDGE_FILE": str(knowledge_file),
                "OPS_STATUS_SOURCE": "prometheus",
            },
        )


def test_load_settings_rejects_unknown_status_source(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.touch()

    with pytest.raises(
        SettingsError,
        match="OPS_STATUS_SOURCE must be 'json' or 'prometheus'",
    ):
        load_settings(
            {
                "OPS_KNOWLEDGE_FILE": str(knowledge_file),
                "OPS_STATUS_SOURCE": "unknown",
            },
        )
