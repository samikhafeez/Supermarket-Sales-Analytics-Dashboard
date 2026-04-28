"""
Centralised logging configuration.

Every module should call `get_logger(__name__)` rather than instantiating its
own logger. This guarantees uniform formatting and a single file handler.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from config.settings import LOG_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_FILE = LOG_DIR / "dashboard.log"

_configured = False


def _configure_root() -> None:
    """Attach handlers once per process."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Clear any pre-existing handlers (Streamlit re-imports modules).
    root.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    try:
        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # If the log directory is read-only (e.g. on Streamlit Cloud) we simply
        # fall back to stdout-only logging rather than crashing.
        pass

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger with shared configuration."""
    _configure_root()
    return logging.getLogger(name)
