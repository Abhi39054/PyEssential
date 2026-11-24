# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]   

## [0.2.0] - 2026-11-24

### Added
- `pyessential.validators`: helpers for validating common data formats with zero external
  dependencies (`is_email`, `is_url`, `is_uuid`, `is_ip`, `is_port`, `is_hex`,
  `is_domain`, `is_mac_address`, `is_json`, and `is_slug`).
- Unit tests in `tests/test_validators.py` and documentation in `docs/validators.md`.

## [0.1.9] - 2026-11-14

### Added
- `pyessential.json_utils`: helpers for reading and writing JSON and JSON Lines files
  (atomic writes), converting dates/UUIDs/sets, and working with nested data
  (`get_by_path`, `set_by_path`, `flatten_json`, `deep_merge`, `diff_json`, `remove_keys`,
  `keys_to_snake_case`, and more).

### Fixed
- pins CI to ubuntu-24.04 so Python 3.9 is available.

## [0.1.8] - 2026-11-03
### Added
- New `pyessential.folders` module with `ensure_folder`, `list_files`, `list_folders`, `is_folder_empty`, `get_folder_size`, `clear_folder`, `delete_folder`, `delete_old_files`, and `remove_empty_folders`.
- Destructive functions (`clear_folder`, `delete_old_files`, `remove_empty_folders`) support `dry_run=True` and return the affected `Path` list.
- Built-in safety checks that refuse to modify filesystem roots or the user's home folder, ignore folder symlinks when walking/deleting, and clear read-only flags on Windows.
- Unit tests in `tests/test_folders.py`
- Added documentation in `.docs/`.

## [0.1.7] - 2026-10-10
### Changed
- Default `log_dir` is now `"logs"` (was `"../logs"`).
- `<name>_stdout.log` now also contains ERROR/CRITICAL records, so it shows events in order.
  Use `include_errors_in_main=False` for the old behavior. `<name>_error.log` still holds errors only.

### Fixed
- `log_error` no longer logs the traceback twice, reports the correct location, and works outside an `except` block.
- Old handlers are now closed when a `Logger` is re-created (no leaked file handles).
- An invalid `level` now raises `ValueError`; int levels are accepted.
- Docs now refer to `_error.log` instead of `_stderr.log`.

### Added
- Thread-safe creation and closing; a `RuntimeWarning` when a second `Logger` reuses an active `log_name`.
- Type hints and an expanded test suite.

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

[Unreleased]: https://github.com/Abhi39054/PyEssential/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.2.0
[0.1.9]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.9
[0.1.8]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.8
[0.1.7]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.7
[0.1.6]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.6
[0.1.5]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.5
[0.1.4]: https://github.com/Abhi39054/PyEssential/releases/tag/v0.1.4