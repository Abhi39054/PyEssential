import pytest
import os
import shutil
import re
import json
import sys
import logging
from pyessentials.logger import Logger # Assuming the main Logger class is saved in 'logger.py'

# --- Configuration ---
TEMP_LOG_DIR = "./temp_pytest_logs"
TEST_LOG_NAME = "test_app"

def get_log_paths(log_dir, log_name):
    """Utility function to generate expected log paths."""
    return {
        'stdin': os.path.join(log_dir, f"{log_name}_stdin.log"),
        'stdout': os.path.join(log_dir, f"{log_name}_stdout.log"),
        'error': os.path.join(log_dir, f"{log_name}_error.log"),
    }

def get_log_content(filepath):
    """Utility function to read content from a log file."""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

@pytest.fixture(scope="session")
def log_setup():
    """
    Pytest fixture to create and clean up the temporary log directory.
    This runs once per test session.
    """
    # Setup
    if os.path.exists(TEMP_LOG_DIR):
        shutil.rmtree(TEMP_LOG_DIR)
    os.makedirs(TEMP_LOG_DIR)
    
    paths = get_log_paths(TEMP_LOG_DIR, TEST_LOG_NAME)
    
    # Yield the log paths to the tests
    yield paths

    # Teardown
    if os.path.exists(TEMP_LOG_DIR):
        shutil.rmtree(TEMP_LOG_DIR)

@pytest.fixture(autouse=True)
def clean_logs(log_setup):
    """
    Pytest fixture to clean up individual log files before each test.
    This mimics the setUp() method in unittest.
    """
    for path in log_setup.values():
        if os.path.exists(path):
            os.remove(path)
    
    # Yield control back to the test
    yield

# Use a test class to group related tests
class TestLoggerPytest:
    """Test suite for the Logger class using Pytest conventions."""
    
    def test_01_initialization_and_path_check(self, log_setup):
        """Test if the Logger initializes correctly and reports the correct file paths."""
        with Logger(log_dir=TEMP_LOG_DIR, log_name=TEST_LOG_NAME) as log:
            # Check path properties
            assert log.stdin_path.endswith(f"{TEST_LOG_NAME}_stdin.log")
            assert log.stdout_path.endswith(f"{TEST_LOG_NAME}_stdout.log")
            assert log.error_path.endswith(f"{TEST_LOG_NAME}_error.log")
        
        # Re-initialize to check internal logger handlers
        log_check = Logger(log_dir=TEMP_LOG_DIR, log_name=TEST_LOG_NAME)
        # Check that only one FileHandler is present by default
        assert len(log_check._stdout_logger.handlers) == 1 
        log_check.close()


    def test_02_message_routing_and_content(self, log_setup):
        """Test if messages are routed correctly to STDOUT, STDIN, and STDERR logs."""
        message_info = "The process is running."
        message_error = "Failed to connect to service."
        message_stdin = "User input received."

        with Logger(log_dir=TEMP_LOG_DIR, log_name=TEST_LOG_NAME, level="DEBUG") as log:
            log.debug("A detailed debug message.")
            log.info(message_info)
            log.warning("Potential issue detected.")
            
            log.error(message_error)
            log.critical("System shutdown imminent.")
            
            log.stdin(message_stdin)

        # 1. Check STDOUT Log (debug, info, warning)
        stdout_content = get_log_content(log_setup['stdout'])
        assert message_info in stdout_content
        assert message_error not in stdout_content
        assert message_stdin not in stdout_content # STDIN messages go to separate file
        
        # 2. Check STDERR Log (error, critical)
        error_content = get_log_content(log_setup['error'])
        assert message_error in error_content
        assert "System shutdown imminent." in error_content
        assert message_info not in error_content

        # 3. Check STDIN Log (stdin)
        stdin_content = get_log_content(log_setup['stdin'])
        assert message_stdin in stdin_content
        assert "INFO" in stdin_content # stdin uses info level internally
        assert message_error not in stdin_content

    def test_03_exception_and_traceback_logging(self, log_setup):
        """Test logging of exceptions using both exception() and log_error()."""
        
        with Logger(log_dir=TEMP_LOG_DIR, log_name=TEST_LOG_NAME) as log:
            try:
                raise KeyError("Test key error for structured logging.")
            except KeyError as e:
                # 1. Test log.exception()
                log.exception("Handled error during dictionary lookup.")
                
                # 2. Test log.log_error(e)
                structured_data = log.log_error(e)

        error_content = get_log_content(log_setup['error'])

        # 1. Check for standard traceback (from log.exception())
        assert "Traceback (most recent call last):" in error_content
        assert "KeyError: 'Test key error for structured logging.'" in error_content
        assert "Handled error during dictionary lookup." in error_content
        
        # 2. Check for structured log data (from log.log_error). This should be a string representation of a dict.
        # Since log_error logs the whole dict object, we check for stringified parts.
        assert "'exception_type': 'KeyError'" in error_content
        assert "'lineno':" in error_content
        
        # 3. Check returned structured data integrity
        assert structured_data["exception_type"] == "KeyError"
        assert "Test key error for structured logging." in structured_data["exception_message"]
    
    def test_04_console_handler_presence(self):
        """Test if StreamHandlers are correctly added when enable_console is True."""
        # Use a temporary logger instance for this test
        log_console = Logger(log_dir=TEMP_LOG_DIR, log_name="console_test", enable_console=True)
        
        # STDOUT logger should have FileHandler and StreamHandler (2 total)
        assert len(log_console._stdout_logger.handlers) == 2
        # STDERR logger should have FileHandler and StreamHandler (2 total)
        assert len(log_console._error_logger.handlers) == 2
        # STDIN logger should only have FileHandler (1 total)
        assert len(log_console._stdin_logger.handlers) == 1
        
        # Verify the console handler streams
        sh_stdout = [h for h in log_console._stdout_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert sh_stdout[1].stream == sys.stdout

        sh_error = [h for h in log_console._error_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert sh_error[1].stream == sys.stderr

        log_console.close()

    def test_05_context_manager_cleanup(self, log_setup):
        """Test if the __exit__ method calls close() and cleans up handlers."""
        log = Logger(log_dir=TEMP_LOG_DIR, log_name="cleanup_test")
        
        # Handlers exist before exit
        assert len(log._stdout_logger.handlers) > 0
        
        # Enter and immediately exit the context manager
        with log:
            log.info("Testing cleanup.")
        
        # Check if handlers were removed after __exit__ (which calls close)
        assert len(log._stdout_logger.handlers) == 0
        assert len(log._error_logger.handlers) == 0
        assert len(log._stdin_logger.handlers) == 0
        
        # Check if files were written
        assert os.path.exists(log.stdout_path)