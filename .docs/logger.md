# Logger

A small, thread-safe logging utility built on Python's standard `logging` library.
One `Logger` gives you three rotating log files, optional console output, and a helper
for logging exceptions with full context.

```python
from pyessential.logger import Logger
```

## Quick start

```python
from pyessential.logger import Logger

log = Logger(log_name="my_app", enable_console=True)

log.info("Application started.")
log.warning("Disk space is low.")
log.error("Could not connect to the database.")
```

Or as a context manager, which closes the log files for you:

```python
with Logger(log_name="my_app") as log:
    log.info("Application started.")
```

## Files written

Files are created inside `log_dir` (default `logs/`, created automatically). A file is only
created when something is first written to it.

| File | Contains |
|---|---|
| `<log_name>_stdout.log` | The main log: every record at or above the configured level, in order. Includes errors by default, so you can see what happened right before a failure. |
| `<log_name>_error.log` | A focused log with only `ERROR` and `CRITICAL` records (including exceptions). |
| `<log_name>_stdin.log` | Input/ingress events recorded with `stdin()`. |

An error logged with `log.error(...)` therefore appears once in the main log and once in the
error log. Set `include_errors_in_main=False` if you want the main log free of errors.

Default line format:

```
2026-10-31 13:22:36.786 - ERROR    [app.py:17] Could not connect to the database.
```

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `log_dir` | `"logs"` | Folder for the log files. Relative paths are relative to the current working directory. |
| `log_name` | `"project"` | Base name of the log files. Must be unique per `Logger` (see [Limitations](#limitations)). |
| `level` | `"debug"` | Minimum level: `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"` (case-insensitive), or a `logging` constant such as `logging.INFO`. Anything else raises `ValueError`. |
| `when` | `"midnight"` | When to rotate files. Any value accepted by `TimedRotatingFileHandler` (`"S"`, `"M"`, `"H"`, `"D"`, `"midnight"`, `"W0"`–`"W6"`). |
| `interval` | `1` | Rotation interval, in units of `when`. |
| `backup_count` | `7` | Number of rotated files to keep. `0` keeps all of them. |
| `enable_console` | `False` | Also print to the console. Records below `ERROR` go to stdout, `ERROR` and above go to stderr. |
| `fmt` | see above | Log line format (standard `logging` format string). |
| `datefmt` | `"%Y-%m-%d %H:%M:%S"` | Date format used in log lines. |
| `encoding` | `"utf-8"` | Encoding of the log files. |
| `include_errors_in_main` | `True` | Write `ERROR`/`CRITICAL` records to the main log as well as the error log. |

## Methods

| Method | Goes to |
|---|---|
| `debug(msg, *args, **kwargs)` | main log |
| `info(msg, *args, **kwargs)` | main log |
| `warning(msg, *args, **kwargs)` | main log |
| `error(msg, *args, **kwargs)` | error log (and main log by default) |
| `critical(msg, *args, **kwargs)` | error log (and main log by default) |
| `exception(msg, *args, **kwargs)` | error log (and main log by default), with the current traceback |
| `stdin(msg, *args, **kwargs)` | stdin log |
| `log_error(err)` | error log (and main log by default), returns a dict |
| `close()` | closes all files |

Messages support the usual `%`-style arguments, and the file and line shown in the log point at
your code, not at the library:

```python
log.info("Processed %d files in %.2fs", count, elapsed)
```

### Logging exceptions

Inside an `except` block, `exception()` logs your message plus the traceback:

```python
try:
    risky()
except Exception:
    log.exception("risky() failed")
```

`log_error(err)` logs a structured record and also returns it. It works inside or outside an
`except` block, because it reads the traceback from the exception itself:

```python
try:
    risky()
except Exception as e:
    details = log.log_error(e)
    # details = {
    #     "exception_type": "ValueError",
    #     "exception_message": "...",
    #     "filename": "app.py",      # where it was raised
    #     "lineno": 42,
    #     "function": "risky",
    #     "timestamp": "2026-10-31 13:22:36",
    #     "traceback": "Traceback (most recent call last): ...",
    # }
```

### Recording input events

```python
log.stdin("User uploaded report.pdf")   # -> <log_name>_stdin.log
```

## Examples

### Several loggers in one application

Create each logger once, at module level, with its own `log_name`:

```python
# app/utils/logger.py
from pyessential.logger import Logger

_opts = dict(log_dir="logs", level="info", enable_console=True, backup_count=30)

app_logger = Logger(log_name="app", **_opts)
api_logger = Logger(log_name="api", **_opts)
```

```python
# anywhere else
from app.utils.logger import app_logger

app_logger.info("Ready.")
```

Python only runs a module once per process, so the loggers are built once and shared by every
file that imports them. Don't create a `Logger` inside a function or request handler, since that
would rebuild the handlers on every call.

### Keep errors out of the main log

```python
log = Logger(log_name="my_app", include_errors_in_main=False)
log.info("goes to my_app_stdout.log")
log.error("goes only to my_app_error.log")
```

### Only warnings and above

```python
log = Logger(log_name="my_app", level="warning")
log.info("ignored")
log.warning("written")
```

## Thread safety

- Logging calls are safe to make from many threads at once. Lines are never interleaved.
- Creating and closing `Logger` instances is also thread-safe, and `close()` can be called more
  than once.

## Limitations

- **Unique names.** Python's `logging` module keeps loggers in a global registry by name. If you
  create a second `Logger` with the same `log_name` while the first is still open, the new one
  takes over the files, a `RuntimeWarning` is emitted, and closing the older one afterwards does
  nothing. Give each `Logger` its own `log_name`.
- **Multiple processes.** Rotation is not safe when several processes write to the same files
  (for example `uvicorn --workers 4`); on Windows it can fail with `PermissionError`. Give each
  process its own `log_name`, or send records through a `QueueHandler`/`QueueListener`.
- **After `close()`**, debug/info messages are dropped, and warnings and above fall back to
  Python's last-resort handler on stderr.
- Requires Python 3.8 or newer.