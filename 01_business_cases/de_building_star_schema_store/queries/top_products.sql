SELECT
    p.name AS product_name,
    SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.name
ORDER BY revenue DESC;