SELECT
    s.store_name,
    SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.store_name
ORDER BY revenue DESC;