"""
Logging configuration for EcoNex project.

Provides consistent logging setup across all modules.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "econex",
    level: int = logging.INFO,
    log_file: str = None
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.
    
    Parameters
    ----------
    name : str
        Logger name.
    level : int
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_file : str, optional
        Path to log file. If None, only console logging is used.
    
    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    logger.setLevel(level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] \033[1m%(module)s\033[0m - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    
    simple_formatter = logging.Formatter(
        fmt='%(levelname)-8s | %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if path provided)
    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        logger.debug(f"Log file created: {log_path}")
    
    return logger


def get_logger(name: str = "econex") -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Parameters
    ----------
    name : str
        Logger name (use module name for hierarchical logging).
    
    Returns
    -------
    logging.Logger
        Logger instance.
    """
    return logging.getLogger(name)
