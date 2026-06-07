"""
Centralized logging configuration for the application.

Controls log levels and output formatting. The verbose flag
(tied to Config.verbose) determines whether DEBUG messages appear.
"""

import logging
import sys
from typing import Optional


_LOG: Optional[logging.Logger] = None


def get_logger(name: str = "assistant") -> logging.Logger:
    """Get the application logger, creating it if needed."""
    global _LOG
    if _LOG is not None:
        return _LOG.getChild(name)

    _LOG = logging.getLogger("assistant")
    _LOG.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    _LOG.addHandler(handler)

    return _LOG.getChild(name)


def set_verbose(enabled: bool) -> None:
    """Switch between INFO (default) and DEBUG logging."""
    root = logging.getLogger("assistant")
    root.setLevel(logging.DEBUG if enabled else logging.INFO)
