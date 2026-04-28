"""
Sidebar filter helpers.

Separating this from the dashboard keeps UI state management out of the main
file and makes it easy to unit-test the filter-application logic.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd
import streamlit as st

from utils.logger import get_logger

logger = get_logger(__name__)

_FILTER_FIELDS: List[Tuple[str, str, str]] = [
    ("supermarket_name", "Supermarket", "Select which supermarkets to include."),
    ("branch", "Branch", "Filter by physical branch identifier."),
    ("city", "City", "Restrict to specific cities."),
    ("product_line", "Product Line", "Compare only selected product categories."),
    ("payment", "Payment Method", "Filter by tender type."),
    ("customer_type", "Customer Type", "Member vs Normal customers."),
    ("gender", "Gender", "Filter by customer gender."),
]


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Render sidebar filters and return the subset of ``df`` that matches.

    All filters default to "everything selected" so the dashboard is useful
    out of the box. A date range filter is always rendered last.
    """
    st.sidebar.header("Filters")
    st.sidebar.caption("Narrow down the data displayed across every tab.")

    working = df
    for col, label, help_text in _FILTER_FIELDS:
        if col not in working.columns:
            continue
        options = sorted(working[col].dropna().unique().tolist())
        if not options:
            continue
        selected = st.sidebar.multiselect(
            label, options, default=options, key=f"flt_{col}", help=help_text
        )
        working = working[working[col].isin(selected)]

    if "sale_date" in working.columns and not working["sale_date"].dropna().empty:
        min_date = working["sale_date"].min().date()
        max_date = working["sale_date"].max().date()

        selected_dates = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Limit results to a specific date window.",
        )

        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            working = working[
                (working["sale_date"].dt.date >= start_date)
                & (working["sale_date"].dt.date <= end_date)
            ]

    logger.info("Filters applied. Rows remaining: %d", len(working))
    return working.copy()
