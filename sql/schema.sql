-- ---------------------------------------------------------------------------
-- Canonical schema for the supermarket sales dataset.
-- ---------------------------------------------------------------------------
-- Notes:
--   * invoice_id is NOT globally unique across supermarkets in the source
--     CSVs, so the primary key is (supermarket_name, invoice_id).
--   * sale_date / sale_time are stored as ISO text for portability; the
--     Python layer converts to real datetimes after read.
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS sales;

CREATE TABLE sales (
    supermarket_name         TEXT    NOT NULL,
    invoice_id               TEXT    NOT NULL,
    branch                   TEXT,
    city                     TEXT,
    customer_type            TEXT,
    gender                   TEXT,
    product_line             TEXT,
    unit_price               REAL,
    quantity                 INTEGER,
    tax                      REAL,
    total                    REAL,
    sale_date                TEXT,   -- ISO date: YYYY-MM-DD
    sale_time                TEXT,   -- ISO time: HH:MM:SS
    payment                  TEXT,
    cogs                     REAL,
    gross_margin_percentage  REAL,
    gross_income             REAL,
    rating                   REAL,
    year                     INTEGER,
    month                    TEXT,
    month_num                INTEGER,
    day_name                 TEXT,
    hour                     INTEGER,
    PRIMARY KEY (supermarket_name, invoice_id)
);

-- Indexes to speed up the most common grouped queries.
CREATE INDEX IF NOT EXISTS idx_sales_market        ON sales(supermarket_name);
CREATE INDEX IF NOT EXISTS idx_sales_date          ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_product       ON sales(product_line);
CREATE INDEX IF NOT EXISTS idx_sales_city          ON sales(city);
CREATE INDEX IF NOT EXISTS idx_sales_market_date   ON sales(supermarket_name, sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_market_prod   ON sales(supermarket_name, product_line);

-- Convenience view: per-market, per-month aggregates, precomputed for
-- forecasting and trend queries.
DROP VIEW IF EXISTS v_monthly_revenue;

CREATE VIEW v_monthly_revenue AS
SELECT
    supermarket_name,
    SUBSTR(sale_date, 1, 7)         AS year_month,
    ROUND(SUM(total), 2)            AS revenue,
    ROUND(SUM(gross_income), 2)     AS gross_income,
    COUNT(*)                        AS transactions,
    ROUND(AVG(rating), 2)           AS avg_rating
FROM sales
GROUP BY supermarket_name, year_month;
