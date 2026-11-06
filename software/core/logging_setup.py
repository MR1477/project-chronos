
"""Logging configuration for Project Chronos."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_directory="logs",
    log_level="INFO",
    max_bytes=1_000_000,
    backup_count=5,
):
    """Configure console and rotating file logging."""

    level = logging.getLevelName(log_level.upper())

    if not isinstance(level, int):
        raise ValueError(f"Invalid logging level: {log_level}")

    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    if backup_count < 1:
        raise ValueError("backup_count must be at least 1")

    directory = Path(log_directory)
    directory.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("chronos")
    logger.setLevel(level)
    logger.propagate = False

    # Remove and close previously configured handlers.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        directory / "chronos.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

