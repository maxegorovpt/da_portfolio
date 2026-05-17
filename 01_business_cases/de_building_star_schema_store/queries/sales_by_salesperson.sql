SELECT
    sp.name AS salesperson_name,
    SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_salesperson sp ON f.salesperson_id = sp.salesperson_id
GROUP BY sp.name
ORDER BY revenue DESC;