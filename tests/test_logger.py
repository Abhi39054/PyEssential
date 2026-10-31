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


def console_handlers(lg):
    """Stream handlers that are not file handlers (TimedRotatingFileHandler is a StreamHandler too)."""
    return [
        h for h in lg.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, FileHandler)
    ]


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
    def test_initialization_and_paths(self, make_logger):
        log = make_logger()
        assert log.stdin_path.endswith(f"{LOG_NAME}_stdin.log")
        assert log.stdout_path.endswith(f"{LOG_NAME}_stdout.log")
        assert log.error_path.endswith(f"{LOG_NAME}_error.log")
        # main logger: main file + error file; stdin logger: one file
        assert len(log._logger.handlers) == 2
        assert len(log._stdin_logger.handlers) == 1

    def test_default_log_dir_is_logs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with Logger(log_name="default_dir_test") as log:
            log.info("hello")
        assert (tmp_path / "logs").is_dir()

    def test_context_manager_cleanup(self, make_logger):
        log = make_logger(log_name="cleanup_test")
        assert len(log._logger.handlers) > 0
        with log:
            log.info("Testing cleanup.")
        assert len(log._logger.handlers) == 0
        assert len(log._stdin_logger.handlers) == 0
        assert os.path.exists(log.stdout_path)


# ------------------------------------------------------------- routing
class TestRouting:
    def test_main_log_has_everything_in_order(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger(level="DEBUG") as log:
            log.debug("debug-msg")
            log.info("info-msg")
            log.warning("warning-msg")
            log.error("error-msg")
            log.critical("critical-msg")

        main = read(p["stdout"])
        positions = [main.index(m) for m in
                     ("debug-msg", "info-msg", "warning-msg", "error-msg", "critical-msg")]
        assert positions == sorted(positions)  # chronological, errors in context

    def test_error_log_has_only_error_and_critical(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger(level="DEBUG") as log:
            log.debug("debug-msg")
            log.info("info-msg")
            log.warning("warning-msg")
            log.error("error-msg")
            log.critical("critical-msg")

        err = read(p["error"])
        assert "error-msg" in err
        assert "critical-msg" in err
        for hidden in ("debug-msg", "info-msg", "warning-msg"):
            assert hidden not in err

    def test_each_error_appears_once_per_file(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger() as log:
            log.error("only-once")
        assert read(p["stdout"]).count("only-once") == 1
        assert read(p["error"]).count("only-once") == 1

    def test_errors_can_be_excluded_from_main(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger(include_errors_in_main=False) as log:
            log.info("info-msg")
            log.error("error-msg")
            log.critical("critical-msg")

        main, err = read(p["stdout"]), read(p["error"])
        assert "info-msg" in main
        assert "error-msg" not in main
        assert "critical-msg" not in main
        assert "error-msg" in err and "critical-msg" in err

    def test_stdin_is_separate(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger() as log:
            log.info("info-msg")
            log.error("error-msg")
            log.stdin("input-msg")

        inp = read(p["stdin"])
        assert "input-msg" in inp
        assert "INFO" in inp
        assert "info-msg" not in inp and "error-msg" not in inp
        assert "input-msg" not in read(p["stdout"])
        assert "input-msg" not in read(p["error"])

    def test_error_level_logger_still_fills_error_log(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger(level="error") as log:
            log.warning("warning-msg")
            log.error("error-msg")
        assert "warning-msg" not in read(p["stdout"])
        assert "error-msg" in read(p["stdout"])
        assert "error-msg" in read(p["error"])

    def test_critical_level_logger_filters_plain_errors(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger(level="critical") as log:
            log.error("error-msg")
            log.critical("critical-msg")
        assert "error-msg" not in read(p["error"])
        assert "critical-msg" in read(p["error"])


# ------------------------------------------------------------- console
class TestConsole:
    def test_console_handlers_present(self, make_logger):
        log = make_logger(log_name="console_test", enable_console=True)
        # main file + error file + console stdout + console stderr
        assert len(log._logger.handlers) == 4
        assert len(log._stdin_logger.handlers) == 1

        streams = {h.stream for h in console_handlers(log._logger)}
        assert streams == {sys.stdout, sys.stderr}

    def test_no_console_handlers_by_default(self, make_logger):
        log = make_logger()
        assert console_handlers(log._logger) == []

    def test_console_output_split_by_level_without_duplicates(self, make_logger, capsys):
        with make_logger(enable_console=True) as log:
            log.info("info-msg")
            log.warning("warning-msg")
            log.error("error-msg")
            log.critical("critical-msg")

        captured = capsys.readouterr()
        assert captured.out.count("info-msg") == 1
        assert captured.out.count("warning-msg") == 1
        assert "error-msg" not in captured.out
        assert "critical-msg" not in captured.out
        assert captured.err.count("error-msg") == 1
        assert captured.err.count("critical-msg") == 1
        assert "info-msg" not in captured.err

    def test_console_respects_include_errors_in_main_independently(self, make_logger, capsys):
        # The option only affects the main *file*; errors still reach stderr.
        with make_logger(enable_console=True, include_errors_in_main=False) as log:
            log.error("error-msg")
        assert capsys.readouterr().err.count("error-msg") == 1


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
        assert log._logger.level == logging.INFO


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

    def test_exception_is_written_to_main_and_error(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger() as log:
            try:
                raise KeyError("both-files")
            except KeyError:
                log.exception("handled")
        for key in ("stdout", "error"):
            content = read(p[key])
            assert "handled" in content
            assert "KeyError: 'both-files'" in content

    def test_log_error_logs_traceback_once_per_file(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        with make_logger() as log:
            try:
                raise ValueError("only once")
            except ValueError as e:
                log.log_error(e)
        assert read(p["error"]).count("Traceback (most recent call last)") == 1
        assert read(p["stdout"]).count("Traceback (most recent call last)") == 1

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
        assert "[logger.py:" not in read(p["stdout"])

    def test_exception_has_no_exc_info_parameter(self):
        assert "exc_info" not in inspect.signature(Logger.exception).parameters

    def test_exit_does_not_shadow_traceback_module(self):
        params = inspect.signature(Logger.__exit__).parameters
        assert "traceback" not in params


# ------------------------------------------------ handler lifecycle
class TestHandlers:
    def test_recreating_logger_does_not_leak_handlers(self, make_logger):
        first = make_logger()
        first.info("open the file")
        old_handlers = list(first._logger.handlers)
        assert old_handlers[0].stream is not None  # main file is open

        with pytest.warns(RuntimeWarning):
            second = make_logger()

        assert all(h.stream is None for h in old_handlers)  # old handlers closed
        assert len(second._logger.handlers) == 2  # no duplicates

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
        assert logging.getLogger("bad_when.main").handlers == []


# ------------------------------------------------------- thread safety
class TestThreading:
    def test_concurrent_logging_is_intact(self, make_logger, tmp_path):
        p = log_paths(tmp_path)
        n_threads, n_msgs, err_every = 8, 100, 10
        errors = []

        with make_logger(level="info") as log:
            def work(i):
                try:
                    for j in range(n_msgs):
                        log.info("thread=%d msg=%d", i, j)
                        if j % err_every == 0:
                            log.error("thread=%d err=%d", i, j)
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)

            threads = [threading.Thread(target=work, args=(i,)) for i in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert not errors
        n_errs = n_threads * (n_msgs // err_every)

        main_lines = read(p["stdout"]).splitlines()
        err_lines = read(p["error"]).splitlines()
        assert len(main_lines) == n_threads * n_msgs + n_errs
        assert len(err_lines) == n_errs

        pattern = re.compile(r"thread=\d+ (msg|err)=\d+$")
        assert all(pattern.search(line) for line in main_lines)  # no interleaved lines
        assert all(pattern.search(line) and "ERROR" in line for line in err_lines)

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