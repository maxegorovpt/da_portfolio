SELECT
    c.name AS customer_name,
    SUM(f.total_amount) AS lifetime_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.name
ORDER BY lifetime_value DESC;