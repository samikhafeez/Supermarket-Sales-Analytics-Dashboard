"""
Analytics service.

Pure, side-effect-free functions that transform the canonical sales DataFrame
into KPIs, forecasts, anomaly flags, cohort tables, and profitability views.

Every function takes a DataFrame and returns a DataFrame / scalar / dict - no
Streamlit imports - so the logic is trivially unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KPIs:
    """Immutable KPI snapshot for a (possibly filtered) dataset."""

    revenue: float
    transactions: int
    avg_basket: float
    avg_rating: float
    total_quantity: int
    gross_income: float
    top_branch: str
    top_product_line: str
    top_payment: str
    supermarket_count: int


def _safe_mode(series: pd.Series) -> str:
    mode = series.dropna().mode()
    return str(mode.iloc[0]) if not mode.empty else "-"


def _safe_idxmax(series: pd.Series) -> str:
    return str(series.idxmax()) if not series.empty else "-"


def compute_kpis(df: pd.DataFrame) -> KPIs:
    """Aggregate headline KPIs for a filtered slice."""
    if df.empty:
        return KPIs(0.0, 0, 0.0, 0.0, 0, 0.0, "-", "-", "-", 0)

    return KPIs(
        revenue=float(df["total"].sum()),
        transactions=int(len(df)),
        avg_basket=float(df["total"].mean()),
        avg_rating=float(df["rating"].mean()) if "rating" in df else 0.0,
        total_quantity=int(df["quantity"].sum()),
        gross_income=float(df["gross_income"].sum())
        if "gross_income" in df else 0.0,
        top_branch=_safe_idxmax(df.groupby("branch")["total"].sum()),
        top_product_line=_safe_idxmax(df.groupby("product_line")["total"].sum()),
        top_payment=_safe_mode(df["payment"]),
        supermarket_count=int(df["supermarket_name"].nunique()),
    )


# ---------------------------------------------------------------------------
# Benchmark summary (per-market league table)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def benchmark_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return a per-supermarket league table suitable for `st.dataframe`."""
    if df.empty:
        return pd.DataFrame()

    summary = (
        df.groupby("supermarket_name", as_index=False)
        .agg(
            revenue=("total", "sum"),
            transactions=("invoice_id", "count"),
            avg_basket=("total", "mean"),
            gross_income=("gross_income", "sum"),
            avg_rating=("rating", "mean"),
            quantity_sold=("quantity", "sum"),
        )
        .sort_values("revenue", ascending=False)
        .reset_index(drop=True)
    )

    # Profit margin = gross_income / revenue (as %). Safe against div-by-zero.
    summary["profit_margin_pct"] = np.where(
        summary["revenue"] > 0,
        (summary["gross_income"] / summary["revenue"]) * 100,
        0.0,
    )

    # Market share.
    total_revenue = summary["revenue"].sum()
    summary["market_share_pct"] = np.where(
        total_revenue > 0,
        (summary["revenue"] / total_revenue) * 100,
        0.0,
    )

    # Gap to leader.
    leader = summary["revenue"].max()
    summary["revenue_gap_to_leader"] = (leader - summary["revenue"]).round(2)

    for col in ("revenue", "avg_basket", "gross_income", "avg_rating",
                "profit_margin_pct", "market_share_pct"):
        summary[col] = summary[col].round(2)

    return summary


# ---------------------------------------------------------------------------
# Forecasting (monthly revenue per supermarket)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Generating revenue forecasts...")
def forecast_monthly_revenue(
    df: pd.DataFrame, horizon_months: int = 3
) -> pd.DataFrame:
    """
    Forecast the next ``horizon_months`` of revenue per supermarket using a
    simple linear regression over monthly totals.

    The returned DataFrame contains both historical and forecast rows with an
    ``is_forecast`` flag so they can be plotted together.

    We deliberately avoid heavyweight libraries (Prophet, statsmodels) to keep
    the requirements minimal - linear regression over monthly aggregates is
    sufficient for a portfolio demonstration and is easily replaced.
    """
    from sklearn.linear_model import LinearRegression

    if df.empty or "sale_date" not in df.columns:
        return pd.DataFrame()

    monthly = (
        df.dropna(subset=["sale_date"])
        .assign(period=lambda d: d["sale_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["supermarket_name", "period"], as_index=False)["total"].sum()
        .sort_values(["supermarket_name", "period"])
    )

    results: List[pd.DataFrame] = []

    for market, group in monthly.groupby("supermarket_name"):
        group = group.sort_values("period").reset_index(drop=True)
        if len(group) < 2:
            group["is_forecast"] = False
            results.append(group)
            continue

        # Feature: months since the first observation.
        x = (
            (group["period"] - group["period"].min()).dt.days / 30
        ).to_numpy().reshape(-1, 1)
        y = group["total"].to_numpy()

        model = LinearRegression()
        model.fit(x, y)

        historical = group.copy()
        historical["is_forecast"] = False

        last_period = group["period"].max()
        future_periods = pd.date_range(
            start=last_period + pd.offsets.MonthBegin(1),
            periods=horizon_months,
            freq="MS",
        )
        future_x = (
            (future_periods - group["period"].min()).days / 30
        ).to_numpy().reshape(-1, 1)
        future_y = model.predict(future_x)

        # Clip negative forecasts to zero - revenue cannot be negative.
        future_y = np.clip(future_y, a_min=0, a_max=None)

        forecast = pd.DataFrame({
            "supermarket_name": market,
            "period": future_periods,
            "total": future_y,
            "is_forecast": True,
        })

        results.append(pd.concat([historical, forecast], ignore_index=True))

    if not results:
        return pd.DataFrame()

    combined = pd.concat(results, ignore_index=True)
    combined["total"] = combined["total"].round(2)
    return combined


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def detect_anomalies(
    df: pd.DataFrame, method: str = "iqr", contamination: float = 0.02
) -> pd.DataFrame:
    """
    Flag outlier transactions per supermarket.

    Args:
        method: "iqr" (Tukey fences) or "zscore" (mean ± 3σ).
        contamination: unused for IQR/z-score; retained for API parity.

    Returns:
        A subset of ``df`` limited to anomalous rows, with ``anomaly_reason``.
    """
    if df.empty:
        return pd.DataFrame()

    anomalies: List[pd.DataFrame] = []

    for market, group in df.groupby("supermarket_name"):
        totals = group["total"].dropna()
        if len(totals) < 5:
            continue

        if method == "zscore":
            mu, sigma = totals.mean(), totals.std(ddof=0)
            if sigma == 0 or np.isnan(sigma):
                continue
            mask = (group["total"] - mu).abs() > 3 * sigma
            reason = "z-score > 3"
        else:  # IQR
            q1, q3 = totals.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask = (group["total"] < lower) | (group["total"] > upper)
            reason = "outside 1.5 × IQR"

        flagged = group.loc[mask].copy()
        flagged["anomaly_reason"] = reason
        anomalies.append(flagged)

    if not anomalies:
        return pd.DataFrame()

    out = pd.concat(anomalies, ignore_index=True)
    logger.info("Anomaly detection flagged %d rows (method=%s)", len(out), method)
    return out.sort_values("total", ascending=False)


# ---------------------------------------------------------------------------
# Cohort analysis (month-of-first-visit vs activity over time)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def cohort_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a customer-type cohort matrix.

    Because the dataset does not include stable customer IDs, we use
    ``customer_type`` (Member vs Normal) as a proxy cohort dimension and
    compute revenue per month for each group. Rows = cohort, columns = months,
    values = revenue.

    This is a conservative but useful implementation; if real customer IDs
    become available later, swap the cohort key here.
    """
    if df.empty or "customer_type" not in df.columns:
        return pd.DataFrame()

    data = df.dropna(subset=["sale_date"]).copy()
    data["month"] = data["sale_date"].dt.to_period("M").astype(str)

    matrix = (
        data.groupby(["customer_type", "month"], as_index=False)["total"]
        .sum()
        .pivot(index="customer_type", columns="month", values="total")
        .fillna(0.0)
        .round(2)
    )
    return matrix


# ---------------------------------------------------------------------------
# Profit margin by category
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def profit_margin_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return revenue, gross income and derived margin per product line."""
    if df.empty:
        return pd.DataFrame()

    summary = (
        df.groupby(["supermarket_name", "product_line"], as_index=False)
        .agg(
            revenue=("total", "sum"),
            gross_income=("gross_income", "sum"),
            cogs=("cogs", "sum"),
        )
    )
    summary["margin_pct"] = np.where(
        summary["revenue"] > 0,
        (summary["gross_income"] / summary["revenue"]) * 100,
        0.0,
    )
    for col in ("revenue", "gross_income", "cogs", "margin_pct"):
        summary[col] = summary[col].round(2)
    return summary.sort_values(["supermarket_name", "margin_pct"], ascending=[True, False])


# ---------------------------------------------------------------------------
# Helpers reused by the dashboard
# ---------------------------------------------------------------------------


def top_bottom(
    df: pd.DataFrame, group_col: str, value_col: str = "total", n: int = 3
) -> Dict[str, pd.DataFrame]:
    """Return dict with ``top`` and ``bottom`` slices per supermarket."""
    if df.empty:
        return {"top": pd.DataFrame(), "bottom": pd.DataFrame()}

    agg = (
        df.groupby(["supermarket_name", group_col], as_index=False)[value_col]
        .sum()
        .sort_values(["supermarket_name", value_col], ascending=[True, False])
    )
    top = agg.groupby("supermarket_name").head(n)
    bottom = agg.groupby("supermarket_name").tail(n)
    return {"top": top, "bottom": bottom}
