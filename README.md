# 🐍 PyEssential

**A growing collection of Python utilities and decorators to simplify common development tasks.**

---

[![CI](https://github.com/Abhi39054/PyEssential/actions/workflows/pypi-publish.yaml/badge.svg)](https://github.com/Abhi39054/PyEssential/actions/workflows/pypi-publish.yaml)
[![PyPI version](https://img.shields.io/pypi/v/pyessential.svg)](https://pypi.org/project/pyessential/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyessential.svg)](https://pypi.org/project/pyessential/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Abhi39054/PyEssential/blob/main/LICENSE)

## ✨ Features

`PyEssential` aims to be the go-to library for small, reusable tools that you often find yourself writing from scratch. It has **no dependencies**.

* **Decorators:** `@timeit` for benchmarking, `@retry` with exponential backoff, and `@deprecated` for marking old code. `@timeit` and `@retry` also work with `async` functions.
* **Generators:** Secure random integers and secret keys.
* **Logging:** A `Logger` with separate log files for input, output and errors.
* **Command line:** Check your installed version with `pyessential --version`.
* **Typing:** Ships a `py.typed` marker so editors and type checkers can use its type hints.
* **Scalability:** Structured for easy addition of new utility groups (e.g., `networking`, `file_io`, `validation`).

## 🚀 Installation

**Requires Python 3.9+**

```bash
pip install pyessential
```

To upgrade to the latest release:

```bash
pip install --upgrade pyessential
```

## 📖 Usage

### `@timeit`

Prints how long a function took, even if it raises. Works with `async def` functions too.

```python
from pyessential.decorators import timeit

@timeit
def slow_function():
    sum(range(1_000_000))

slow_function()
# [slow_function] executed in 0.0123 seconds.
```

### `@retry`

Retries a function when it raises, waiting longer between each attempt. After the last attempt, the original exception is re-raised.

```python
from pyessential.decorators import retry

@retry(tries=4, delay=0.5, backoff=2, exceptions=(ConnectionError, TimeoutError))
def fetch_data():
    ...
```

This waits 0.5s, 1s, then 2s between attempts. Only the listed exceptions trigger a retry; anything else is raised immediately.

| Option | Meaning |
|--------|---------|
| `tries` | Total attempts, including the first (default 3) |
| `delay` | Seconds to wait after the first failure (default 1.0) |
| `backoff` | Multiplier applied to the wait after each failure (default 2.0; use 1 for a constant delay) |
| `max_delay` | Upper limit for any single wait |
| `jitter` | Up to this many extra random seconds added to each wait |
| `exceptions` | Exception class or tuple of classes that trigger a retry (default `Exception`) |
| `on_retry` | Callback `on_retry(exc, attempt, wait)`, e.g. for logging |

### `@deprecated`

Emits a `DeprecationWarning` when the function or class is used.

```python
from pyessential.decorators import deprecated

@deprecated("use new_func instead", version="0.2.0")
def old_func():
    ...
```

Python hides `DeprecationWarning` by default outside of `__main__` and test runs. Pass `category=FutureWarning` if you want end users to always see it.

### Random generators

```python
from pyessential import generate_random_int, generate_secret_key

generate_random_int(1, 10)   # e.g. 7 (both ends are included)
generate_secret_key(16)      # 32 hex characters (the length is in bytes)
```

### `Logger`

```python
from pyessential import Logger

with Logger(log_name="my_app", log_dir="logs", enable_console=True) as log:
    log.info("Application started")
    log.error("Something went wrong")
```

### Command line

```bash
pyessential --version
python -m pyessential --version   # also works
```

## 🛠️ Development

```bash
git clone https://github.com/Abhi39054/PyEssential.git
cd PyEssential
pip install -e .
pip install pytest
pytest
```

### Releasing

1. Move the entries under `[Unreleased]` in `CHANGELOG.md` to a new version heading with today's date.
2. Bump the version in `pyessential/_version.py`, commit, and push to `main`:
```bash
   git commit -am "chore: bump version to X.Y.Z"
   git push origin main
```
3. Tag the release and push the tag:
```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin vX.Y.Z
```
4. CI runs the tests, builds the package, publishes to TestPyPI, waits for approval, publishes to PyPI, and creates the GitHub Release.

The tag must match the version in `_version.py` (`vX.Y.Z` ↔ `X.Y.Z`), or the build fails.

## 📝 Changelog

See [CHANGELOG.md](https://github.com/Abhi39054/PyEssential/blob/main/CHANGELOG.md) for what changed in each release.

## 🤝 Contributing

Contributions are welcome. See [CONTRIBUTING.md](https://github.com/Abhi39054/PyEssential/blob/main/CONTRIBUTING.md).

## 📄 License

Released under the [MIT License](https://github.com/Abhi39054/PyEssential/blob/main/LICENSE).