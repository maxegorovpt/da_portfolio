CREATE TABLE fact_sales (
    sales_id SERIAL PRIMARY KEY,

    date_id DATE REFERENCES dim_date(date_id),
    customer_id INT REFERENCES dim_customer(customer_id),
    product_id INT REFERENCES dim_product(product_id),

    store_id INT REFERENCES dim_store(store_id),
    salesperson_id INT REFERENCES dim_salesperson(salesperson_id),
    channel_id INT REFERENCES dim_channel(channel_id),

    quantity INT,
    unit_price NUMERIC(10,2),
    total_amount NUMERIC(10,2)
);