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
    approval_database_file: Path
    operator_api_key: str | None
    approver_api_key: str | None
    auditor_api_key: str | None
    operator_next_api_key: str | None
    approver_next_api_key: str | None
    auditor_next_api_key: str | None
    rate_limit_requests: int
    rate_limit_window_seconds: float
    keycloak_issuer: str | None
    keycloak_audience: str | None
    keycloak_jwks_url: str | None
    redis_url: str | None
    prometheus_scrape_token: str | None
    alert_webhook_token: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    diagnostic_container: str | None


@dataclass(frozen=True, slots=True)
class AlertRelaySettings:
    webhook_token: str
    telegram_bot_token: str
    telegram_chat_id: str


@dataclass(frozen=True, slots=True)
class AuditBackupSettings:
    archive_directory: Path
    backup_directory: Path


def load_settings(
    environment: Mapping[str, str] | None = None,
) -> Settings:
    source = os.environ if environment is None else environment
    status_source = _status_source(source)
    prometheus_url = _optional_secret(source, "OPS_PROMETHEUS_URL")

    if status_source == "prometheus" and prometheus_url is None:
        raise SettingsError("Missing required environment variable: OPS_PROMETHEUS_URL")

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
        prometheus_url=prometheus_url,
        audit_log_file=_optional_path(
            source,
            "OPS_AUDIT_LOG_FILE",
            default=Path("var/audit-events.jsonl"),
        ),
        approval_database_file=_optional_path(
            source,
            "OPS_APPROVAL_DATABASE_FILE",
            default=Path("var/approvals.sqlite3"),
        ),
        operator_api_key=_optional_secret(source, "OPS_OPERATOR_API_KEY"),
        approver_api_key=_optional_secret(source, "OPS_APPROVER_API_KEY"),
        auditor_api_key=_optional_secret(source, "OPS_AUDITOR_API_KEY"),
        operator_next_api_key=_optional_secret(source, "OPS_OPERATOR_NEXT_API_KEY"),
        approver_next_api_key=_optional_secret(source, "OPS_APPROVER_NEXT_API_KEY"),
        auditor_next_api_key=_optional_secret(source, "OPS_AUDITOR_NEXT_API_KEY"),
        rate_limit_requests=_optional_positive_int(
            source,
            "OPS_RATE_LIMIT_REQUESTS",
            default=60,
        ),
        rate_limit_window_seconds=_optional_positive_float(
            source,
            "OPS_RATE_LIMIT_WINDOW_SECONDS",
            default=60.0,
        ),
        keycloak_issuer=_optional_secret(source, "OPS_KEYCLOAK_ISSUER"),
        keycloak_audience=_optional_secret(source, "OPS_KEYCLOAK_AUDIENCE"),
        keycloak_jwks_url=_optional_secret(source, "OPS_KEYCLOAK_JWKS_URL"),
        redis_url=_optional_secret(source, "OPS_REDIS_URL"),
        prometheus_scrape_token=_optional_secret(source, "OPS_PROMETHEUS_SCRAPE_TOKEN"),
        alert_webhook_token=_optional_secret(source, "OPS_ALERT_WEBHOOK_TOKEN"),
        telegram_bot_token=_optional_secret(source, "OPS_TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_optional_secret(source, "OPS_TELEGRAM_CHAT_ID"),
        diagnostic_container=_optional_secret(source, "OPS_DIAGNOSTIC_CONTAINER"),
    )


def load_alert_relay_settings(
    environment: Mapping[str, str] | None = None,
) -> AlertRelaySettings:
    source = os.environ if environment is None else environment
    return AlertRelaySettings(
        webhook_token=_required_text(source, "OPS_ALERT_WEBHOOK_TOKEN"),
        telegram_bot_token=_required_text(source, "OPS_TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_required_text(source, "OPS_TELEGRAM_CHAT_ID"),
    )


def load_audit_backup_settings(
    environment: Mapping[str, str] | None = None,
) -> AuditBackupSettings:
    source = os.environ if environment is None else environment
    return AuditBackupSettings(
        archive_directory=_optional_path(
            source,
            "OPS_AUDIT_ARCHIVE_DIRECTORY",
            default=Path("var/audit-archive"),
        ),
        backup_directory=Path(_required_text(source, "OPS_AUDIT_BACKUP_DIRECTORY")),
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


def _optional_positive_int(
    environment: Mapping[str, str],
    variable_name: str,
    *,
    default: int,
) -> int:
    raw_value = environment.get(variable_name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as error:
        raise SettingsError(f"Environment variable {variable_name} must be an integer") from error

    if value <= 0:
        raise SettingsError(f"Environment variable {variable_name} must be positive")

    return value


def _optional_positive_float(
    environment: Mapping[str, str],
    variable_name: str,
    *,
    default: float,
) -> float:
    raw_value = environment.get(variable_name)

    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError as error:
        raise SettingsError(f"Environment variable {variable_name} must be a number") from error

    if value <= 0:
        raise SettingsError(f"Environment variable {variable_name} must be positive")

    return value
