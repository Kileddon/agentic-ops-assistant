import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class SettingsError(ValueError):
    """Raised when required application settings are missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    knowledge_file: Path
    service_status_file: Path


def load_settings(
    environment: Mapping[str, str] | None = None,
) -> Settings:
    source = os.environ if environment is None else environment

    return Settings(
        knowledge_file=_required_file_path(source, "OPS_KNOWLEDGE_FILE"),
        service_status_file=_required_file_path(
            source,
            "OPS_SERVICE_STATUS_FILE",
        ),
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
