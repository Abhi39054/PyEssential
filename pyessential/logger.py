"""
Logger utility for application logging.

This module provides the ``Logger`` class, a logging utility that integrates
with Python's standard ``logging`` library. Each ``Logger`` writes to:

* ``<log_name>_stdout.log`` - the main log: every record at or above the
  configured level, in chronological order (errors included by default, so you
  can see what happened right before a failure).
* ``<log_name>_error.log``  - a focused log holding only ERROR and CRITICAL
  records (including exceptions).
* ``<log_name>_stdin.log``  - input/ingress events recorded with ``stdin()``.

All files use timed rotation. Optional console output sends records below ERROR
to ``sys.stdout`` and ERROR/CRITICAL to ``sys.stderr``.

Thread safety:
    * Logging calls (``debug``, ``info``, ``error``, ``log_error``, ...) are
      thread-safe. Each underlying handler serializes its own writes with an
      internal lock, and no extra shared state is touched on the logging path.
    * Creating and closing ``Logger`` instances is also thread-safe: handler
      setup and teardown are guarded by a module-level re-entrant lock, and
      ``close()`` is idempotent.

Limitations:
    * Loggers are registered globally by name in the ``logging`` module, so two
      ``Logger`` instances with the same ``log_name`` share the same underlying
      loggers. The most recently created instance owns the handlers: creating
      it replaces the older instance's handlers (a ``RuntimeWarning`` is
      emitted), and closing the older instance afterwards does nothing. Use a
      unique ``log_name`` per instance.
    * ``TimedRotatingFileHandler`` is not safe for multiple *processes* writing
      to the same file (rollover can fail with ``PermissionError`` on Windows).
      For multi-process use, give each process its own ``log_name`` or route
      records through a ``QueueHandler``/``QueueListener``.
    * After ``close()`` the loggers have no handlers, so debug/info messages are
      dropped and warnings and above fall back to Python's last-resort handler
      (stderr).
    * Requires Python 3.8+ (uses ``stacklevel`` in logging calls).
"""

import logging
import os
import sys
import threading
import traceback
import warnings
import weakref
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, Union

# Guards handler setup/teardown and the instance registry.
_LOCK = threading.RLock()

# log_name -> the Logger instance that currently owns the handlers.
_INSTANCES: "weakref.WeakValueDictionary[str, Logger]" = weakref.WeakValueDictionary()


class _BelowLevelFilter(logging.Filter):
    """Pass only records strictly below ``level`` (e.g. everything under ERROR)."""

    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < self.level


class Logger:
    """
    A logging utility class for managing application logs.

    Files written (in ``log_dir``):

    1. ``<log_name>_stdout.log`` - main log, all levels in order. Includes
       ERROR/CRITICAL unless ``include_errors_in_main=False``.
    2. ``<log_name>_error.log``  - ERROR and CRITICAL only.
    3. ``<log_name>_stdin.log``  - events recorded with ``stdin()``.

    The class can be used as a context manager to ensure handlers are closed.

    Example:
        >>> log = Logger(log_name="my_app", enable_console=True)
        >>> log.info("Application started.")
        >>> log.error("Something went wrong!")
        >>> log.close()

        or

        >>> with Logger(log_name="my_app", enable_console=True) as log:
        ...     log.info("Application started.")
        ...     log.error("Something went wrong!")
    """

    _LEVEL_MAP = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(
        self,
        log_dir: str = "logs",
        log_name: str = "project",
        level: Union[str, int] = "debug",
        when: str = "midnight",
        interval: int = 1,
        backup_count: int = 7,
        enable_console: bool = False,
        fmt: str = "%(asctime)s.%(msecs)03d - %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        encoding: str = "utf-8",
        include_errors_in_main: bool = True,
    ) -> None:
        """
        Args:
            log_dir: Directory to store log files, relative to the current
                working directory unless absolute. Default is ``'logs'``.
            log_name: Base name for the three log files
                (``<log_name>_stdin.log``, ``<log_name>_stdout.log``,
                ``<log_name>_error.log``). Use a unique name per instance.
            level: Logging level, either a name ('debug', 'info', 'warning',
                'error', 'critical') or a ``logging`` int constant.
                Default is ``'debug'``.
            when: Time interval type for log rotation. Default is ``'midnight'``.
            interval: Interval for log rotation. Default is 1.
            backup_count: Number of backup log files to keep. Default is 7.
            enable_console: Also log to the console (records below ERROR to
                stdout, ERROR and above to stderr). Default is False.
            fmt: Log message format.
            datefmt: Date format used in logs.
            encoding: Encoding for log files. Default is ``'utf-8'``.
            include_errors_in_main: If True (default), ERROR/CRITICAL records
                are written to the main ``_stdout.log`` as well as to
                ``_error.log``, so the main log tells the whole story. Set to
                False to keep the main log free of errors (previous behavior).

        Raises:
            ValueError: If ``level`` is not a valid level name or int.
        """
        log_level = self._resolve_level(level)
        error_level = max(log_level, logging.ERROR)

        self.log_dir = os.path.abspath(log_dir)
        self.log_name = log_name
        self.include_errors_in_main = include_errors_in_main
        self._closed = False

        self.stdin_path = os.path.join(self.log_dir, f"{self.log_name}_stdin.log")
        self.stdout_path = os.path.join(self.log_dir, f"{self.log_name}_stdout.log")
        self.error_path = os.path.join(self.log_dir, f"{self.log_name}_error.log")

        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        file_opts = dict(
            when=when,
            interval=interval,
            backup_count=backup_count,
            encoding=encoding,
            formatter=formatter,
        )

        with _LOCK:
            existing = _INSTANCES.get(self.log_name)
            if existing is not None and not existing._closed:
                warnings.warn(
                    f"A Logger named {self.log_name!r} is already active; its handlers "
                    "are being replaced. Use a unique log_name per instance.",
                    RuntimeWarning,
                    stacklevel=2,
                )

            os.makedirs(self.log_dir, exist_ok=True)

            built = []
            try:
                # --- stdin: its own logger and file ---
                self._stdin_logger = self._build_logger(f"{self.log_name}.stdin", log_level)
                built.append(self._stdin_logger)
                self._stdin_logger.addHandler(
                    self._file_handler(self.stdin_path, log_level, **file_opts)
                )

                # --- main logger: one logger, several level-filtered handlers ---
                self._logger = self._build_logger(f"{self.log_name}.main", log_level)
                built.append(self._logger)

                # Main file: everything (optionally without ERROR+)
                main_fh = self._file_handler(self.stdout_path, log_level, **file_opts)
                if not include_errors_in_main:
                    main_fh.addFilter(_BelowLevelFilter(logging.ERROR))
                self._logger.addHandler(main_fh)

                # Error file: ERROR and CRITICAL only
                self._logger.addHandler(
                    self._file_handler(self.error_path, error_level, **file_opts)
                )

                if enable_console:
                    out_h = logging.StreamHandler(sys.stdout)
                    out_h.setLevel(log_level)
                    out_h.addFilter(_BelowLevelFilter(logging.ERROR))
                    out_h.setFormatter(formatter)
                    self._logger.addHandler(out_h)

                    err_h = logging.StreamHandler(sys.stderr)
                    err_h.setLevel(error_level)
                    err_h.setFormatter(formatter)
                    self._logger.addHandler(err_h)
            except Exception:
                # Don't leak handlers if setup fails partway through.
                for lg in built:
                    self._close_handlers(lg)
                raise

            _INSTANCES[self.log_name] = self

    # --------------- Public Methods ---------------
    def debug(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log a debug message to the main log."""
        self._logger.debug(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def info(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log an info message to the main log."""
        self._logger.info(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def warning(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log a warning message to the main log."""
        self._logger.warning(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def error(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log an error message to the error log (and the main log by default)."""
        self._logger.error(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def critical(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log a critical message to the error log (and the main log by default)."""
        self._logger.critical(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def exception(self, msg, *args, stacklevel=2, **kwargs) -> None:
        """Log an error message with the current exception info.

        Goes to the error log (and the main log by default). Intended to be
        called from an ``except`` block.
        """
        kwargs["exc_info"] = True
        self._logger.error(msg, *args, stacklevel=stacklevel, **kwargs)

    def stdin(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Explicitly record 'input' or ingress events."""
        self._stdin_logger.info(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def log_error(self, err: BaseException) -> Dict[str, Any]:
        """Log an exception with its traceback at ERROR level.

        Works inside or outside an ``except`` block, since the traceback is
        taken from the exception object itself. Thread-safe (uses no shared
        state besides the logger's own handlers).

        Args:
            err: The exception instance to log.

        Returns:
            A dict describing the exception (type, message, location,
            function, timestamp and full traceback).
        """
        tb = err.__traceback__
        if tb is not None:
            last = traceback.extract_tb(tb)[-1]  # frame where it was actually raised
            filename = os.path.basename(last.filename)
            lineno = last.lineno
            func_name = last.name
        else:
            filename, lineno, func_name = "<unknown>", -1, "<unknown>"

        data = {
            "exception_type": type(err).__name__,
            "exception_message": str(err),
            "filename": filename,
            "lineno": lineno,
            "function": func_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceback": "".join(traceback.format_exception(type(err), err, tb)),
        }

        # Traceback is already in `data`, so no exc_info (avoids duplication).
        # stacklevel=2 makes [file:line] point at the caller of log_error.
        self._logger.error(data, stacklevel=2)
        return data

    def close(self) -> None:
        """Flush and close all handlers. Safe to call more than once and from any thread."""
        with _LOCK:
            if self._closed:
                return
            self._closed = True

            # If a newer instance with the same log_name replaced us, the
            # loggers (and handlers) now belong to it. Leave them alone.
            if _INSTANCES.get(self.log_name) is not self:
                return

            for lg in (self._stdin_logger, self._logger):
                self._close_handlers(lg)

            _INSTANCES.pop(self.log_name, None)

    def __enter__(self) -> "Logger":
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        self.close()

    # --------------- Internals ---------------
    @classmethod
    def _resolve_level(cls, level: Union[str, int]) -> int:
        """Convert a level name or int into a ``logging`` level int."""
        if isinstance(level, bool):
            raise ValueError(f"Invalid log level: {level!r}")
        if isinstance(level, int):
            return level
        if isinstance(level, str):
            try:
                return cls._LEVEL_MAP[level.strip().lower()]
            except KeyError:
                pass
        valid = ", ".join(cls._LEVEL_MAP)
        raise ValueError(
            f"Invalid log level: {level!r}. Use one of: {valid} (or a logging int constant)."
        )

    @staticmethod
    def _close_handlers(logger: logging.Logger) -> None:
        """Detach, flush and close every handler on the given logger.

        Handlers are removed first so no new records are dispatched to them;
        ``close()`` then waits on each handler's own lock, so in-flight writes
        from other threads finish before the file is closed.
        """
        for h in list(logger.handlers):
            logger.removeHandler(h)
            try:
                h.flush()
            except Exception:
                pass
            try:
                h.close()
            except Exception:
                pass

    @staticmethod
    def _build_logger(name: str, level: int) -> logging.Logger:
        """Get the named logger, reset to a clean state (no handlers, no propagation)."""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        # Close (not just drop) existing handlers to avoid leaked file handles
        # and rotation/locking problems on re-initialization.
        Logger._close_handlers(logger)
        logger.propagate = False  # Don't pass messages to the root logger
        return logger

    @staticmethod
    def _file_handler(
        filepath: str,
        level: int,
        when: str,
        interval: int,
        backup_count: int,
        encoding: str,
        formatter: logging.Formatter,
    ) -> TimedRotatingFileHandler:
        fh = TimedRotatingFileHandler(
            filename=filepath,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding,
            delay=True,
            utc=False,
        )
        fh.setLevel(level)
        fh.setFormatter(formatter)
        return fh