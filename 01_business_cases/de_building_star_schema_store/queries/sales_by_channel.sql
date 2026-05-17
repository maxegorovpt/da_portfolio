SELECT
    ch.channel_name,
    SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_channel ch ON f.channel_id = ch.channel_id
GROUP BY ch.channel_name
ORDER BY revenue DESC;