import inspect
import time
from functools import wraps


def timeit(func):
    """Measure and print a function's execution time.

    Works with regular and ``async`` functions. The time is printed even if
    the function raises an exception.

    Example:
        >>> @timeit
        ... def work():
        ...     sum(range(1_000_000))
        >>> work()  # doctest: +SKIP
        [work] executed in 0.0123 seconds.
    """
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                print(f"[{func.__name__}] executed in {time.perf_counter() - start:.4f} seconds.")
        return async_wrapper

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            print(f"[{func.__name__}] executed in {time.perf_counter() - start:.4f} seconds.")
    return wrapper