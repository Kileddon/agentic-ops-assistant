import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

StatusSource = Literal["json", "prometheus"]


class SettingsError(ValueError):
    """Raised when required application settings are missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    knowledge_file: Path
    service_status_file: Path | None
    ollama_model: str
    status_source: StatusSource
    prometheus_url: str | None
    audit_log_file: Path
    operator_api_key: str | None
    approver_api_key: str | None
    auditor_api_key: str | None
    operator_next_api_key: str | None
    approver_next_api_key: str | None
    auditor_next_api_key: str | None


def load_settings(
    environment: Mapping[str, str] | None = None,
) -> Settings:
    source = os.environ if environment is None else environment
    status_source = _status_source(source)

    return Settings(
        knowledge_file=_required_file_path(source, "OPS_KNOWLEDGE_FILE"),
        ollama_model=_optional_text(
            source,
            "OPS_OLLAMA_MODEL",
            default="qwen2.5:3b",
        ),
        status_source=status_source,
        service_status_file=(
            _required_file_path(source, "OPS_SERVICE_STATUS_FILE")
            if status_source == "json"
            else None
        ),
        prometheus_url=(
            _required_text(source, "OPS_PROMETHEUS_URL") if status_source == "prometheus" else None
        ),
        audit_log_file=_optional_path(
            source,
            "OPS_AUDIT_LOG_FILE",
            default=Path("var/audit-events.jsonl"),
        ),
        operator_api_key=_optional_secret(source, "OPS_OPERATOR_API_KEY"),
        approver_api_key=_optional_secret(source, "OPS_APPROVER_API_KEY"),
        auditor_api_key=_optional_secret(source, "OPS_AUDITOR_API_KEY"),
        operator_next_api_key=_optional_secret(source, "OPS_OPERATOR_NEXT_API_KEY"),
        approver_next_api_key=_optional_secret(source, "OPS_APPROVER_NEXT_API_KEY"),
        auditor_next_api_key=_optional_secret(source, "OPS_AUDITOR_NEXT_API_KEY"),
    )


def _required_file_path(
    environment: Mapping[str, str],
    variable_name: str,
) -> Path:
    raw_value = environment.get(variable_name)

    if raw_value is None or not raw_value.strip():
        raise SettingsError(f"Missing required environment variable: {variable_name}")

    path = Path(raw_value)

    if not path.is_file():
        raise SettingsError(
            f"Environment variable {variable_name} must reference a file: {path}",
        )

    return path


def _optional_text(
    environment: Mapping[str, str],
    variable_name: str,
    *,
    default: str,
) -> str:
    raw_value = environment.get(variable_name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip()

    if not normalized_value:
        raise SettingsError(f"Environment variable {variable_name} must not be blank")

    return normalized_value


def _required_text(
    environment: Mapping[str, str],
    variable_name: str,
) -> str:
    raw_value = environment.get(variable_name)

    if raw_value is None or not raw_value.strip():
        raise SettingsError(f"Missing required environment variable: {variable_name}")

    return raw_value.strip()


def _status_source(environment: Mapping[str, str]) -> StatusSource:
    raw_value = environment.get("OPS_STATUS_SOURCE", "json")
    normalized_value = raw_value.strip().casefold()

    if normalized_value == "json":
        return "json"

    if normalized_value == "prometheus":
        return "prometheus"

    raise SettingsError(
        "Environment variable OPS_STATUS_SOURCE must be 'json' or 'prometheus'",
    )


def _optional_path(
    environment: Mapping[str, str],
    variable_name: str,
    *,
    default: Path,
) -> Path:
    raw_value = environment.get(variable_name)

    if raw_value is None:
        return default

    if not raw_value.strip():
        raise SettingsError(f"Environment variable {variable_name} must not be blank")

    return Path(raw_value)


def _optional_secret(
    environment: Mapping[str, str],
    variable_name: str,
) -> str | None:
    raw_value = environment.get(variable_name)

    if raw_value is None:
        return None

    if not raw_value.strip():
        raise SettingsError(f"Environment variable {variable_name} must not be blank")

    return raw_value
