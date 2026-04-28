"""
Data-loading service.

Responsibilities:
- Read raw CSVs from disk or user uploads.
- Standardise column names, dtypes, and derive time-based columns.
- Persist the canonical ``sales`` table into SQLite.
- Provide cached read helpers for the Streamlit layer.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pandas as pd
import streamlit as st

from config.settings import (
    DB_PATH,
    DEFAULT_FILES,
    NUMERIC_COLUMNS,
    RAW_DIR,
    REQUIRED_COLUMNS,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Mapping from raw (heterogeneous) CSV headers to our canonical column names.
_COLUMN_RENAME_MAP = {
    "Invoice ID": "invoice_id",
    "Branch": "branch",
    "City": "city",
    "Customer type": "customer_type",
    "Gender": "gender",
    "Product line": "product_line",
    "Unit price": "unit_price",
    "Quantity": "quantity",
    "Tax 5%": "tax",
    "Total": "total",
    "Date": "sale_date",
    "Time": "sale_time",
    "Payment": "payment",
    "cogs": "cogs",
    "gross margin percentage": "gross_margin_percentage",
    "gross income": "gross_income",
    "Rating": "rating",
}


# ---------------------------------------------------------------------------
# Core transformation
# ---------------------------------------------------------------------------


def standardise_columns(df: pd.DataFrame, supermarket_name: str) -> pd.DataFrame:
    """
    Return a cleaned copy of ``df`` with canonical column names, parsed
    dates/times, numeric dtypes, and convenience columns (year, month, etc).

    Raises:
        ValueError: if any of the canonical columns are missing after rename.
    """
    if df.empty:
        raise ValueError("Input dataframe is empty.")

    out = df.rename(columns=_COLUMN_RENAME_MAP).copy()

    missing: List[str] = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(
            f"Missing required columns after rename: {missing}. "
            f"Found columns: {list(out.columns)}"
        )

    # Parse dates - try day-first first (matches the competitor CSV),
    # fall back to pandas' inference.
    parsed = pd.to_datetime(out["sale_date"], dayfirst=True, errors="coerce")
    if parsed.isna().all():
        parsed = pd.to_datetime(out["sale_date"], errors="coerce")
    out["sale_date"] = parsed

    out["sale_time"] = pd.to_datetime(
        out["sale_time"], format="%H:%M:%S", errors="coerce"
    )

    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # Derived time-based columns for grouping/filtering.
    out["year"] = out["sale_date"].dt.year
    out["month"] = out["sale_date"].dt.month_name()
    out["month_num"] = out["sale_date"].dt.month
    out["day_name"] = out["sale_date"].dt.day_name()
    out["hour"] = out["sale_time"].dt.hour
    out["supermarket_name"] = supermarket_name

    return out


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _read_csv(csv_path: Path, supermarket_name: str) -> pd.DataFrame:
    logger.info("Reading CSV %s (as %s)", csv_path, supermarket_name)
    raw = pd.read_csv(csv_path)
    return standardise_columns(raw, supermarket_name)


def load_raw_csvs(
    files: Iterable[Tuple[str, str]] = DEFAULT_FILES,
) -> pd.DataFrame:
    """Load and combine the default built-in CSVs from ``data/raw``."""
    frames: List[pd.DataFrame] = []
    for filename, market_name in files:
        csv_path = RAW_DIR / filename
        if not csv_path.exists():
            logger.warning("Skipping missing file: %s", csv_path)
            continue
        frames.append(_read_csv(csv_path, market_name))
        logger.info("Loaded %s as %s", filename, market_name)

    if not frames:
        raise FileNotFoundError(
            f"No supermarket CSV files found in {RAW_DIR}. "
            f"Expected one of: {[f for f, _ in files]}"
        )

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["supermarket_name", "invoice_id"])
    logger.info("Combined dataset: %d rows across %d markets", len(combined),
                combined["supermarket_name"].nunique())
    return combined


def persist_to_sqlite(df: pd.DataFrame, db_path: Path = DB_PATH) -> None:
    """
    Write the combined dataset to SQLite, creating indexes that materially
    speed up the analytics queries.
    """
    export = df.copy()

    # SQLite has no native datetime - store ISO strings.
    export["sale_date"] = export["sale_date"].dt.strftime("%Y-%m-%d")
    export["sale_time"] = export["sale_time"].dt.strftime("%H:%M:%S")

    with sqlite3.connect(db_path) as conn:
        export.to_sql("sales", conn, if_exists="replace", index=False)

        # Helpful indexes for grouped/filtered queries.
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_sales_market ON sales(supermarket_name);
            CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
            CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_line);
            CREATE INDEX IF NOT EXISTS idx_sales_market_date ON sales(supermarket_name, sale_date);
            """
        )
        conn.commit()

    logger.info("Persisted %d rows to %s", len(export), db_path)


# ---------------------------------------------------------------------------
# Streamlit-facing cached readers
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Loading sales data from database...")
def load_from_database(db_path: Optional[Path] = None) -> pd.DataFrame:
    """Return the full ``sales`` table as a typed DataFrame (cached)."""
    path = db_path or DB_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Database not found at {path}. "
            f"Run `python -m services.data_loader` to build it."
        )

    with sqlite3.connect(path) as conn:
        df = pd.read_sql_query("SELECT * FROM sales", conn)

    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce")
    df["sale_time"] = pd.to_datetime(df["sale_time"], format="%H:%M:%S",
                                     errors="coerce")
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info("Loaded %d rows from database", len(df))
    return df


@st.cache_data(show_spinner="Processing uploaded files...")
def load_from_uploads(uploaded_payloads: List[Tuple[str, bytes]]) -> pd.DataFrame:
    """
    Combine uploaded CSV payloads into a single standardised DataFrame.

    ``uploaded_payloads`` is a list of (filename, raw_bytes) tuples so that
    Streamlit's cache key remains stable.
    """
    from io import BytesIO

    frames: List[pd.DataFrame] = []
    for idx, (filename, payload) in enumerate(uploaded_payloads, start=1):
        market_name = f"Supermarket {idx}"
        try:
            raw = pd.read_csv(BytesIO(payload))
            frames.append(standardise_columns(raw, market_name))
        except Exception as exc:  # pragma: no cover - user input path
            logger.exception("Failed to process upload %s", filename)
            raise ValueError(f"Could not process {filename}: {exc}") from exc

    if not frames:
        raise ValueError("No valid CSVs to load.")

    return pd.concat(frames, ignore_index=True)


def run_sql(query: str, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Execute a read-only SQL query and return the result."""
    path = db_path or DB_PATH
    if not path.exists():
        raise FileNotFoundError(f"Database not found at {path}.")
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(query, conn)


# ---------------------------------------------------------------------------
# CLI entry point: rebuild the SQLite database from raw CSVs.
# ---------------------------------------------------------------------------


def main() -> None:
    combined = load_raw_csvs()
    persist_to_sqlite(combined)
    print(f"Loaded {len(combined):,} rows into {DB_PATH}")


if __name__ == "__main__":
    main()
