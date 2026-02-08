"""
Centralized Logging Configuration
Provides structured JSON logging for the TraceNet application
"""

import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logger(name: str = "tracenet", level: str = "INFO") -> logging.Logger:
    """
    Configure structured JSON logging.
    
    Args:
        name: Logger name (default: "tracenet")
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to prevent duplicates
    logger.handlers = []
    
    # Console handler with JSON formatting
    handler = logging.StreamHandler(sys.stdout)
    
    # JSON formatter for structured logging
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Create default logger instance
logger = setup_logger()
