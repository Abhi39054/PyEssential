import inspect
import logging
import os
import re
import sys
import threading
from logging import FileHandler

import pytest

from pyessential.logger import Logger

LOG_NAME = "test_app"


def log_paths(log_dir, log_name=LOG_NAME):
    """Expected log file paths for a given directory and name."""
    return {
        "stdin": os.path.join(str(log_dir), f"{log_name}_stdin.log"),
        "stdout": os.path.join(str(log_dir), f"{log_name}_stdout.log"),
        "error": os.path.join(str(log_dir), f"{log_name}_error.log"),
    }


def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def make_logger(tmp_path):
    """Factory that creates Loggers in tmp_path and always closes them afterwards,
    even if the test fails (important on Windows, where open files block cleanup)."""
    created = []

    def _make(**kwargs):
        kwargs.setdefault("log_dir", str(tmp_path))
        kwargs.setdefault("log_name", LOG_NAME)
        lg = Logger(**kwargs)
        created.append(lg)
        return lg

    yield _make

    for lg in created:
        lg.close()


# ---------------------------------------------------------------- basics
class TestBasics:
    def test_initialization_and_paths(self, make_logger, tmp_path):
        log = make_logger()
        assert log.stdin_path.endswith(f"{LOG_NAME}_stdin.log")
        assert log.stdout_path.endswith(f"{LOG_NAME}_stdout.log")
        assert log.error_path.endswith(f"{LOG_NAME}_error.log")
        # Only a file handler by default
        assert len(log._stdout_logger.handlers) == 1

    def test_default_log_dir_is_logs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with Logger(log_name="default_dir_test") as log:
            log.info("hello")
        assert (tmp_path / "logs").is_dir()

    def test_message_routing_and_content(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger(level="DEBUG") as log:
            log.debug("A detailed debug message.")
            log.info("The process is running.")
            log.warning("Potential issue detected.")
            log.error("Failed to connect to service.")
            log.critical("System shutdown imminent.")
            log.stdin("User input received.")

        out, err, inp = read(p["stdout"]), read(p["error"]), read(p["stdin"])
        assert "The process is running." in out
        assert "Failed to connect to service." not in out
        assert "User input received." not in out

        assert "Failed to connect to service." in err
        assert "System shutdown imminent." in err
        assert "The process is running." not in err

        assert "User input received." in inp
        assert "INFO" in inp
        assert "Failed to connect to service." not in inp

    def test_console_handlers(self, make_logger):
        log = make_logger(log_name="console_test", enable_console=True)
        assert len(log._stdout_logger.handlers) == 2
        assert len(log._error_logger.handlers) == 2
        assert len(log._stdin_logger.handlers) == 1

        def console(lg):
            # TimedRotatingFileHandler is itself a StreamHandler, so exclude files
            return [
                h for h in lg.handlers
                if isinstance(h, logging.StreamHandler) and not isinstance(h, FileHandler)
            ]

        assert console(log._stdout_logger)[0].stream is sys.stdout
        assert console(log._error_logger)[0].stream is sys.stderr

    def test_context_manager_cleanup(self, make_logger):
        log = make_logger(log_name="cleanup_test")
        assert len(log._stdout_logger.handlers) > 0
        with log:
            log.info("Testing cleanup.")
        assert len(log._stdout_logger.handlers) == 0
        assert len(log._error_logger.handlers) == 0
        assert len(log._stdin_logger.handlers) == 0
        assert os.path.exists(log.stdout_path)


# ------------------------------------------------------- level validation
class TestLevel:
    @pytest.mark.parametrize("bad", ["warnng", "", "verbose", None, 1.5, True])
    def test_invalid_level_raises(self, tmp_path, bad):
        with pytest.raises(ValueError):
            Logger(log_dir=str(tmp_path), log_name="bad_level", level=bad)

    def test_int_level_accepted(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger(level=logging.WARNING) as log:
            log.info("hidden")
            log.warning("shown")
        out = read(p["stdout"])
        assert "shown" in out
        assert "hidden" not in out

    def test_level_name_is_case_insensitive(self, make_logger):
        log = make_logger(level="Info")
        assert log._stdout_logger.level == logging.INFO


# ------------------------------------------------ exceptions / log_error
class TestExceptions:
    def test_exception_and_log_error_inside_except(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger() as log:
            try:
                raise KeyError("Test key error for structured logging.")
            except KeyError as e:
                log.exception("Handled error during dictionary lookup.")
                data = log.log_error(e)

        err = read(p["error"])
        assert "Traceback (most recent call last):" in err
        assert "KeyError: 'Test key error for structured logging.'" in err
        assert "Handled error during dictionary lookup." in err
        assert "'exception_type': 'KeyError'" in err
        assert data["exception_type"] == "KeyError"
        assert "Test key error for structured logging." in data["exception_message"]

    def test_log_error_logs_traceback_once(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger() as log:
            try:
                raise ValueError("only once")
            except ValueError as e:
                log.log_error(e)
        assert read(p["error"]).count("Traceback (most recent call last)") == 1

    def test_log_error_works_outside_except_block(self, make_logger, tmp_path):
        p = log_paths(tmp_path)

        def boom():
            raise ValueError("raised in helper")

        try:
            boom()
        except ValueError as e:
            saved = e

        with make_logger() as log:
            data = log.log_error(saved)  # called OUTSIDE the except block

        assert data["function"] == "boom"  # frame where it was raised
        assert data["lineno"] != -1
        assert data["filename"] == os.path.basename(__file__)
        err = read(p["error"])
        assert "raised in helper" in err
        assert "NoneType: None" not in err

    def test_log_error_with_never_raised_exception(self, make_logger):
        with make_logger() as log:
            data = log.log_error(RuntimeError("never raised"))
        assert data["filename"] == "<unknown>"
        assert data["lineno"] == -1

    def test_log_error_points_at_caller(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger() as log:
            log.log_error(ValueError("where am I"))
        # [file:line] from the log format must be this file, not logger.py
        assert f"[{os.path.basename(__file__)}:" in read(p["error"])
        assert "[logger.py:" not in read(p["error"])

    def test_exception_has_no_exc_info_parameter(self):
        assert "exc_info" not in inspect.signature(Logger.exception).parameters

    def test_exit_does_not_shadow_traceback_module(self):
        params = inspect.signature(Logger.__exit__).parameters
        assert "traceback" not in params


# ------------------------------------------------ handler lifecycle
class TestHandlers:
    def test_recreating_logger_does_not_leak_handlers(self, make_logger, tmp_path):
        first = make_logger()
        first.info("open the file")
        old_handlers = list(first._stdout_logger.handlers)
        assert old_handlers[0].stream is not None  # file is open

        with pytest.warns(RuntimeWarning):
            second = make_logger()

        assert old_handlers[0].stream is None  # old handler was closed
        assert len(second._stdout_logger.handlers) == 1  # no duplicates

    def test_close_is_idempotent(self, make_logger):
        log = make_logger()
        log.info("x")
        log.close()
        log.close()  # must not raise

    def test_closing_replaced_instance_does_not_close_newer(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        old = make_logger()
        with pytest.warns(RuntimeWarning):
            new = make_logger()
        old.close()  # should be a no-op for the shared loggers
        new.info("still alive")
        assert "still alive" in read(p["stdout"])

    def test_no_warning_after_proper_close(self, make_logger, recwarn):
        make_logger().close()
        make_logger()
        assert not [w for w in recwarn if issubclass(w.category, RuntimeWarning)]

    def test_failed_init_does_not_leak(self, tmp_path):
        with pytest.raises(ValueError):
            Logger(log_dir=str(tmp_path), log_name="bad_when", when="not-a-valid-when")
        assert logging.getLogger("bad_when.stdin").handlers == []


# ------------------------------------------------------- thread safety
class TestThreading:
    def test_concurrent_logging_is_intact(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        n_threads, n_msgs = 8, 100
        errors = []

        with make_logger(level="info") as log:
            def work(i):
                try:
                    for j in range(n_msgs):
                        log.info("thread=%d msg=%d", i, j)
                        if j % 10 == 0:
                            try:
                                1 / 0
                            except ZeroDivisionError as e:
                                log.log_error(e)
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)

            threads = [threading.Thread(target=work, args=(i,)) for i in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert not errors
        lines = read(p["stdout"]).splitlines()
        assert len(lines) == n_threads * n_msgs
        pattern = re.compile(r"thread=\d+ msg=\d+$")
        assert all(pattern.search(line) for line in lines)  # no interleaved lines

    def test_concurrent_create_and_close(self, tmp_path):
        errors = []

        def work(i):
            try:
                for _ in range(20):
                    with Logger(log_dir=str(tmp_path), log_name=f"worker_{i}") as lg:
                        lg.info("hi")
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=work, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors