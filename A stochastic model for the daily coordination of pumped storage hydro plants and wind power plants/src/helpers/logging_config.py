"""Centralized Logging Configuration.

Provides consistent logging setup across all project frameworks.
Supports both console output and file logging with configurable levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional



PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RelativePathFormatter(logging.Formatter):
    """Custom formatter that replaces absolute project paths with relative paths."""

    def format(self, record):
        # Get the standard formatted message
        formatted_message = super().format(record)
        # Replace absolute project root with relative prefix
        return formatted_message.replace(str(PROJECT_ROOT), ".")


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """Configure and return a logger with console and optional file output.

    This function should be called once per application entry point
    (e.g., workflow.py) to set up the root logger for that framework.
    Child modules should use get_logger() instead.

    Args:
        name: Logger name (e.g., 'econex' for optimization, 'wds' for water simulation).
            Child loggers use hierarchical names like 'econex.preprocessing'.
        level: Logging level (e.g., logging.DEBUG, logging.INFO, logging.WARNING).
        log_file: Path to log file. If provided, logs will also be written to this file.
            File logging captures DEBUG level regardless of console level.

    Returns:
        Configured logger instance.

    Examples:
        >>> # In workflow.py (entry point)
        >>> logger = setup_logger("econex", level=logging.INFO, log_file="run.log")
        >>> logger.info("Starting workflow")

        >>> # In other modules
        >>> logger = get_logger("econex.preprocessing")
        >>> logger.debug("Loading data...")
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicates on re-initialization
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level

    # Console handler with concise format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = RelativePathFormatter(
        fmt='%(asctime)s | %(levelname)-8s | \033[1m%(name)s\033[0m | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler with detailed format (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # Always capture debug in file
        file_format = RelativePathFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    # Don't propagate to root logger to avoid duplicate messages
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    This is the preferred way to get a logger in individual modules.
    The logger will inherit configuration from the parent logger
    set up by setup_logger().

    Args:
        name: Full hierarchical logger name (e.g., 'econex.preprocessing',
            'wds.simulation'). Should start with the framework root name.

    Returns:
        Logger instance.

    Examples:
        >>> # In preprocessing.py
        >>> logger = get_logger("econex.preprocessing")
        >>> logger.info("Loading configuration...")
    """
    return logging.getLogger(name)
