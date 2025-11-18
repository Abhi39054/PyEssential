"""
    Logger utility for application logging.

    This module provides the 'Logger' class, a robust logging utility that
    integrates with Python's standard 'logging' library. It configures
    three separate loggers/files for STDIN (ingress), STDOUT (general/info),
    and STDERR (errors/critical) messages, with support for
    timed log rotation and console output.

"""

import os
import sys
import traceback
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


class Logger:
    """
    A logging utility class for managing application logs with separate streams.

    It sets up three distinct, rotation-enabled log files:
    1. STDIN (for input/ingress events)
    2. STDOUT (for general debug/info/warning messages)
    3. STDERR (for error/critical messages and exceptions)

    The class is designed to be used as a context manager to ensure log closure.

    Example:
    >>> log = Logger(log_name="my_app", enable_console=True)
    >>> log.info("Application started.")
    >>> log.error("Something went wrong!")

    or 

    >>> with Logger(log_name="my_app", enable_console=True) as log:
    ...     log.info("Application started.")
    ...     log.error("Something went wrong!")
    ...
    """

    _LEVEL_MAP = {
        "debug":logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(
            self,
            log_dir="../logs",
            log_name="project",
            level="debug",
            when="midnight",
            interval=1,
            backup_count=7,
            enable_console=False,
            fmt="%(asctime)s.%(msecs)03d - %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            encoding="utf-8"
    ):
        """
        Args:
            log_dir (str) : Directory to store log files. Default is '../logs'.
            log_name (str) : Base name for the three log files (<log_name>_stdin.log, <log_name>_stdout.log, <log_name>_stderr.log).
            level (str) : Logging level. Default is 'debug'.
            when (str) : Time interval for log rotation. Default is 'midnight'.
            interval (int) : Interval for log rotation. Default is 1.
            backup_count (int) : Number of backup log files to keep. Default is 7.
            enable_console (bool) : Enable console logging. Default is False.
            fmt (str) : Log message format. Default is "%(asctime)s.%(msecs)03d - %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s".
            datefmt (str) : Date format in logs. Default is "%Y-%m-%d %H:%M:%S".
            encoding (str) : Encoding for log files. Default is "utf-8".
        """

        self.log_dir = os.path.abspath(log_dir)
        self.log_name = log_name

        # Filenames (with 'logs' extension as is common; can be changed if needed)
        self.stdin_path = os.path.join(self.log_dir, f"{self.log_name}_stdin.log")
        self.stdout_path = os.path.join(self.log_dir, f"{self.log_name}_stdout.log")
        self.error_path = os.path.join(self.log_dir, f"{self.log_name}_error.log")

        # Ensure Directory
        os.makedirs(self.log_dir, exist_ok=True)

        # Common formatter
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

        # Create three dedicated loggers so routing is explicit and simple
        self._stdin_logger = self._build_logger(
            name=f"{self.log_name}.stdin",
            filepath=self.stdin_path,
            level=level,
            when=when,
            interval=interval,
            backup_count=backup_count,
            formatter=formatter,
            encoding=encoding,
            enable_console=False,   # stdin is typically not logged to console
        )

        self._stdout_logger = self._build_logger(
            name=f"{self.log_name}.stdout",
            filepath=self.stdout_path,
            level=level,
            when=when,
            interval=interval,
            backup_count=backup_count,
            formatter=formatter,
            encoding=encoding,
            enable_console=enable_console,
            console_to_stderr=False # stdout -> sys.stdout
        )

        self._error_logger = self._build_logger(
            name=f"{self.log_name}.error",
            filepath=self.error_path,
            level=level,
            when=when,
            interval=interval,
            backup_count=backup_count,
            formatter=formatter,
            encoding=encoding,
            enable_console=enable_console,
            console_to_stderr=True # stderr -> sys.stderr
        )

    # --------------- Public Methods ---------------
    def debug(self, msg, *args, exc_info=False, stacklevel=2, **kwargs):
        """Log a debug message to stdout logger."""
        self._stdout_logger.debug(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def info(self, msg, *args, exc_info=False, stacklevel=2, **kwargs):
        """Log an info message to stdout logger."""
        self._stdout_logger.info(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def warning(self, msg, *args, exc_info=False, stacklevel=2, **kwargs):
        """Log a warning message to stdout logger."""
        self._stdout_logger.warning(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)

    def error(self, msg, *args, exc_info=False, stacklevel=2, **kwargs):
        """Log an error message to error logger."""
        self._error_logger.error(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)
    
    def critical(self, msg, *args, exc_info=False, stacklevel=2, **kwargs):
        """Log a critical message to error logger."""
        self._error_logger.critical(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs)
    
    def exception(self, msg, *args, exc_info=False, stacklevel=2, **kwargs):
        """Log an exception message to error logger."""
        self._error_logger.error(msg, *args, exc_info=True, stacklevel=stacklevel, **kwargs)

    def stdin(self, msg, *args, exc_info=False, stacklevel=2, **kwargs):
        """Explicitly record 'input' or ingress events."""
        self._stdin_logger.info(msg, *args, exc_info=exc_info, stacklevel=stacklevel, **kwargs) 

    def log_error(self, err: Exception):
        """Log an exception with traceback to the error logger.

        Args:
            err (Exception): The exception instance to log.
        """
        
        exc_type, exc_obj, exc_tb = sys.exc_info()

        if exc_tb is None:
            # It means getting called outputside except block.
            filename = "<unknown>"
            lineno = -1
            func_name = "<unknown>"
        else:
            filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
            func_name = traceback.extract_tb(exc_tb, 1)[0][2]
        
        e_type = err.__class__.__name__

        data = {
            "exception_type": e_type,
            "exception_message": str(err),
            "filename": filename,
            "lineno": lineno,
            "function": func_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceback": traceback.format_exc()
        }

        # log to stderr file
        self.error(data, exc_info=True, stacklevel=2)
        return data
    
    def close(self):
        """
        Flush and close all handlers explicitly.
        """

        for lg in (self._stdin_logger, self._stdout_logger, self._error_logger):
            for h in list(lg.handlers):
                try:
                    h.flush()
                except Exception:
                    pass
                
                try:
                    h.close()
                except Exception:
                    pass

                lg.removeHandler(h)

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    # --------------- Internals ---------------
    @classmethod
    def _build_logger(
            cls,
            name,
            filepath,
            level,
            when,
            interval,
            backup_count,
            formatter,
            encoding,
            enable_console=False,
            console_to_stderr=False
    ):
        
        log_level = cls._LEVEL_MAP.get(level.lower(), logging.DEBUG)
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        logger.handlers.clear()  # Avoid duplicate handlers on re-initialization
        logger.propagate = False # Prevent log messages from being propagated to the root logger

        # Timed Rotating File Handler
        fh = TimedRotatingFileHandler(
            filename=filepath,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding,
            delay=True,
            utc=False
        )
        
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        if enable_console:
            stream = sys.stderr if console_to_stderr else sys.stdout
            sh = logging.StreamHandler(stream)
            sh.setFormatter(formatter)
            sh.setLevel(log_level)
            logger.addHandler(sh)

        return logger
