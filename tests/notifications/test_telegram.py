import json

import httpx2
import pytest

from agentic_ops_assistant.notifications.telegram import (
    TelegramNotificationError,
    TelegramNotifier,
)


def test_notifier_sends_only_the_supplied_summary() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={"ok": True})

    client = httpx2.Client(transport=httpx2.MockTransport(handler))

    TelegramNotifier(bot_token="token", chat_id="123", client=client).send("safe summary")

    assert len(requests) == 1
    assert str(requests[0].url) == "https://api.telegram.org/bottoken/sendMessage"
    assert json.loads(requests[0].content) == {"chat_id": "123", "text": "safe summary"}


def test_notifier_rejects_a_failed_telegram_response() -> None:
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json={"ok": False})),
    )
    notifier = TelegramNotifier(bot_token="token", chat_id="123", client=client)

    with pytest.raises(TelegramNotificationError, match="rejected"):
        notifier.send("safe summary")


def test_notifier_rejects_blank_configuration() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        TelegramNotifier(bot_token="", chat_id="123")
