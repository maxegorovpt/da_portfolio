CREATE TABLE dim_customer (
    customer_id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT,
    country TEXT,
    signup_date DATE
);