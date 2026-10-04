import asyncio
import time

import pytest

from pyessential.decorators import retry


class Flaky:
    """Callable helper that fails a set number of times, then succeeds."""

    def __init__(self, failures, exc=ValueError):
        self.failures = failures
        self.exc = exc
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc(f"fail {self.calls}")
        return "ok"


@pytest.fixture
def sleeps(monkeypatch):
    """Record sleep durations instead of really sleeping."""
    recorded = []
    monkeypatch.setattr(time, "sleep", recorded.append)
    return recorded


@pytest.fixture
def async_sleeps(monkeypatch):
    recorded = []

    async def fake_sleep(seconds):
        recorded.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


def test_returns_value_without_retrying(sleeps):
    flaky = Flaky(failures=0)
    assert retry(tries=3)(flaky)() == "ok"
    assert flaky.calls == 1
    assert sleeps == []


def test_retries_then_succeeds_with_backoff(sleeps):
    flaky = Flaky(failures=2)
    assert retry(tries=3, delay=1, backoff=2)(flaky)() == "ok"
    assert flaky.calls == 3
    assert sleeps == [1, 2]


def test_raises_last_exception_when_tries_exhausted(sleeps):
    flaky = Flaky(failures=10)
    with pytest.raises(ValueError, match="fail 3"):
        retry(tries=3, delay=0.1)(flaky)()
    assert flaky.calls == 3
    assert len(sleeps) == 2  # no sleep after the final attempt


def test_tries_one_means_no_retry(sleeps):
    flaky = Flaky(failures=1)
    with pytest.raises(ValueError):
        retry(tries=1)(flaky)()
    assert flaky.calls == 1
    assert sleeps == []


def test_other_exceptions_are_not_retried(sleeps):
    flaky = Flaky(failures=5, exc=KeyError)
    with pytest.raises(KeyError):
        retry(tries=3, exceptions=ValueError)(flaky)()
    assert flaky.calls == 1
    assert sleeps == []


def test_accepts_tuple_of_exceptions(sleeps):
    flaky = Flaky(failures=1, exc=ConnectionError)
    assert retry(tries=2, exceptions=(ConnectionError, TimeoutError))(flaky)() == "ok"


def test_max_delay_caps_wait(sleeps):
    flaky = Flaky(failures=3)
    retry(tries=4, delay=1, backoff=10, max_delay=2)(flaky)()
    assert sleeps == [1, 2, 2]


def test_constant_delay_with_backoff_one(sleeps):
    flaky = Flaky(failures=3)
    retry(tries=4, delay=0.5, backoff=1)(flaky)()
    assert sleeps == [0.5, 0.5, 0.5]


def test_jitter_adds_bounded_random_time(sleeps):
    flaky = Flaky(failures=2)
    retry(tries=3, delay=1, backoff=1, jitter=0.5)(flaky)()
    assert len(sleeps) == 2
    assert all(1 <= wait <= 1.5 for wait in sleeps)


def test_on_retry_callback(sleeps):
    calls = []
    flaky = Flaky(failures=2)
    retry(tries=3, delay=1, backoff=2, on_retry=lambda e, n, w: calls.append((str(e), n, w)))(flaky)()
    assert calls == [("fail 1", 1, 1), ("fail 2", 2, 2)]


def test_bare_decorator_uses_defaults(sleeps):
    flaky = Flaky(failures=2)

    @retry
    def work():
        return flaky()

    assert work() == "ok"
    assert sleeps == [1.0, 2.0]


def test_passes_arguments_and_preserves_metadata(sleeps):
    @retry(tries=2)
    def add(a, b=0):
        """Add numbers."""
        return a + b

    assert add(2, b=3) == 5
    assert add.__name__ == "add"
    assert add.__doc__ == "Add numbers."


def test_invalid_arguments_raise_value_error():
    with pytest.raises(ValueError):
        retry(tries=0)
    with pytest.raises(ValueError):
        retry(tries=2.5)
    with pytest.raises(ValueError):
        retry(delay=-1)
    with pytest.raises(ValueError):
        retry(backoff=0.5)
    with pytest.raises(ValueError):
        retry(max_delay=-1)
    with pytest.raises(ValueError):
        retry(jitter=-0.1)


def test_invalid_exceptions_raise_type_error():
    with pytest.raises(TypeError):
        retry(exceptions="ValueError")
    with pytest.raises(TypeError):
        retry(exceptions=(ValueError, "oops"))


def test_async_retries_then_succeeds(async_sleeps):
    state = {"calls": 0}

    @retry(tries=3, delay=1, backoff=2)
    async def work():
        state["calls"] += 1
        if state["calls"] < 3:
            raise ValueError("not yet")
        return "done"

    assert asyncio.run(work()) == "done"
    assert state["calls"] == 3
    assert async_sleeps == [1, 2]


def test_async_raises_when_tries_exhausted(async_sleeps):
    @retry(tries=2, delay=0.1)
    async def work():
        raise RuntimeError("always")

    with pytest.raises(RuntimeError, match="always"):
        asyncio.run(work())
    assert len(async_sleeps) == 1