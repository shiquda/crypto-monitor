"""
Logging configuration for Crypto Monitor.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def setup_logging(log_dir: Path | None = None, log_level: int = logging.INFO) -> None:
    """
    Setup logging configuration.

    Args:
        log_dir: Directory to save log files. If None, uses default user data directory.
        log_level: Logging level (default: logging.INFO)
    """
    if log_dir is None:
        if os.name == "nt":  # Windows
            log_dir = Path(os.environ.get("APPDATA", "")) / "crypto-monitor" / "logs"
        else:  # Linux/Mac
            log_dir = Path.home() / ".config" / "crypto-monitor" / "logs"

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"

    # Create formatters and handlers
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File Handler (with rotation)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info(f"Logging initialized. Log file: {log_file}")
