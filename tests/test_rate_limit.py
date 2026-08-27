import pytest

from agentic_ops_assistant.auth.models import ApiRole
from agentic_ops_assistant.rate_limit import FixedWindowRateLimiter, RedisFixedWindowRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_rate_limiter_limits_each_role_and_endpoint_independently() -> None:
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=10.0)

    assert limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigations") is None
    assert limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigations") == 10
    assert limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigation-summaries") is None
    assert limiter.acquire(role=ApiRole.AUDITOR, endpoint="investigations") is None


def test_rate_limiter_allows_requests_after_the_window_expires() -> None:
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=10.0, clock=clock)

    assert limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigations") is None
    clock.advance(3.2)
    assert limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigations") == 7
    clock.advance(6.8)
    assert limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigations") is None


@pytest.mark.parametrize(
    ("max_requests", "window_seconds", "message"),
    [
        (0, 1.0, "Maximum requests must be positive"),
        (1, 0.0, "Rate-limit window must be positive"),
    ],
)
def test_rate_limiter_rejects_invalid_configuration(
    max_requests: int,
    window_seconds: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        FixedWindowRateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds,
        )


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.scripts: list[tuple[str, int, tuple[str, ...]]] = []

    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> list[int]:
        self.scripts.append((script, numkeys, keys_and_args))
        key, window_seconds = keys_and_args
        self.values[key] = self.values.get(key, 0) + 1
        self.expirations.setdefault(key, int(window_seconds))
        return [self.values[key], self.expirations[key]]


def test_redis_rate_limiter_shares_counter_by_role_and_endpoint() -> None:
    redis_client = FakeRedis()
    first_limiter = RedisFixedWindowRateLimiter(redis_client, max_requests=1, window_seconds=15)
    second_limiter = RedisFixedWindowRateLimiter(redis_client, max_requests=1, window_seconds=15)

    assert first_limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigations") is None
    assert second_limiter.acquire(role=ApiRole.OPERATOR, endpoint="investigations") == 15
    assert len(redis_client.scripts) == 2
    assert all(script[1] == 1 for script in redis_client.scripts)
