CREATE TABLE dwh.dim_date (
    date_key        INTEGER PRIMARY KEY,
    full_date       DATE NOT NULL UNIQUE,
    day_of_month    INTEGER NOT NULL,
    day_name        VARCHAR(10) NOT NULL,
    month_num       INTEGER NOT NULL,
    month_name      VARCHAR(10) NOT NULL,
    quarter_num     INTEGER NOT NULL,
    year_num        INTEGER NOT NULL,
    is_weekend      BOOLEAN NOT NULL
);