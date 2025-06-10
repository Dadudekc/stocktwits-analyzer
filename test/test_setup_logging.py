import pytest
import logging
import os
from pathlib import Path

import sys
# Ensure the parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logins.setup_logging import setup_logging

@pytest.fixture
def log_dir(tmp_path):
    """Fixture to provide a temporary log directory for testing."""
    log_directory = tmp_path / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)  # Ensure it exists
    return log_directory


@pytest.fixture
def logger_instance(log_dir):
    """Fixture to create and return a test logger."""
    return setup_logging("test_logger", log_dir=log_dir)


def test_logger_creation(logger_instance):
    """Ensure the logger is created successfully."""
    assert isinstance(logger_instance, logging.Logger)
    assert logger_instance.name == "test_logger"


def test_log_directory_creation(logger_instance, log_dir):
    """Ensure the log directory is created."""
    assert log_dir.exists() and log_dir.is_dir(), f"Log directory does not exist: {log_dir}"


def test_log_file_creation(logger_instance, log_dir):
    """Ensure the log file is created after logging."""
    log_file = log_dir / "test_logger.log"
    logger_instance.info("This is a test log entry.")

    assert log_file.exists(), f"Log file was not created: {log_file}"
    assert log_file.stat().st_size > 0, "Log file is empty after writing a log entry."


def test_console_logging(logger_instance, caplog):
    """Ensure logs are sent to the console."""
    with caplog.at_level(logging.INFO):
        logger_instance.info("Console log test")

    assert "Console log test" in caplog.text


def test_file_logging(logger_instance, log_dir):
    """Ensure logs are written to the file."""
    log_file = log_dir / "test_logger.log"
    logger_instance.info("File log test")

    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()

    assert "File log test" in log_content


def test_log_rotation(logger_instance, log_dir):
    """Test that log rotation works correctly."""
    log_file = log_dir / "test_logger.log"
    
    # Write enough data to exceed 5MB and trigger rotation
    large_entry = "Filling up log file for rotation test. " * 500  # ~20KB per line
    for _ in range(3000):  # ~60MB total
        logger_instance.debug(large_entry)

    # Ensure the main log file and backup files exist
    rotated_logs = list(log_dir.glob("test_logger.log*"))

    # Debugging Output
    print(f"Log files found: {[file.name for file in rotated_logs]}")

    assert log_file.exists(), "Main log file does not exist after logging."
    assert len(rotated_logs) > 1, f"Log rotation failed. Expected >1 log files, found: {len(rotated_logs)}"
