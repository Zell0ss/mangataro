"""
Centralized logging configuration for MangaTaro API

Sets up Loguru with:
- Log rotation (50 MB per file)
- Retention (30 days)
- Compression (gzip)
- Separate files for different log levels
- Structured JSON logging for errors
- Console output with colors
"""
import sys
from pathlib import Path
from loguru import logger
import os

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Remove default handler
logger.remove()

# Console handler with colors (INFO and above)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# General application log (DEBUG and above)
logger.add(
    LOGS_DIR / "mangataro.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="50 MB",  # Rotate when file reaches 50 MB
    retention="30 days",  # Keep logs for 30 days
    compression="gz",  # Compress rotated logs
    enqueue=True,  # Thread-safe
)

# Error log (WARNING and above)
logger.add(
    LOGS_DIR / "errors.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="WARNING",
    rotation="20 MB",
    retention="60 days",  # Keep errors longer
    compression="gz",
    enqueue=True,
)

# Critical errors in JSON format for easier parsing
logger.add(
    LOGS_DIR / "critical.json",
    format="{message}",
    level="ERROR",
    rotation="10 MB",
    retention="90 days",
    compression="gz",
    serialize=True,  # JSON format
    enqueue=True,
)

# Tracking-specific log (for chapter tracking operations)
tracking_logger = logger.bind(component="tracking")
logger.add(
    LOGS_DIR / "tracking.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    rotation="30 MB",
    retention="14 days",
    compression="gz",
    filter=lambda record: record["extra"].get("component") == "tracking",
    enqueue=True,
)

# API requests log (for debugging API issues)
api_logger = logger.bind(component="api")
logger.add(
    LOGS_DIR / "api.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="50 MB",
    retention="7 days",
    compression="gz",
    filter=lambda record: record["extra"].get("component") == "api",
    enqueue=True,
)

# Log the configuration
logger.info("Logging system initialized")
logger.info(f"Logs directory: {LOGS_DIR.absolute()}")
logger.debug(f"Debug mode: {os.getenv('API_DEBUG', 'false')}")


def get_logger(component: str = None):
    """
    Get a logger instance, optionally bound to a component.

    Args:
        component: Component name for filtering (e.g., "tracking", "api", "scraping")

    Returns:
        Logger instance

    Examples:
        >>> log = get_logger("tracking")
        >>> log.info("Starting chapter tracking")  # Goes to tracking.log

        >>> log = get_logger()
        >>> log.info("General message")  # Goes to mangataro.log
    """
    if component:
        return logger.bind(component=component)
    return logger


# Export configured loggers
__all__ = ["logger", "get_logger", "tracking_logger", "api_logger"]
