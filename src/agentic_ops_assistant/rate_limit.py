import math
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Protocol, cast

from agentic_ops_assistant.auth.models import ApiRole


class RedisCounter(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> object: ...


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


class RedisFixedWindowRateLimiter:
    _ACQUIRE_SCRIPT = """
        local count = redis.call('INCR', KEYS[1])
        if count == 1 then
            redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return {count, redis.call('TTL', KEYS[1])}
    """

    def __init__(
        self,
        client: RedisCounter,
        *,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        if max_requests <= 0 or window_seconds <= 0:
            raise ValueError("Redis rate-limit configuration must be positive.")
        self._client = client
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    def acquire(self, *, role: ApiRole, endpoint: str) -> int | None:
        key = f"agentic_ops:rate_limit:{role.value}:{endpoint}"
        result = self._client.eval(
            self._ACQUIRE_SCRIPT,
            1,
            key,
            str(self._window_seconds),
        )
        if (
            not isinstance(result, list)
            or len(result) != 2
            or not isinstance(result[0], int)
            or not isinstance(result[1], int)
        ):
            raise RuntimeError("Redis rate limiter returned an invalid result.")

        values = cast(list[object], result)
        count = values[0]
        ttl = values[1]
        if not isinstance(count, int) or not isinstance(ttl, int):
            raise RuntimeError("Redis rate limiter returned an invalid result.")
        if count <= self._max_requests:
            return None
        return max(1, ttl)
