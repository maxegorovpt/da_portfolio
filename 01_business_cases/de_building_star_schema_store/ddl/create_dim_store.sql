CREATE TABLE dim_store (
    store_id SERIAL PRIMARY KEY,
    store_name TEXT,
    city TEXT,
    country TEXT,
    store_type TEXT  -- e.g. physical, online hub, franchise
);