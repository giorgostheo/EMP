"""
Logging utility module for configuring and managing application logs.

This module:
1. Parses the 'V' environment variable to control logging level
2. Maps values of 'V' to Python's built-in logging levels
3. Configures the logging system based on the mapped level

Environment Variables:
- V (int): Logging verbosity level
  - 0: ERROR only (default)
  - 1: INFO and above
  - 2: DEBUG and above

Usage:
import log_utils
# Automatically configures logging when imported
"""

import os
import logging
from datetime import datetime

def get_log_level_from_env():
    """
    Parse the 'V' environment variable to determine logging level.

    Returns:
        int: Python logging level based on V value
    """
    try:
        # Get V from environment, default to 0 if not set or invalid
        v = int(os.getenv('V', '0'))

        # Clamp values outside of 0-2 range
        if v < 0:
            v = 0
            logging.error("Invalid V value (<0), defaulting to ERROR level")
        elif v > 2:
            v = 2
            logging.error("Invalid V value (>2), defaulting to DEBUG level")

        # Map V to logging levels
        if v == 0:
            return logging.ERROR
        elif v == 1:
            return logging.INFO
        else:  # v == 2
            return logging.DEBUG

    except ValueError:
        # If conversion fails, default to ERROR level
        logging.error("Invalid V value (not an integer), defaulting to ERROR level")
        return logging.ERROR

def setup_logging():
    """
    Configure the logging system with appropriate log level from environment.

    This sets up logging with a timestamped format and the level determined by V.
    """
    level = get_log_level_from_env()

    # Format includes timestamp in hh:mm:ss:ms format
    logging.basicConfig(
        level=level,
        format='[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'  # Time-only format for concise output
    )

# Configure logging when this module is imported
setup_logging()
