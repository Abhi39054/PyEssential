# Decorators

Ready-to-use decorators for everyday tasks.

```python
from pyessential.decorators import timeit, retry
```

## Overview

| Decorator | Purpose |
|---|---|
| [`@timeit`](#timeit) | Measure and report how long a function takes. |
| [`@retry`](#retry) | Re-run a function that raises, waiting longer between attempts. |
| [`@deprecated`](#deprecated) | Mark a function as deprecated. |

---

## `timeit`

Measures how long a function takes to run and reports it. Use it without parentheses.
It also works on `async` functions.

```python
from pyessential.decorators import timeit

@timeit
def slow_function():
    sum(range(1_000_000))

slow_function()
# [slow_function] executed in 0.0123 seconds.
```

The report starts with the function's name in square brackets, followed by the elapsed time.

<!-- TODO: confirm whether the report goes to print() or logging, whether the wrapped
     function's return value and metadata are preserved, and add an async example. -->

---

## `retry`

Retries a function when it raises, waiting longer between each attempt. After the last attempt,
the original exception is re-raised.

```python
from pyessential.decorators import retry

@retry(tries=4, delay=0.5, backoff=2, exceptions=(ConnectionError, TimeoutError))
def fetch_data():
    ...
```

This makes up to four attempts and waits 0.5 s, 1 s, then 2 s between them. Only the listed
exceptions trigger a retry. Any other exception is raised immediately.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `tries` | `3` | Total attempts, including the first one. |
| `delay` | `1.0` | Seconds to wait after the first failure. |
| `backoff` | `2.0` | Multiplier applied to the wait after each failure. Use `1` for a constant delay. |
| `max_delay` | | Upper limit for any single wait, in seconds. |
| `jitter` | | Up to this many extra random seconds are added to each wait. |
| `exceptions` | `Exception` | Exception class, or tuple of classes, that trigger a retry. |
| `on_retry` | | Callback `on_retry(exc, attempt, wait)`, e.g. for logging. |

<!-- TODO: add the defaults of max_delay, jitter and on_retry, and say whether retry works on
     async functions. -->

### Logging retries

```python
from pyessential.decorators import retry

def log_retry(exc, attempt, wait):
    print(f"Attempt {attempt} failed ({exc!r}); retrying in {wait:.1f}s")

@retry(tries=3, delay=1, exceptions=ConnectionError, on_retry=log_retry)
def fetch_data():
    ...
```

### Handling the final failure

When every attempt fails, the last exception is raised to the caller, so you can handle it as
usual:

```python
try:
    fetch_data()
except ConnectionError:
    ...  # all attempts failed
```

---

## `deprecated`

<!-- TODO: document @deprecated: how to apply it  -->