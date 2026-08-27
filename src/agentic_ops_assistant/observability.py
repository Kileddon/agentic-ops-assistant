from collections import Counter
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class ApiMetrics:
    request_count: int
    status_counts: dict[str, int]
    total_duration_ms: float


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
