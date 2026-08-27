import math
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from agentic_ops_assistant.auth.models import ApiRole


@dataclass(frozen=True, slots=True)
class _Window:
    started_at: float
    request_count: int


class FixedWindowRateLimiter:
    """Limits authenticated requests per role and endpoint in one process."""

    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_requests <= 0:
            raise ValueError("Maximum requests must be positive.")

        if window_seconds <= 0:
            raise ValueError("Rate-limit window must be positive.")

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._lock = Lock()
        self._windows: dict[tuple[ApiRole, str], _Window] = {}

    def acquire(self, *, role: ApiRole, endpoint: str) -> int | None:
        """Returns retry-after seconds when the request is rejected."""
        now = self._clock()
        key = (role, endpoint)

        with self._lock:
            window = self._windows.get(key)

            if window is None or now >= window.started_at + self._window_seconds:
                self._windows[key] = _Window(started_at=now, request_count=1)
                return None

            if window.request_count >= self._max_requests:
                remaining_seconds = window.started_at + self._window_seconds - now
                return max(1, math.ceil(remaining_seconds))

            self._windows[key] = _Window(
                started_at=window.started_at,
                request_count=window.request_count + 1,
            )
            return None
