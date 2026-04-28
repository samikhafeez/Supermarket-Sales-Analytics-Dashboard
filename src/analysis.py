"""
Legacy analysis helpers - retained for notebook compatibility.

New code should call ``services.analytics`` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.data_loader import run_sql  # noqa: E402


def run_query(query: str):
    return run_sql(query)


def get_total_revenue() -> float:
    df = run_sql("SELECT ROUND(SUM(total), 2) AS total_revenue FROM sales;")
    return float(df["total_revenue"].iloc[0])


def get_average_rating() -> float:
    df = run_sql("SELECT ROUND(AVG(rating), 2) AS avg_rating FROM sales;")
    return float(df["avg_rating"].iloc[0])


def get_top_branch() -> str:
    df = run_sql(
        """
        SELECT branch FROM sales
        GROUP BY branch
        ORDER BY SUM(total) DESC
        LIMIT 1;
        """
    )
    return str(df["branch"].iloc[0])
