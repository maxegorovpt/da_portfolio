CREATE TABLE dim_salesperson (
    salesperson_id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT,
    region TEXT,
    hire_date DATE
);