-- ---------------------------------------------------------------------------
-- Advanced analytics queries.
-- Showcases CTEs, window functions, and multi-level aggregations.
-- ---------------------------------------------------------------------------

-- 1. Running monthly revenue with MoM % change per supermarket.
WITH monthly AS (
    SELECT
        supermarket_name,
        SUBSTR(sale_date, 1, 7) AS year_month,
        SUM(total) AS revenue
    FROM sales
    GROUP BY supermarket_name, year_month
)
SELECT
    supermarket_name,
    year_month,
    ROUND(revenue, 2) AS revenue,
    ROUND(LAG(revenue) OVER (PARTITION BY supermarket_name ORDER BY year_month), 2)
        AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (PARTITION BY supermarket_name ORDER BY year_month))
        / NULLIF(LAG(revenue) OVER (PARTITION BY supermarket_name ORDER BY year_month), 0),
        2
    ) AS mom_change_pct
FROM monthly
ORDER BY supermarket_name, year_month;

-- 2. Top 3 product lines per supermarket by revenue.
WITH ranked AS (
    SELECT
        supermarket_name,
        product_line,
        SUM(total) AS revenue,
        RANK() OVER (PARTITION BY supermarket_name ORDER BY SUM(total) DESC) AS rnk
    FROM sales
    GROUP BY supermarket_name, product_line
)
SELECT supermarket_name, product_line, ROUND(revenue, 2) AS revenue
FROM ranked
WHERE rnk <= 3
ORDER BY supermarket_name, rnk;

-- 3. Profit margin by product line + supermarket.
SELECT
    supermarket_name,
    product_line,
    ROUND(SUM(total), 2)                                AS revenue,
    ROUND(SUM(gross_income), 2)                         AS gross_income,
    ROUND(100.0 * SUM(gross_income) / NULLIF(SUM(total), 0), 2) AS margin_pct
FROM sales
GROUP BY supermarket_name, product_line
ORDER BY supermarket_name, margin_pct DESC;

-- 4. Revenue share (% of market) per supermarket.
WITH totals AS (
    SELECT supermarket_name, SUM(total) AS revenue FROM sales GROUP BY supermarket_name
)
SELECT
    supermarket_name,
    ROUND(revenue, 2)                                         AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)          AS market_share_pct
FROM totals
ORDER BY revenue DESC;

-- 5. Hour-of-day heatmap data per supermarket.
SELECT
    supermarket_name,
    CAST(SUBSTR(sale_time, 1, 2) AS INTEGER) AS hour,
    ROUND(SUM(total), 2) AS revenue,
    COUNT(*)             AS transactions
FROM sales
GROUP BY supermarket_name, hour
ORDER BY supermarket_name, hour;

-- 6. Outlier transactions (approx Tukey fences per supermarket).
WITH per_market AS (
    SELECT
        supermarket_name,
        total,
        PERCENT_RANK() OVER (PARTITION BY supermarket_name ORDER BY total) AS pr
    FROM sales
),
bounds AS (
    SELECT
        supermarket_name,
        MIN(CASE WHEN pr >= 0.25 THEN total END) AS q1,
        MIN(CASE WHEN pr >= 0.75 THEN total END) AS q3
    FROM per_market
    GROUP BY supermarket_name
)
SELECT
    s.supermarket_name,
    s.invoice_id,
    s.sale_date,
    s.product_line,
    ROUND(s.total, 2) AS total
FROM sales s
JOIN bounds b USING (supermarket_name)
WHERE s.total > b.q3 + 1.5 * (b.q3 - b.q1)
   OR s.total < b.q1 - 1.5 * (b.q3 - b.q1)
ORDER BY s.supermarket_name, s.total DESC;

-- 7. Customer-type cohort matrix (revenue per type per month).
SELECT
    customer_type,
    SUBSTR(sale_date, 1, 7) AS year_month,
    ROUND(SUM(total), 2) AS revenue
FROM sales
GROUP BY customer_type, year_month
ORDER BY customer_type, year_month;
