# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.5] - 2026-10-04
### Added
- `@timeit` now supports `async` functions.
### Changed
- `@timeit` now prints the elapsed time even if the function raises, and uses `time.perf_counter()` for more accurate timing.

## [0.1.4] - 2026-10-03
### Added
- `pyessential --version` command line interface.
- `@deprecated` decorator for functions and classes.
### Changed
- Minimum supported Python version is now 3.9.
- Releases are now published from `v*` git tags.

[Unreleased]: https://github.com/Abhi39054/PyEssential/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.5
[0.1.4]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.4