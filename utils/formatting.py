"""Presentation-layer helpers for formatting values consistently."""

from __future__ import annotations

from config.settings import CURRENCY_SYMBOL


def format_currency(value: float, decimals: int = 2) -> str:
    """Format a numeric value as a currency string (e.g. ``£1,234.56``)."""
    if value is None:
        return "-"
    try:
        return f"{CURRENCY_SYMBOL}{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a value already on a 0-100 scale as ``12.3%``."""
    if value is None:
        return "-"
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "-"


def format_number(value: float, decimals: int = 0) -> str:
    """Format a plain number with thousands separators."""
    if value is None:
        return "-"
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "-"
