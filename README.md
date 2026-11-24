# PyEssential

**A growing collection of Python utilities and decorators that simplify common development tasks.**

[![CI](https://github.com/Abhi39054/PyEssential/actions/workflows/pypi-publish.yaml/badge.svg)](https://github.com/Abhi39054/PyEssential/actions/workflows/pypi-publish.yaml)
[![PyPI version](https://img.shields.io/pypi/v/pyessential.svg)](https://pypi.org/project/pyessential/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyessential.svg)](https://pypi.org/project/pyessential/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Abhi39054/PyEssential/blob/main/LICENSE)

---

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Decorators](#decorators)
  - [Random generators](#random-generators)
  - [Logger](#logger)
  - [Command line](#command-line)
- [Documentation](#documentation)
- [Development](#development)
  - [Prerequisites](#prerequisites)
  - [Clone and set up](#clone-and-set-up)
  - [Run the tests](#run-the-tests)
  - [Releasing](#releasing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Introduction

PyEssential is a small library of reusable tools that developers often end up writing from
scratch: timing and retrying functions, marking old code as deprecated, generating secure random
values, and setting up rotating log files.

The goals are simple:

- **Easy to adopt.** Import a function or class and start using it, with no setup code.
- **No dependencies.** It uses only the Python standard library.
- **Well typed.** It ships a `py.typed` marker, so editors and type checkers can use its type hints.
- **Built to grow.** New utility groups (for example networking, file I/O or validation) can be
  added without changing what already exists.

## Features

| Area | What you get |
|---|---|
| **Decorators** | `@timeit` for benchmarking, `@retry` with exponential backoff, and `@deprecated` for marking old code. `@timeit` and `@retry` also work with `async` functions. |
| **Generators** | Cryptographically secure random integers and secret keys. |
| **Logging** | A `Logger` with rotating log files for the main log, errors and input events, plus optional console output. |
| **Command line** | Check your installed version with `pyessential --version`. |
| **Typing** | Ships a `py.typed` marker. |
| **JSON utilities** | Safe JSON and JSON Lines file I/O, nested-data helpers, merging and diffing. |

## Installation

**Requirements:** Python 3.9 or newer.

Install from [PyPI](https://pypi.org/project/pyessential/):

```bash
pip install pyessential
```

Upgrade to the latest release:

```bash
pip install --upgrade pyessential
```

Check that it is installed:

```bash
pyessential --version
```

## Quick Start

```python
from pyessential import Logger, generate_secret_key
from pyessential.decorators import retry, timeit

@timeit
@retry(tries=3, delay=0.5, exceptions=ConnectionError)
def fetch_data():
    ...

with Logger(log_name="my_app", enable_console=True) as log:
    log.info("Starting up")
    log.info("Generated a %d-character key", len(generate_secret_key()))
    fetch_data()
```

## Usage

### Decorators

#### `@timeit`

Prints how long a function took, even if it raises. Works with `async def` functions too.

```python
from pyessential.decorators import timeit

@timeit
def slow_function():
    sum(range(1_000_000))

slow_function()
# [slow_function] executed in 0.0123 seconds.
```

#### `@retry`

Retries a function when it raises, waiting longer between each attempt. After the last attempt,
the original exception is re-raised.

```python
from pyessential.decorators import retry

@retry(tries=4, delay=0.5, backoff=2, exceptions=(ConnectionError, TimeoutError))
def fetch_data():
    ...
```

This waits 0.5 s, 1 s, then 2 s between attempts. Only the listed exceptions trigger a retry;
anything else is raised immediately.

| Option | Meaning |
|--------|---------|
| `tries` | Total attempts, including the first (default `3`). |
| `delay` | Seconds to wait after the first failure (default `1.0`). |
| `backoff` | Multiplier applied to the wait after each failure (default `2.0`; use `1` for a constant delay). |
| `max_delay` | Upper limit for any single wait. |
| `jitter` | Up to this many extra random seconds added to each wait. |
| `exceptions` | Exception class or tuple of classes that trigger a retry (default `Exception`). |
| `on_retry` | Callback `on_retry(exc, attempt, wait)`, for example for logging. |

#### `@deprecated`

Emits a `DeprecationWarning` when the function or class is used.

```python
from pyessential.decorators import deprecated

@deprecated("use new_func instead", version="0.2.0")
def old_func():
    ...
```

> **Note:** Python hides `DeprecationWarning` by default outside of `__main__` and test runs.
> Pass `category=FutureWarning` if you want end users to always see it.

### Random generators

```python
from pyessential import generate_random_int, generate_secret_key

generate_random_int(1, 10)   # e.g. 7 (both ends are included)
generate_secret_key(16)      # 32 hex characters (the length is in bytes)
```

Both functions use Python's `secrets` module, so the values are suitable for tokens and keys.

### Logger

```python
from pyessential import Logger

with Logger(log_name="my_app", log_dir="logs", enable_console=True) as log:
    log.info("Application started")
    log.error("Something went wrong")
```

The logger writes rotating files to `log_dir`: a main log, an error log, and an input log.

### Command line

```bash
pyessential --version
python -m pyessential --version   # also works
```

## Documentation

Detailed guides with parameters and examples:

- [Decorators](https://github.com/Abhi39054/PyEssential/blob/main/.docs/decorators.md)
- [Generators](https://github.com/Abhi39054/PyEssential/blob/main/.docs/generators.md)
- [Logger](https://github.com/Abhi39054/PyEssential/blob/main/.docs/logger.md)
- [JSON utilities](https://github.com/Abhi39054/PyEssential/blob/main/.docs/json_utils.md)
- [Validator Utility](https://github.com/Abhi39054/PyEssential/blob/main/.docs/validators.md)

## Development

### Prerequisites

- Python 3.9 or newer
- [Git](https://git-scm.com/downloads)

### Clone and set up

```bash
git clone https://github.com/Abhi39054/PyEssential.git
cd PyEssential
```

Create and activate a virtual environment:

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the package in editable mode, so your changes are picked up without reinstalling, along
with the test tools:

```bash
pip install -e .
pip install pytest
```

### Run the tests

```bash
pytest
```

### Releasing

1. Move the entries under `[Unreleased]` in `CHANGELOG.md` to a new version heading with
   today's date.
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

4. CI runs the tests, builds the package, publishes to TestPyPI, waits for approval, publishes
   to PyPI, and creates the GitHub Release.

The tag must match the version in `_version.py` (`vX.Y.Z` corresponds to `X.Y.Z`), or the
build fails.

## Roadmap

PyEssential is structured so that new utility groups can be added easily. Ideas under
consideration include networking, file I/O and validation helpers. Suggestions are welcome:
open an [issue](https://github.com/Abhi39054/PyEssential/issues).

## Changelog

See [CHANGELOG.md](https://github.com/Abhi39054/PyEssential/blob/main/CHANGELOG.md) for what
changed in each release.

## Contributing

Contributions are welcome. Please read
[CONTRIBUTING.md](https://github.com/Abhi39054/PyEssential/blob/main/CONTRIBUTING.md) before
opening a pull request. To report a bug or request a feature, open an
[issue](https://github.com/Abhi39054/PyEssential/issues).

## License

Released under the [MIT License](https://github.com/Abhi39054/PyEssential/blob/main/LICENSE).

## Author

Created and maintained by **Abhishek Kumar** ([@Abhi39054](https://github.com/Abhi39054)).