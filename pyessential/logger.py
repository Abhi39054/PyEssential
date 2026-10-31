"""
Logger utility for application logging.

This module provides the ``Logger`` class, a logging utility that integrates
with Python's standard ``logging`` library. It configures three separate
loggers/files for STDIN (ingress), STDOUT (general/info) and ERROR
(errors/critical) messages, with timed log rotation and optional console
output.

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


class Logger:
    """
    A logging utility class for managing application logs with separate streams.

    It sets up three distinct, rotation-enabled log files:

    1. ``<log_name>_stdin.log``  - input/ingress events
    2. ``<log_name>_stdout.log`` - debug/info/warning messages
    3. ``<log_name>_error.log``  - error/critical messages and exceptions

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
            enable_console: Also log to the console. Default is False.
            fmt: Log message format.
            datefmt: Date format used in logs.
            encoding: Encoding for log files. Default is ``'utf-8'``.

        Raises:
            ValueError: If ``level`` is not a valid level name or int.
        """
        log_level = self._resolve_level(level)

        self.log_dir = os.path.abspath(log_dir)
        self.log_name = log_name
        self._closed = False

        self.stdin_path = os.path.join(self.log_dir, f"{self.log_name}_stdin.log")
        self.stdout_path = os.path.join(self.log_dir, f"{self.log_name}_stdout.log")
        self.error_path = os.path.join(self.log_dir, f"{self.log_name}_error.log")

        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

        common = dict(
            level=log_level,
            when=when,
            interval=interval,
            backup_count=backup_count,
            formatter=formatter,
            encoding=encoding,
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
                # Three dedicated loggers so routing is explicit and simple
                self._stdin_logger = self._build_logger(
                    name=f"{self.log_name}.stdin",
                    filepath=self.stdin_path,
                    enable_console=False,  # stdin is typically not logged to console
                    **common,
                )
                built.append(self._stdin_logger)

                self._stdout_logger = self._build_logger(
                    name=f"{self.log_name}.stdout",
                    filepath=self.stdout_path,
                    enable_console=enable_console,
                    console_to_stderr=False,  # -> sys.stdout
                    **common,
                )
                built.append(self._stdout_logger)

                self._error_logger = self._build_logger(
                    name=f"{self.log_name}.error",
                    filepath=self.error_path,
                    enable_console=enable_console,
                    console_to_stderr=True,  # -> sys.stderr
                    **common,
                )
                built.append(self._error_logger)
            except Exception:
                # Don't leak handlers if setup fails partway through.
                for lg in built:
                    self._close_handlers(lg)
                raise

            _INSTANCES[self.log_name] = self

    # --------------- Public Methods ---------------
    def debug(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log a debug message to the stdout logger."""
        self._stdout_logger.debug(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def info(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log an info message to the stdout logger."""
        self._stdout_logger.info(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def warning(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log a warning message to the stdout logger."""
        self._stdout_logger.warning(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def error(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log an error message to the error logger."""
        self._error_logger.error(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def critical(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Log a critical message to the error logger."""
        self._error_logger.critical(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def exception(self, msg, *args, stacklevel=2, **kwargs) -> None:
        """Log an error message with the current exception info to the error logger.

        Intended to be called from an ``except`` block.
        """
        kwargs["exc_info"] = True
        self._error_logger.error(msg, *args, stacklevel=stacklevel, **kwargs)

    def stdin(self, msg, *args, exc_info=False, stacklevel=2, **kwargs) -> None:
        """Explicitly record 'input' or ingress events."""
        self._stdin_logger.info(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def log_error(self, err: BaseException) -> Dict[str, Any]:
        """Log an exception with its traceback to the error logger.

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
        self._error_logger.error(data, stacklevel=2)
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

            for lg in (self._stdin_logger, self._stdout_logger, self._error_logger):
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
    def _build_logger(
        name: str,
        filepath: str,
        level: int,
        when: str,
        interval: int,
        backup_count: int,
        formatter: logging.Formatter,
        encoding: str,
        enable_console: bool = False,
        console_to_stderr: bool = False,
    ) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        # Close (not just drop) existing handlers to avoid leaked file handles
        # and rotation/locking problems on re-initialization.
        Logger._close_handlers(logger)
        logger.propagate = False  # Don't pass messages to the root logger

        fh = TimedRotatingFileHandler(
            filename=filepath,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding,
            delay=True,
            utc=False,
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        if enable_console:
            stream = sys.stderr if console_to_stderr else sys.stdout
            sh = logging.StreamHandler(stream)
            sh.setFormatter(formatter)
            sh.setLevel(level)
            logger.addHandler(sh)

        return logger