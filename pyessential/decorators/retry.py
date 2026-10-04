import asyncio
import inspect
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union, cast

F = TypeVar("F", bound=Callable[..., Any])

ExceptionTypes = Union[Type[BaseException], Tuple[Type[BaseException], ...]]


def _wait_time(
    attempt: int,
    delay: float,
    backoff: float,
    max_delay: Optional[float],
    jitter: float,
) -> float:
    """Seconds to wait after the given (1-based) failed attempt."""
    wait = delay * (backoff ** (attempt - 1))
    if max_delay is not None:
        wait = min(wait, max_delay)
    if jitter:
        wait += random.uniform(0, jitter)
    return wait


def retry(
    tries: Any = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    *,
    max_delay: Optional[float] = None,
    jitter: float = 0.0,
    exceptions: ExceptionTypes = Exception,
    on_retry: Optional[Callable[[BaseException, int, float], None]] = None,
) -> Any:
    """Retry a function when it raises, waiting longer between each attempt.

    Works with regular and ``async`` functions. Can be used with or without
    parentheses (``@retry`` or ``@retry(tries=5)``).

    Args:
        tries: Total number of attempts, including the first one (default 3).
        delay: Seconds to wait after the first failure (default 1.0).
        backoff: Multiplier applied to the wait after each failure (default 2.0).
            Use 1 for a constant delay.
        max_delay: Upper limit in seconds for any single wait.
        jitter: Up to this many extra random seconds are added to each wait,
            which helps avoid many clients retrying at the same moment.
        exceptions: Exception class (or tuple of classes) that should trigger
            a retry. Any other exception is raised immediately.
        on_retry: Optional callback ``on_retry(exc, attempt, wait)`` called
            before each wait, e.g. for logging.

    Raises:
        ValueError: If an argument is out of range.
        TypeError: If ``exceptions`` is not an exception class or tuple of them.

    The original exception is re-raised once all attempts are used up.

    Example:
        >>> @retry(tries=4, delay=0.5, exceptions=(ConnectionError, TimeoutError))
        ... def fetch():
        ...     ...
    """
    # Support bare usage: @retry
    if callable(tries):
        return retry()(tries)

    if not isinstance(tries, int) or isinstance(tries, bool) or tries < 1:
        raise ValueError("tries must be an integer >= 1")
    if delay < 0:
        raise ValueError("delay must be >= 0")
    if backoff < 1:
        raise ValueError("backoff must be >= 1")
    if max_delay is not None and max_delay < 0:
        raise ValueError("max_delay must be >= 0")
    if jitter < 0:
        raise ValueError("jitter must be >= 0")

    exc_types = exceptions if isinstance(exceptions, tuple) else (exceptions,)
    if not exc_types or not all(
        isinstance(e, type) and issubclass(e, BaseException) for e in exc_types
    ):
        raise TypeError("exceptions must be an exception class or a tuple of them")

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                for attempt in range(1, tries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exc_types as exc:
                        if attempt == tries:
                            raise
                        wait = _wait_time(attempt, delay, backoff, max_delay, jitter)
                        if on_retry is not None:
                            on_retry(exc, attempt, wait)
                        await asyncio.sleep(wait)

            return cast(F, async_wrapper)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, tries + 1):
                try:
                    return func(*args, **kwargs)
                except exc_types as exc:
                    if attempt == tries:
                        raise
                    wait = _wait_time(attempt, delay, backoff, max_delay, jitter)
                    if on_retry is not None:
                        on_retry(exc, attempt, wait)
                    time.sleep(wait)

        return cast(F, wrapper)

    return decorator