# 🐍 PyEssential

**A growing collection of Python utilities and decorators to simplify common development tasks.**

---

[![CI](https://github.com/Abhi39054/PyEssential/actions/workflows/pypi-publish.yaml/badge.svg)](https://github.com/Abhi39054/PyEssential/actions/workflows/pypi-publish.yaml)
[![PyPI version](https://img.shields.io/pypi/v/pyessential.svg)](https://pypi.org/project/pyessential/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyessential.svg)](https://pypi.org/project/pyessential/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## ✨ Features

`PyEssential` aims to be the go-to library for small, reusable tools that you often find yourself writing from scratch.

* **Performance:** Includes the ready-to-use `@timeit` decorator for simple function benchmarking.
* **Command line:** Check your installed version with `pyessential --version`.
* **Code Clarity:** Utility functions for common tasks like string manipulation (e.g., casing). *(Coming soon!)*
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

```python
from pyessential.decorators import timeit

@timeit
def slow_function():
    sum(range(1_000_000))

slow_function()
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
pytest
```

### Releasing

1. Bump the version in `pyessential/_version.py`, commit, and push to `main`:
   ```bash
   git commit -am "chore: bump version to 0.1.4"
   git push origin main
   ```
2. Tag the release and push the tag:
   ```bash
   git tag -a v0.1.4 -m "Release 0.1.4"
   git push origin v0.1.4
   ```
3. CI runs the tests, builds the package, publishes to TestPyPI, waits for approval, publishes to PyPI, and creates the GitHub Release.

The tag must match the version in `_version.py` (`v0.1.4` ↔ `0.1.4`), or the build fails.

## 🤝 Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

Released under the [MIT License](LICENSE).