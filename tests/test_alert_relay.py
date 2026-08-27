from fastapi.testclient import TestClient

from agentic_ops_assistant.alert_relay import create_alert_relay


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, text: str) -> None:
        self.messages.append(text)


def test_alert_relay_accepts_a_signed_firing_alert() -> None:
    notifier = FakeNotifier()
    client = TestClient(create_alert_relay(webhook_token="alert-token", notifier=notifier))

    response = client.post(
        "/alerts/prometheus",
        headers={"Authorization": "Bearer alert-token"},
        json={
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "ApiDown", "job": "agentic-ops-assistant"},
                    "annotations": {"summary": "The API is unavailable."},
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"notified": 1}
    assert notifier.messages == [
        "Prometheus alert: ApiDown\n"
        "Service: agentic-ops-assistant\n"
        "Summary: The API is unavailable.",
    ]


def test_alert_relay_rejects_a_missing_webhook_credential() -> None:
    client = TestClient(create_alert_relay(webhook_token="alert-token", notifier=FakeNotifier()))

    response = client.post("/alerts/prometheus", json={"alerts": []})

    assert response.status_code == 401
