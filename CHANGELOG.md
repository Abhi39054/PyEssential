# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.6] - 2026-10-10
### Changed
- Releases are now published with PyPI Trusted Publishing instead of API tokens.
### Fixed
- The `LICENSE` and `CONTRIBUTING.md` links in the README now work on the PyPI page.

## [0.1.5] - 2026-10-04
### Added
- `@timeit` now supports `async` functions.
- `@retry` decorator with exponential backoff, jitter, `max_delay`, and async support.
- `py.typed` marker, so type checkers can use the package's type hints.
### Changed
- `@timeit` now prints the elapsed time even if the function raises, and uses `time.perf_counter()` for more accurate timing.
- `generate_random_int` and `generate_secret_key` now raise `ValueError` for invalid arguments instead of returning an empty key or failing with an obscure error.
- Corrected the `generate_secret_key` docs: `length` is the number of bytes, so the hex key is twice as long.

## [0.1.4] - 2026-10-03
### Added
- `pyessential --version` command line interface.
- `@deprecated` decorator for functions and classes.
### Changed
- Minimum supported Python version is now 3.9.
- Releases are now published from `v*` git tags.

[Unreleased]: https://github.com/Abhi39054/PyEssential/compare/v0.1.6...HEAD
[0.1.5]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.6
[0.1.5]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.5
[0.1.4]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.4