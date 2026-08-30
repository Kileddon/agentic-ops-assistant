from pathlib import Path

import pytest

from agentic_ops_assistant.incident_detection_cli import (
    _build_parser,
    _notifier_from_environment,
)
from agentic_ops_assistant.notifications.telegram import TelegramNotifier


def test_notification_mode_requires_local_telegram_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPS_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("OPS_TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(ValueError, match="OPS_TELEGRAM_BOT_TOKEN"):
        _notifier_from_environment(True)


def test_notification_mode_reads_telegram_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("OPS_TELEGRAM_CHAT_ID", "123")

    assert isinstance(_notifier_from_environment(True), TelegramNotifier)
    assert _notifier_from_environment(False) is None


def test_parser_converts_knowledge_file_to_path() -> None:
    arguments = _build_parser().parse_args(
        [
            "--knowledge-file",
            "examples/knowledge.json",
            "--prometheus-url",
            "http://127.0.0.1:9090",
            "agentic-ops-assistant",
        ]
    )

    assert arguments.knowledge_file == Path("examples/knowledge.json")
