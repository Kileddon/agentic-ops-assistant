import hashlib
import json
from threading import Lock
from typing import Literal

from pydantic import BaseModel, Field


class PrometheusAlert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)


class PrometheusAlertWebhook(BaseModel):
    alerts: list[PrometheusAlert]


def format_prometheus_alert(alert: PrometheusAlert) -> str:
    alert_name = alert.labels.get("alertname", "Prometheus alert")
    service = alert.labels.get("service") or alert.labels.get("job", "unknown service")
    summary = alert.annotations.get("summary", "No summary provided.")
    return (
        f"Prometheus alert: {alert_name}\n"
        f"Status: {alert.status}\n"
        f"Service: {service}\n"
        f"Summary: {summary}"
    )


class AlertDeduplicator:
    def __init__(self) -> None:
        self._active_fingerprints: set[str] = set()
        self._lock = Lock()

    def should_notify(self, alert: PrometheusAlert) -> bool:
        fingerprint = _fingerprint(alert)
        with self._lock:
            if alert.status == "firing":
                if fingerprint in self._active_fingerprints:
                    return False
                self._active_fingerprints.add(fingerprint)
                return True
            if fingerprint not in self._active_fingerprints:
                return False
            self._active_fingerprints.remove(fingerprint)
            return True


def _fingerprint(alert: PrometheusAlert) -> str:
    return hashlib.sha256(
        json.dumps(alert.labels, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()
