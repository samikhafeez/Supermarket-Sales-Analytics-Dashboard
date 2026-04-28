"""
Insights service.

Generates automatic, human-readable bullet points and an executive-summary
paragraph from aggregated data. The implementation is rule-based so it runs
offline, is deterministic, and incurs no API cost - but the function
signatures are designed so an LLM backend could be dropped in later.

Design goals:
- Every insight is grounded in an actual figure in the dataframe.
- Insights never hallucinate - if a comparison is not meaningful (single
  supermarket, zero revenue, etc) it is simply skipped.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from utils.formatting import format_currency, format_percentage
from utils.logger import get_logger

logger = get_logger(__name__)


def _pct_diff(a: float, b: float) -> float:
    """Return (a - b) / b * 100 with a zero-safe fallback."""
    if b == 0:
        return 0.0
    return (a - b) / b * 100


def generate_insights(df: pd.DataFrame, benchmark: pd.DataFrame) -> List[str]:
    """
    Produce a list of human-readable insight strings.

    ``benchmark`` is the output of ``analytics.benchmark_summary(df)``.
    """
    insights: List[str] = []

    if df.empty or benchmark.empty:
        return ["Not enough data to generate insights."]

    # 1. Revenue leader vs runner-up.
    if len(benchmark) >= 2:
        leader = benchmark.iloc[0]
        runner_up = benchmark.iloc[1]
        diff_pct = _pct_diff(leader["revenue"], runner_up["revenue"])
        insights.append(
            f"**{leader['supermarket_name']}** leads on revenue with "
            f"{format_currency(leader['revenue'])}, outperforming "
            f"**{runner_up['supermarket_name']}** by {format_percentage(diff_pct)}."
        )

    # 2. Highest profit margin.
    if "profit_margin_pct" in benchmark.columns:
        margin_leader = benchmark.sort_values("profit_margin_pct", ascending=False).iloc[0]
        insights.append(
            f"**{margin_leader['supermarket_name']}** has the strongest profit "
            f"margin at {format_percentage(margin_leader['profit_margin_pct'])}."
        )

    # 3. Best customer satisfaction.
    if "avg_rating" in benchmark.columns:
        rating_leader = benchmark.sort_values("avg_rating", ascending=False).iloc[0]
        insights.append(
            f"Customers rate **{rating_leader['supermarket_name']}** highest "
            f"with an average score of {rating_leader['avg_rating']:.2f} / 10."
        )

    # 4. Top-selling product line overall.
    top_product = (
        df.groupby("product_line")["total"].sum().sort_values(ascending=False).head(1)
    )
    if not top_product.empty:
        name = top_product.index[0]
        revenue = top_product.iloc[0]
        insights.append(
            f"The top-selling category overall is **{name}**, generating "
            f"{format_currency(revenue)} across all supermarkets."
        )

    # 5. Best trading day.
    if "day_name" in df.columns:
        top_day = df.groupby("day_name")["total"].sum().sort_values(ascending=False).head(1)
        if not top_day.empty:
            insights.append(
                f"**{top_day.index[0]}** is the strongest trading day with "
                f"{format_currency(top_day.iloc[0])} in total revenue."
            )

    # 6. Month-over-month movement.
    if "sale_date" in df.columns and df["sale_date"].notna().any():
        monthly = (
            df.dropna(subset=["sale_date"])
            .assign(period=lambda d: d["sale_date"].dt.to_period("M"))
            .groupby("period")["total"].sum().sort_index()
        )
        if len(monthly) >= 2:
            latest, previous = monthly.iloc[-1], monthly.iloc[-2]
            change = _pct_diff(latest, previous)
            direction = "up" if change >= 0 else "down"
            insights.append(
                f"Total revenue moved {direction} {format_percentage(abs(change))} "
                f"month-on-month ({format_currency(previous)} → {format_currency(latest)})."
            )

    # 7. Payment-method preference.
    if "payment" in df.columns:
        payment_share = df["payment"].value_counts(normalize=True)
        if not payment_share.empty:
            top_pay = payment_share.index[0]
            share_pct = payment_share.iloc[0] * 100
            insights.append(
                f"**{top_pay}** is the preferred payment method, used in "
                f"{format_percentage(share_pct)} of transactions."
            )

    # 8. Member vs normal customer basket size.
    if "customer_type" in df.columns:
        avg_basket = df.groupby("customer_type")["total"].mean()
        if {"Member", "Normal"}.issubset(avg_basket.index):
            member, normal = avg_basket["Member"], avg_basket["Normal"]
            diff = _pct_diff(member, normal)
            higher = "higher" if diff >= 0 else "lower"
            insights.append(
                f"Members spend {format_percentage(abs(diff))} {higher} per "
                f"transaction than Normal customers on average."
            )

    logger.info("Generated %d automatic insights", len(insights))
    return insights


def generate_executive_summary(df: pd.DataFrame, benchmark: pd.DataFrame) -> str:
    """Return a single-paragraph executive summary."""
    if df.empty or benchmark.empty:
        return "There is not enough data in the current selection to summarise."

    total_revenue = df["total"].sum()
    total_transactions = len(df)
    markets = benchmark["supermarket_name"].tolist()

    leader = benchmark.iloc[0]
    tail = "; ".join(
        f"{row['supermarket_name']} on {format_currency(row['revenue'])}"
        for _, row in benchmark.iloc[1:].iterrows()
    )

    summary = (
        f"Across {len(markets)} supermarkets ({', '.join(markets)}) the current "
        f"selection covers {format_currency(total_revenue)} of revenue from "
        f"{total_transactions:,} transactions. "
        f"The market leader is **{leader['supermarket_name']}** with "
        f"{format_currency(leader['revenue'])} "
        f"({format_percentage(leader.get('market_share_pct', 0))} share)"
    )
    if tail:
        summary += f", followed by {tail}."
    else:
        summary += "."
    return summary


def as_markdown(insights: List[str]) -> str:
    """Convenience: render a bullet list as Markdown."""
    if not insights:
        return "_No insights available._"
    return "\n".join(f"- {item}" for item in insights)
