-- 1. Total revenue by branch
SELECT branch, ROUND(SUM(total), 2) AS revenue
FROM sales
GROUP BY branch
ORDER BY revenue DESC;

-- 2. Total revenue by city
SELECT city, ROUND(SUM(total), 2) AS revenue
FROM sales
GROUP BY city
ORDER BY revenue DESC;

-- 3. Top product lines by revenue
SELECT product_line, ROUND(SUM(total), 2) AS revenue
FROM sales
GROUP BY product_line
ORDER BY revenue DESC;

-- 4. Average customer rating by branch
SELECT branch, ROUND(AVG(rating), 2) AS avg_rating
FROM sales
GROUP BY branch
ORDER BY avg_rating DESC;

-- 5. Most used payment method
SELECT payment, COUNT(*) AS usage_count
FROM sales
GROUP BY payment
ORDER BY usage_count DESC;

-- 6. Average basket value by customer type
SELECT customer_type, ROUND(AVG(total), 2) AS avg_basket_value
FROM sales
GROUP BY customer_type
ORDER BY avg_basket_value DESC;

-- 7. Quantity sold by product line
SELECT product_line, SUM(quantity) AS total_quantity
FROM sales
GROUP BY product_line
ORDER BY total_quantity DESC;

-- 8. Revenue by gender
SELECT gender, ROUND(SUM(total), 2) AS revenue
FROM sales
GROUP BY gender
ORDER BY revenue DESC;

-- 9. Gross income by branch
SELECT branch, ROUND(SUM(gross_income), 2) AS total_gross_income
FROM sales
GROUP BY branch
ORDER BY total_gross_income DESC;

-- 10. Sales count by hour
SELECT SUBSTR(sale_time, 1, 2) AS hour, COUNT(*) AS sales_count
FROM sales
GROUP BY hour
ORDER BY hour;