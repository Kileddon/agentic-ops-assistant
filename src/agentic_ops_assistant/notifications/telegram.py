from typing import Protocol

import httpx2


class TelegramNotificationError(RuntimeError):
    pass


class NotificationSender(Protocol):
    def send(self, text: str) -> None: ...


class TelegramNotifier:
    def __init__(
        self, *, bot_token: str, chat_id: str, client: httpx2.Client | None = None
    ) -> None:
        if not bot_token.strip() or not chat_id.strip():
            raise ValueError("Telegram bot token and chat ID must not be blank.")

        self._bot_token = bot_token
        self._chat_id = chat_id
        self._client = httpx2.Client() if client is None else client

    def send(self, text: str) -> None:
        try:
            response = self._client.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                json={"chat_id": self._chat_id, "text": text},
            )
            response.raise_for_status()
            if response.json().get("ok") is not True:
                raise TelegramNotificationError("Telegram rejected the notification.")
        except httpx2.HTTPError as error:
            raise TelegramNotificationError("Telegram notification could not be sent.") from error
