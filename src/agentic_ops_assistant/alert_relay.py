from collections.abc import Mapping
from secrets import compare_digest
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException

from agentic_ops_assistant.alerting import (
    AlertDeduplicator,
    PrometheusAlertWebhook,
    format_prometheus_alert,
)
from agentic_ops_assistant.notifications.telegram import (
    NotificationSender,
    TelegramNotificationError,
    TelegramNotifier,
)
from agentic_ops_assistant.settings import load_alert_relay_settings


def create_alert_relay(
    *,
    webhook_token: str,
    notifier: NotificationSender,
    deduplicator: AlertDeduplicator | None = None,
) -> FastAPI:
    app = FastAPI(title="Agentic Ops Alert Relay", version="0.1.0")
    alert_deduplicator = AlertDeduplicator() if deduplicator is None else deduplicator

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/alerts/prometheus")
    def receive_prometheus_alert(
        webhook: PrometheusAlertWebhook,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        expected_header = f"Bearer {webhook_token}"
        if authorization is None or not compare_digest(authorization, expected_header):
            raise HTTPException(status_code=401, detail="Invalid Prometheus alert credentials.")

        notify_alerts = tuple(
            alert for alert in webhook.alerts if alert_deduplicator.should_notify(alert)
        )
        try:
            for alert in notify_alerts:
                notifier.send(format_prometheus_alert(alert))
        except TelegramNotificationError as error:
            raise HTTPException(
                status_code=502, detail="Telegram alert notification failed."
            ) from error

        return {"notified": len(notify_alerts)}

    return app


def create_alert_relay_from_environment(
    environment: Mapping[str, str] | None = None,
) -> FastAPI:
    settings = load_alert_relay_settings(environment)
    return create_alert_relay(
        webhook_token=settings.webhook_token,
        notifier=TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        ),
    )
