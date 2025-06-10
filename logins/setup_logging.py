import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(
    script_name: str,
    log_dir: str = None,  # Accepts both str and Path
    max_log_size: int = 5 * 1024 * 1024,  # 5MB limit
    backup_count: int = 3,
    console_log_level: int = logging.INFO,
    file_log_level: int = logging.DEBUG
) -> logging.Logger:
    """
    Sets up a unified logger.

    - Supports both file & console logging.
    - Auto-creates log directories if missing.
    - Prevents duplicate handlers.

    :param script_name: Name of the script (used in logs).
    :param log_dir: Directory to store logs.
    :param max_log_size: Max file size before rotating logs (default: 5MB).
    :param backup_count: Number of old log files to retain (default: 3).
    :param console_log_level: Console logging level (default: INFO).
    :param file_log_level: File logging level (default: DEBUG).
    :return: Configured logging.Logger instance.
    """

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)  # Capture all logs

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Convert log_dir to a Path object if it's a string
    if log_dir is None:
        project_root = Path(__file__).resolve().parents[1]
        log_dir = project_root / 'logs' / 'Utilities'
    else:
        log_dir = Path(log_dir)  # Ensure it's a Path object

    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)

    # Define log file path
    log_file = log_dir / f"{script_name}.log"

    # Setup Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Setup File Handler
    try:
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=max_log_size,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"⚠️ Error setting up file handler: {e}")

    # Setup Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Example Usage
if __name__ == "__main__":
    logger = setup_logging("test_logger", log_dir=os.path.join(os.getcwd(), "logs", "social"))
    logger.info("✅ Logging system initialized successfully!")
