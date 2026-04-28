"""
Central configuration for the Supermarket Sales Analytics Dashboard.

All paths, constants, schemas, and styling live here so the rest of the
codebase does not hardcode environment-specific details.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parents[1]
DB_PATH: Path = BASE_DIR / "supermarket_sales.db"
RAW_DIR: Path = BASE_DIR / "data" / "raw"
PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
LOG_DIR: Path = BASE_DIR / "logs"

# Ensure optional directories exist (no-op if already present).
for _p in (PROCESSED_DIR, LOG_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

CURRENCY_SYMBOL: str = "£"

DAY_ORDER: List[str] = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

DEFAULT_FILES: List[Tuple[str, str]] = [
    ("supermarket_sales.csv", "Supermarket A"),
    ("supermarket_sales_competitor.csv", "Supermarket B"),
    ("supermarket_sales_competitor_2.csv", "Supermarket C"),
]

# Canonical column names after standardisation.
REQUIRED_COLUMNS: List[str] = [
    "invoice_id", "branch", "city", "customer_type", "gender", "product_line",
    "unit_price", "quantity", "tax", "total", "sale_date", "sale_time",
    "payment", "cogs", "gross_margin_percentage", "gross_income", "rating",
]

NUMERIC_COLUMNS: List[str] = [
    "unit_price", "quantity", "tax", "total", "cogs",
    "gross_margin_percentage", "gross_income", "rating",
]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

# Colour-blind-friendly qualitative palette.
COLOR_PALETTE: List[str] = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#17becf",
]

CHART_TEMPLATE: str = "plotly_white"
