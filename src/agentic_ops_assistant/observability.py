from collections import Counter
from dataclasses import dataclass
from threading import Lock
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ApiMetrics:
    request_count: int
    status_counts: dict[str, int]
    total_duration_ms: float


class RedisMetricsStore(Protocol):
    def incr(self, key: str) -> int: ...
    def hincrby(self, key: str, field: str, amount: int) -> int: ...
    def incrbyfloat(self, key: str, amount: float) -> float: ...
    def get(self, key: str) -> str | None: ...
    def hgetall(self, key: str) -> dict[str, str]: ...


class InMemoryApiMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._request_count = 0
        self._status_counts: Counter[str] = Counter()
        self._total_duration_ms = 0.0

    def record(self, *, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self._request_count += 1
            self._status_counts[str(status_code)] += 1
            self._total_duration_ms += duration_ms

    def snapshot(self) -> ApiMetrics:
        with self._lock:
            return ApiMetrics(
                request_count=self._request_count,
                status_counts=dict(self._status_counts),
                total_duration_ms=round(self._total_duration_ms, 3),
            )


class RedisApiMetrics:
    def __init__(self, client: RedisMetricsStore) -> None:
        self._client = client

    def record(self, *, status_code: int, duration_ms: float) -> None:
        self._client.incr("agentic_ops:metrics:requests")
        self._client.hincrby("agentic_ops:metrics:statuses", str(status_code), 1)
        self._client.incrbyfloat("agentic_ops:metrics:duration_ms", duration_ms)

    def snapshot(self) -> ApiMetrics:
        return ApiMetrics(
            request_count=int(self._client.get("agentic_ops:metrics:requests") or 0),
            status_counts={
                status: int(count)
                for status, count in self._client.hgetall("agentic_ops:metrics:statuses").items()
            },
            total_duration_ms=float(self._client.get("agentic_ops:metrics:duration_ms") or 0),
        )


def render_prometheus_metrics(metrics: ApiMetrics) -> str:
    lines = [
        "# TYPE agentic_ops_http_requests_total counter",
        f"agentic_ops_http_requests_total {metrics.request_count}",
        "# TYPE agentic_ops_http_response_status_total counter",
    ]
    lines.extend(
        f'agentic_ops_http_response_status_total{{status="{status}"}} {count}'
        for status, count in sorted(metrics.status_counts.items())
    )
    lines.extend(
        [
            "# TYPE agentic_ops_http_request_duration_milliseconds_total counter",
            f"agentic_ops_http_request_duration_milliseconds_total {metrics.total_duration_ms}",
            "",
        ],
    )
    return "\n".join(lines)
