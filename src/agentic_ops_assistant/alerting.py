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
    return f"Prometheus alert: {alert_name}\nService: {service}\nSummary: {summary}"
