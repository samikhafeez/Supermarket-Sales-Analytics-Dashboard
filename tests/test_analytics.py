"""
Smoke tests for the analytics service.

Run with:
    pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.analytics import (  # noqa: E402
    benchmark_summary,
    cohort_analysis,
    compute_kpis,
    detect_anomalies,
    forecast_monthly_revenue,
    profit_margin_by_category,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "invoice_id": [f"INV{i}" for i in range(n)],
        "branch": rng.choice(["A", "B", "C"], size=n),
        "city": rng.choice(["London", "Manchester", "Leeds"], size=n),
        "customer_type": rng.choice(["Member", "Normal"], size=n),
        "gender": rng.choice(["Male", "Female"], size=n),
        "product_line": rng.choice(["Food", "Drink", "Home"], size=n),
        "unit_price": rng.uniform(1, 100, size=n),
        "quantity": rng.integers(1, 10, size=n),
        "tax": rng.uniform(0, 10, size=n),
        "total": rng.uniform(5, 500, size=n),
        "sale_date": dates,
        "sale_time": pd.to_datetime(rng.choice(
            ["10:00:00", "12:00:00", "18:30:00"], size=n
        ), format="%H:%M:%S"),
        "payment": rng.choice(["Cash", "Credit card", "Ewallet"], size=n),
        "cogs": rng.uniform(1, 300, size=n),
        "gross_margin_percentage": np.full(n, 4.76),
        "gross_income": rng.uniform(0.5, 50, size=n),
        "rating": rng.uniform(4, 10, size=n),
        "supermarket_name": rng.choice(
            ["Supermarket A", "Supermarket B", "Supermarket C"], size=n
        ),
        "month": dates.month_name(),
        "month_num": dates.month,
        "day_name": dates.day_name(),
        "year": dates.year,
        "hour": 12,
    })


def test_compute_kpis(sample_df: pd.DataFrame) -> None:
    kpis = compute_kpis(sample_df)
    assert kpis.transactions == len(sample_df)
    assert kpis.revenue > 0
    assert kpis.supermarket_count >= 1


def test_benchmark_summary(sample_df: pd.DataFrame) -> None:
    summary = benchmark_summary(sample_df)
    assert not summary.empty
    # Rows ordered descending by revenue.
    assert summary["revenue"].is_monotonic_decreasing
    # Market share sums to ~100.
    assert pytest.approx(summary["market_share_pct"].sum(), rel=1e-2) == 100


def test_forecast_shape(sample_df: pd.DataFrame) -> None:
    out = forecast_monthly_revenue(sample_df, horizon_months=3)
    assert not out.empty
    assert {"supermarket_name", "period", "total", "is_forecast"} <= set(out.columns)
    # We expect forecast rows per supermarket.
    assert out["is_forecast"].sum() > 0


def test_detect_anomalies_returns_dataframe(sample_df: pd.DataFrame) -> None:
    # Inject an obvious outlier per market.
    spike = sample_df.copy()
    for market in spike["supermarket_name"].unique():
        idx = spike[spike["supermarket_name"] == market].index[0]
        spike.loc[idx, "total"] = 100_000.0
    anomalies = detect_anomalies(spike, method="iqr")
    assert not anomalies.empty
    assert "anomaly_reason" in anomalies.columns


def test_cohort_analysis(sample_df: pd.DataFrame) -> None:
    matrix = cohort_analysis(sample_df)
    assert not matrix.empty
    assert matrix.index.name == "customer_type"


def test_profit_margin(sample_df: pd.DataFrame) -> None:
    margin = profit_margin_by_category(sample_df)
    assert not margin.empty
    assert (margin["margin_pct"] >= 0).all()
