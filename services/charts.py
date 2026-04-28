"""
Chart service.

Every Plotly figure used by the dashboard is built here. Centralising chart
construction keeps styling consistent, makes unit testing easier, and stops
the Streamlit page from drowning in chart-formatting code.

Each function takes already-aggregated / filtered data and returns a
``plotly.graph_objects.Figure``.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.settings import CHART_TEMPLATE, COLOR_PALETTE, DAY_ORDER


# ---------------------------------------------------------------------------
# Shared styling helper
# ---------------------------------------------------------------------------


def _style(fig: go.Figure, *, xaxis: str = "", yaxis: str = "",
           show_legend: bool = True) -> go.Figure:
    """Apply the dashboard-wide Plotly template."""
    fig.update_layout(
        template=CHART_TEMPLATE,
        xaxis_title=xaxis,
        yaxis_title=yaxis,
        showlegend=show_legend,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
# Comparison charts
# ---------------------------------------------------------------------------


def chart_revenue_by_supermarket(df: pd.DataFrame) -> go.Figure:
    data = (
        df.groupby("supermarket_name", as_index=False)["total"]
        .sum()
        .sort_values("total", ascending=False)
    )
    fig = px.bar(
        data, x="supermarket_name", y="total",
        color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        text_auto=".2s",
        title="Revenue by Supermarket",
    )
    return _style(fig, xaxis="Supermarket", yaxis="Revenue (£)", show_legend=False)


def chart_avg_basket(df: pd.DataFrame) -> go.Figure:
    data = (
        df.groupby("supermarket_name", as_index=False)["total"]
        .mean()
        .sort_values("total", ascending=False)
    )
    fig = px.bar(
        data, x="supermarket_name", y="total",
        color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        text_auto=".2f",
        title="Average Basket by Supermarket",
    )
    return _style(fig, xaxis="Supermarket", yaxis="Average Basket (£)", show_legend=False)


def chart_monthly_revenue(df: pd.DataFrame) -> go.Figure:
    data = (
        df.groupby(["supermarket_name", "month_num", "month"], as_index=False)["total"]
        .sum()
        .sort_values(["month_num", "supermarket_name"])
    )
    fig = px.line(
        data, x="month", y="total", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        markers=True,
        title="Monthly Revenue Comparison",
    )
    return _style(fig, xaxis="Month", yaxis="Revenue (£)")


def chart_product_line_revenue(df: pd.DataFrame) -> go.Figure:
    data = df.groupby(["supermarket_name", "product_line"], as_index=False)["total"].sum()
    fig = px.bar(
        data, x="product_line", y="total", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        barmode="group",
        title="Product Line Revenue Comparison",
    )
    return _style(fig, xaxis="Product Line", yaxis="Revenue (£)")


def chart_day_of_week(df: pd.DataFrame) -> go.Figure:
    data = df.groupby(["supermarket_name", "day_name"], as_index=False)["total"].sum()
    data["day_name"] = pd.Categorical(data["day_name"], categories=DAY_ORDER, ordered=True)
    data = data.sort_values("day_name")
    fig = px.bar(
        data, x="day_name", y="total", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        barmode="group",
        title="Revenue by Day of Week",
    )
    return _style(fig, xaxis="Day", yaxis="Revenue (£)")


def chart_payment_methods(df: pd.DataFrame) -> go.Figure:
    data = (
        df.groupby(["supermarket_name", "payment"], as_index=False)["invoice_id"]
        .count()
        .rename(columns={"invoice_id": "usage_count"})
    )
    fig = px.bar(
        data, x="payment", y="usage_count", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        barmode="group",
        title="Payment Method Usage Comparison",
    )
    return _style(fig, xaxis="Payment Method", yaxis="Usage Count")


def chart_customer_type(df: pd.DataFrame) -> go.Figure:
    data = df.groupby(["supermarket_name", "customer_type"], as_index=False)["total"].sum()
    fig = px.bar(
        data, x="customer_type", y="total", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        barmode="group",
        title="Customer Type Revenue Comparison",
    )
    return _style(fig, xaxis="Customer Type", yaxis="Revenue (£)")


def chart_rating_by_product(df: pd.DataFrame) -> go.Figure:
    data = df.groupby(["supermarket_name", "product_line"], as_index=False)["rating"].mean()
    fig = px.line(
        data, x="product_line", y="rating", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        markers=True,
        title="Average Rating by Product Line",
    )
    return _style(fig, xaxis="Product Line", yaxis="Average Rating")


# ---------------------------------------------------------------------------
# Market share / gap
# ---------------------------------------------------------------------------


def chart_market_share(df: pd.DataFrame) -> go.Figure:
    data = df.groupby("supermarket_name", as_index=False)["total"].sum()
    fig = px.pie(
        data, values="total", names="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        title="Revenue Share by Supermarket",
    )
    return _style(fig)


def chart_revenue_gap(benchmark: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        benchmark, x="supermarket_name", y="revenue_gap_to_leader",
        color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        title="Revenue Gap to Leader",
    )
    return _style(fig, xaxis="Supermarket", yaxis="Gap (£)", show_legend=False)


# ---------------------------------------------------------------------------
# Extras
# ---------------------------------------------------------------------------


def chart_high_value(df: pd.DataFrame) -> go.Figure:
    threshold = df["total"].quantile(0.95)
    hv = (
        df[df["total"] > threshold]
        .groupby("supermarket_name", as_index=False)["invoice_id"]
        .count()
        .rename(columns={"invoice_id": "high_value_transactions"})
    )
    fig = px.bar(
        hv, x="supermarket_name", y="high_value_transactions",
        color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        title=f"High-Value Transactions (> £{threshold:,.2f})",
    )
    return _style(fig, xaxis="Supermarket", yaxis="Count", show_legend=False)


def chart_unit_price_box(df: pd.DataFrame) -> go.Figure:
    fig = px.box(
        df, x="supermarket_name", y="unit_price", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        title="Unit Price Distribution by Supermarket",
    )
    return _style(fig, xaxis="Supermarket", yaxis="Unit Price (£)", show_legend=False)


# ---------------------------------------------------------------------------
# Forecasting / anomalies / margin / cohort
# ---------------------------------------------------------------------------


def chart_forecast(forecast_df: pd.DataFrame) -> go.Figure:
    """
    Plot historical monthly revenue + forecast band as dashed segments.
    Expects the dataframe produced by ``analytics.forecast_monthly_revenue``.
    """
    if forecast_df.empty:
        return _style(go.Figure(), xaxis="Period", yaxis="Revenue (£)")

    fig = go.Figure()

    for i, (market, group) in enumerate(forecast_df.groupby("supermarket_name")):
        colour = COLOR_PALETTE[i % len(COLOR_PALETTE)]
        history = group[~group["is_forecast"]]
        future = group[group["is_forecast"]]

        fig.add_trace(go.Scatter(
            x=history["period"], y=history["total"],
            mode="lines+markers", name=f"{market} (actual)",
            line=dict(color=colour),
        ))

        if not future.empty:
            # Bridge the last actual point with the first forecast so the line
            # is visually continuous.
            if not history.empty:
                bridge_x = [history["period"].iloc[-1], future["period"].iloc[0]]
                bridge_y = [history["total"].iloc[-1], future["total"].iloc[0]]
                fig.add_trace(go.Scatter(
                    x=bridge_x, y=bridge_y, mode="lines",
                    line=dict(color=colour, dash="dot"), showlegend=False,
                ))

            fig.add_trace(go.Scatter(
                x=future["period"], y=future["total"],
                mode="lines+markers", name=f"{market} (forecast)",
                line=dict(color=colour, dash="dash"),
            ))

    fig.update_layout(title="Monthly Revenue: History + Forecast")
    return _style(fig, xaxis="Period", yaxis="Revenue (£)")


def chart_anomalies(df: pd.DataFrame, anomalies: pd.DataFrame) -> go.Figure:
    """Scatter of transactions with anomalies highlighted."""
    if df.empty:
        return _style(go.Figure())

    fig = px.scatter(
        df, x="sale_date", y="total", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        opacity=0.35,
        title="Transactions Over Time (anomalies highlighted)",
    )

    if not anomalies.empty:
        fig.add_trace(go.Scatter(
            x=anomalies["sale_date"], y=anomalies["total"],
            mode="markers",
            marker=dict(symbol="x", size=11, color="red", line=dict(width=1)),
            name="Anomaly",
            hovertext=anomalies.get("anomaly_reason", pd.Series([], dtype=str)),
        ))

    return _style(fig, xaxis="Date", yaxis="Transaction Total (£)")


def chart_profit_margin(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="product_line", y="margin_pct", color="supermarket_name",
        color_discrete_sequence=COLOR_PALETTE,
        barmode="group",
        title="Profit Margin (%) by Product Line",
    )
    return _style(fig, xaxis="Product Line", yaxis="Margin (%)")


def chart_cohort_heatmap(matrix: pd.DataFrame) -> go.Figure:
    """Render the cohort matrix from ``analytics.cohort_analysis`` as a heatmap."""
    if matrix.empty:
        return _style(go.Figure(), xaxis="Month", yaxis="Cohort")

    fig = go.Figure(data=go.Heatmap(
        z=matrix.values,
        x=list(matrix.columns),
        y=list(matrix.index),
        colorscale="Blues",
        colorbar=dict(title="Revenue (£)"),
        hovertemplate="Cohort=%{y}<br>Month=%{x}<br>Revenue=£%{z:,.0f}<extra></extra>",
    ))
    fig.update_layout(title="Customer Cohort Revenue Heatmap")
    return _style(fig, xaxis="Month", yaxis="Cohort", show_legend=False)
