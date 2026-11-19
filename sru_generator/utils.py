"""
Utility functions for the SRU Generator package.
"""

import logging


def setup_logger(
    name: str = "sru_generator", level: int = logging.INFO
) -> logging.Logger:
    """
    Opt-in helper for applications: attach a console handler to the package logger.

    The package itself never calls this; importing it configures no logging.
    Calling it replaces any handlers already on the logger.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger
