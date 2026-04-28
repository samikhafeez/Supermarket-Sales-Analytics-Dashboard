"""
Supermarket Sales Analytics Dashboard - Streamlit entry point.

This file is intentionally thin: it wires services/utils/config together and
handles presentation only. All business logic lives under ``services/``.

Run locally:
    streamlit run app/dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make sibling packages importable when Streamlit runs this file directly.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import streamlit as st

from config.settings import DB_PATH
from services.analytics import (
    benchmark_summary,
    cohort_analysis,
    compute_kpis,
    detect_anomalies,
    forecast_monthly_revenue,
    profit_margin_by_category,
)
from services.charts import (
    chart_anomalies,
    chart_avg_basket,
    chart_cohort_heatmap,
    chart_customer_type,
    chart_day_of_week,
    chart_forecast,
    chart_high_value,
    chart_market_share,
    chart_monthly_revenue,
    chart_payment_methods,
    chart_product_line_revenue,
    chart_profit_margin,
    chart_rating_by_product,
    chart_revenue_by_supermarket,
    chart_revenue_gap,
    chart_unit_price_box,
)
from services.data_loader import load_from_database, load_from_uploads, run_sql
from services.insights import (
    as_markdown,
    generate_executive_summary,
    generate_insights,
)
from utils.filters import apply_filters
from utils.formatting import format_currency, format_number, format_percentage
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Supermarket Sales Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Supermarket Sales Analytics & Multi-Market Comparison")
st.caption(
    "Production-grade analytics dashboard featuring KPI tracking, forecasting, "
    "anomaly detection, cohort analysis, and auto-generated insights."
)


# ---------------------------------------------------------------------------
# Data source selection
# ---------------------------------------------------------------------------


def _load_data() -> pd.DataFrame:
    st.sidebar.header("Data Source")
    data_source = st.sidebar.radio(
        "Choose source",
        ["Built-in synthetic datasets", "Upload my own CSV files"],
        help=(
            "Built-in uses the three pre-loaded synthetic datasets. "
            "Upload mode lets you compare any CSVs that follow the supermarket "
            "sales schema."
        ),
    )

    if data_source == "Built-in synthetic datasets":
        try:
            return load_from_database()
        except FileNotFoundError as exc:
            st.error(
                f"{exc}\n\nBuild the database with:\n\n"
                f"```bash\npython -m services.data_loader\n```"
            )
            st.stop()
        except Exception as exc:  # noqa: BLE001 - surface any read error to UI
            logger.exception("Failed to load database")
            st.error(f"Could not load database: {exc}")
            st.stop()

    uploaded = st.sidebar.file_uploader(
        "Upload 2+ CSV files", type=["csv"], accept_multiple_files=True,
        help="Each file is treated as a separate supermarket for comparison.",
    )
    if not uploaded or len(uploaded) < 2:
        st.info("Upload at least two CSV files to begin comparison.")
        st.stop()

    payloads = [(f.name, f.getvalue()) for f in uploaded]
    try:
        return load_from_uploads(payloads)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()


data_source_mode = st.sidebar.empty()  # placeholder; real selector is inside _load_data
raw_df = _load_data()
filtered_df = apply_filters(raw_df)

if filtered_df.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

kpis = compute_kpis(filtered_df)
benchmark = benchmark_summary(filtered_df)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_overview, tab_comparison, tab_insights, tab_forecast, tab_sql = st.tabs([
    "Overview", "Comparison", "Insights", "Forecasting", "SQL Explorer",
])


# --- Overview ---------------------------------------------------------------
with tab_overview:
    st.subheader("Headline KPIs")
    st.caption("Aggregated across every supermarket in the current selection.")

    k1, k2, k3, k4 = st.columns(4)
    k5, k6, k7, k8 = st.columns(4)
    k1.metric("Total Revenue", format_currency(kpis.revenue),
              help="Sum of transaction totals.")
    k2.metric("Transactions", format_number(kpis.transactions),
              help="Number of invoices in the current selection.")
    k3.metric("Average Basket", format_currency(kpis.avg_basket),
              help="Mean transaction value.")
    k4.metric("Average Rating", f"{kpis.avg_rating:.2f}",
              help="Mean customer satisfaction score (0-10).")
    k5.metric("Quantity Sold", format_number(kpis.total_quantity),
              help="Total units sold.")
    k6.metric("Supermarkets", str(kpis.supermarket_count),
              help="Distinct supermarkets in the current selection.")
    k7.metric("Top Product Line", kpis.top_product_line)
    k8.metric("Top Payment Method", kpis.top_payment)

    st.divider()
    st.subheader("Per-Supermarket Snapshot")
    st.caption(
        "Ranked by revenue. The gap-to-leader column shows how far each "
        "competitor trails the market leader."
    )
    display_cols = [
        "supermarket_name", "revenue", "market_share_pct", "transactions",
        "avg_basket", "gross_income", "profit_margin_pct", "avg_rating",
        "quantity_sold", "revenue_gap_to_leader",
    ]
    st.dataframe(
        benchmark[display_cols].rename(columns={
            "supermarket_name": "Supermarket",
            "revenue": "Revenue (£)",
            "market_share_pct": "Share (%)",
            "transactions": "Transactions",
            "avg_basket": "Avg Basket (£)",
            "gross_income": "Gross Income (£)",
            "profit_margin_pct": "Margin (%)",
            "avg_rating": "Avg Rating",
            "quantity_sold": "Units",
            "revenue_gap_to_leader": "Gap to Leader (£)",
        }),
        use_container_width=True,
        hide_index=True,
    )


# --- Comparison -------------------------------------------------------------
with tab_comparison:
    st.subheader("Revenue & Basket Comparison")
    c1, c2 = st.columns(2)
    c1.plotly_chart(chart_revenue_by_supermarket(filtered_df),
                    use_container_width=True)
    c2.plotly_chart(chart_avg_basket(filtered_df), use_container_width=True)

    c3, c4 = st.columns(2)
    c3.plotly_chart(chart_monthly_revenue(filtered_df), use_container_width=True)
    c4.plotly_chart(chart_product_line_revenue(filtered_df),
                    use_container_width=True)

    st.divider()
    st.subheader("Market Share & Gap Analysis")
    g1, g2 = st.columns(2)
    g1.plotly_chart(chart_market_share(filtered_df), use_container_width=True)
    g2.plotly_chart(chart_revenue_gap(benchmark), use_container_width=True)

    st.divider()
    st.subheader("Operational & Customer View")
    o1, o2 = st.columns(2)
    o1.plotly_chart(chart_day_of_week(filtered_df), use_container_width=True)
    o2.plotly_chart(chart_payment_methods(filtered_df), use_container_width=True)

    o3, o4 = st.columns(2)
    o3.plotly_chart(chart_customer_type(filtered_df), use_container_width=True)
    o4.plotly_chart(chart_rating_by_product(filtered_df),
                    use_container_width=True)

    st.divider()
    st.subheader("Distributional Extras")
    e1, e2 = st.columns(2)
    e1.plotly_chart(chart_high_value(filtered_df), use_container_width=True)
    e2.plotly_chart(chart_unit_price_box(filtered_df), use_container_width=True)


# --- Insights ---------------------------------------------------------------
with tab_insights:
    st.subheader("Executive Summary")
    st.caption(
        "Automatically generated from the current selection. The summary is "
        "rule-based and deterministic."
    )
    st.markdown(generate_executive_summary(filtered_df, benchmark))

    st.divider()
    st.subheader("Key Insights")
    st.markdown(as_markdown(generate_insights(filtered_df, benchmark)))

    st.divider()
    st.subheader("Profit Margin by Category")
    margin_df = profit_margin_by_category(filtered_df)
    st.caption(
        "Margin = gross income / revenue. Higher margin products are the most "
        "profitable per pound of revenue."
    )
    st.plotly_chart(chart_profit_margin(margin_df), use_container_width=True)
    st.dataframe(margin_df.rename(columns={
        "supermarket_name": "Supermarket",
        "product_line": "Product Line",
        "revenue": "Revenue (£)",
        "gross_income": "Gross Income (£)",
        "cogs": "COGS (£)",
        "margin_pct": "Margin (%)",
    }), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Anomaly Detection")
    method = st.radio(
        "Detection method",
        ["iqr", "zscore"],
        horizontal=True,
        help=(
            "IQR flags transactions outside 1.5× the inter-quartile range. "
            "Z-score flags transactions more than 3 standard deviations from "
            "the mean. Both run per supermarket."
        ),
    )
    anomalies = detect_anomalies(filtered_df, method=method)
    st.plotly_chart(
        chart_anomalies(filtered_df, anomalies), use_container_width=True
    )
    if not anomalies.empty:
        st.caption(f"{len(anomalies)} anomalous transactions detected.")
        st.dataframe(
            anomalies[[
                "supermarket_name", "invoice_id", "sale_date", "product_line",
                "total", "anomaly_reason",
            ]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No anomalies detected in the current selection.")

    st.divider()
    st.subheader("Cohort Analysis")
    st.caption(
        "Revenue contribution of each customer type across months. Use it to "
        "spot shifts in member vs casual-customer behaviour over time."
    )
    cohort = cohort_analysis(filtered_df)
    st.plotly_chart(chart_cohort_heatmap(cohort), use_container_width=True)
    if not cohort.empty:
        st.dataframe(cohort, use_container_width=True)


# --- Forecasting ------------------------------------------------------------
with tab_forecast:
    st.subheader("Monthly Revenue Forecast")
    st.caption(
        "Linear-regression forecast per supermarket. Actual data is solid; "
        "predicted values are dashed. Tweak the horizon to project further out."
    )

    horizon = st.slider(
        "Forecast horizon (months)", min_value=1, max_value=12, value=3,
        help="How many months ahead to project.",
    )
    forecast_df = forecast_monthly_revenue(filtered_df, horizon_months=horizon)
    st.plotly_chart(chart_forecast(forecast_df), use_container_width=True)

    if not forecast_df.empty:
        forecast_only = forecast_df[forecast_df["is_forecast"]].copy()
        if not forecast_only.empty:
            forecast_only["period"] = forecast_only["period"].dt.strftime("%Y-%m")
            st.dataframe(
                forecast_only.rename(columns={
                    "supermarket_name": "Supermarket",
                    "period": "Period",
                    "total": "Forecast Revenue (£)",
                })[["Supermarket", "Period", "Forecast Revenue (£)"]],
                use_container_width=True, hide_index=True,
            )


# --- SQL Explorer -----------------------------------------------------------
with tab_sql:
    st.subheader("SQL Query Explorer")
    st.caption("Run saved queries against the built-in SQLite database.")

    saved_queries = {
        "Branch Revenue": """
            SELECT supermarket_name, branch, ROUND(SUM(total), 2) AS revenue
            FROM sales
            GROUP BY supermarket_name, branch
            ORDER BY revenue DESC;
        """,
        "Top Product Lines by Market (window function)": """
            WITH ranked AS (
                SELECT supermarket_name, product_line,
                       SUM(total) AS revenue,
                       RANK() OVER (PARTITION BY supermarket_name
                                    ORDER BY SUM(total) DESC) AS rnk
                FROM sales
                GROUP BY supermarket_name, product_line
            )
            SELECT supermarket_name, product_line, ROUND(revenue, 2) AS revenue
            FROM ranked WHERE rnk <= 3
            ORDER BY supermarket_name, rnk;
        """,
        "Month-over-Month Change": """
            WITH monthly AS (
                SELECT supermarket_name,
                       SUBSTR(sale_date, 1, 7) AS ym,
                       SUM(total) AS revenue
                FROM sales GROUP BY supermarket_name, ym
            )
            SELECT supermarket_name, ym, ROUND(revenue, 2) AS revenue,
                   ROUND(100.0 * (revenue - LAG(revenue) OVER (
                        PARTITION BY supermarket_name ORDER BY ym))
                         / NULLIF(LAG(revenue) OVER (
                                PARTITION BY supermarket_name ORDER BY ym), 0),
                         2) AS mom_pct
            FROM monthly ORDER BY supermarket_name, ym;
        """,
        "Revenue Share (%)": """
            WITH t AS (
                SELECT supermarket_name, SUM(total) AS revenue
                FROM sales GROUP BY supermarket_name
            )
            SELECT supermarket_name, ROUND(revenue, 2) AS revenue,
                   ROUND(100.0 * revenue / SUM(revenue) OVER (), 2) AS market_share_pct
            FROM t ORDER BY revenue DESC;
        """,
    }

    selected_name = st.selectbox("Saved queries", list(saved_queries.keys()))
    query = saved_queries[selected_name].strip()
    st.code(query, language="sql")

    if DB_PATH.exists():
        try:
            result = run_sql(query)
            st.dataframe(result, use_container_width=True, hide_index=True)
        except Exception as exc:  # noqa: BLE001 - surface to UI
            logger.exception("SQL query failed")
            st.error(f"Query failed: {exc}")
    else:
        st.info(
            "SQL explorer is only available in built-in database mode. "
            "Upload mode operates on in-memory DataFrames."
        )


# ---------------------------------------------------------------------------
# Footer: data preview + downloads
# ---------------------------------------------------------------------------

st.divider()
with st.expander("Filtered Data Preview"):
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

col_a, col_b = st.columns(2)
col_a.download_button(
    "Download Filtered Data (CSV)",
    data=filtered_df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_supermarket_comparison.csv",
    mime="text/csv",
)
col_b.download_button(
    "Download Benchmark Summary (CSV)",
    data=benchmark.to_csv(index=False).encode("utf-8"),
    file_name="benchmark_summary.csv",
    mime="text/csv",
)
