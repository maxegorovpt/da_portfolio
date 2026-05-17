# 📊 Sales Data Warehouse (PostgreSQL Star Schema)

## 🧭 Overview

This project implements a **dimensional data warehouse using a star schema in PostgreSQL**, designed to simulate a real-world retail analytics system.

It demonstrates:
- Data warehouse modeling
- Fact and dimension design
- SQL analytics
- Business intelligence readiness

### Project Folder Structure
```text
sales-data-warehouse/

├── README.md
├── erd/
│   └── schema.dbml
│
├── ddl/
│   ├── create_dim_customer.sql
│   ├── create_dim_product.sql
│   ├── create_dim_date.sql
│   ├── create_dim_store.sql
│   ├── create_dim_salesperson.sql
│   ├── create_dim_channel.sql
│   └── create_fact_sales.sql
│
└── queries/
    ├── revenue_over_time.sql
    ├── top_products.sql
    ├── customer_ltv.sql
    ├── sales_by_store.sql
    ├── sales_by_salesperson.sql
    └── sales_by_channel.sql
```
---

## 🎯 Business Problem

Companies need a structured way to analyze:

- Sales performance over time
- Product performance
- Customer value (CLV)
- Revenue trends

This warehouse enables fast, consistent reporting across all dimensions.

---

## 🏗️ Data Architecture

### ⭐ Star Schema

                dim_customer
                     |
dim_date —— fact_sales —— dim_product

---

## 📌 Data Model Design

### 🧾 Fact Table: fact_sales

**Grain:** One row per product per order (line item level)

| Column        | Description |
|--------------|-------------|
| sales_id     | Surrogate key |
| date_id      | Transaction date |
| customer_id  | Buyer reference |
| product_id   | Product sold |
| quantity     | Units sold |
| unit_price   | Price per unit |
| total_amount | Revenue |

---

### 👤 Dimension Tables

#### dim_customer
- customer_id (PK)
- name
- email
- country
- signup_date

#### dim_product
- product_id (PK)
- name
- category
- brand

#### dim_date
- date_id (PK)
- day, month, year
- weekday

---

## 🧱 Tech Stack

- PostgreSQL
- SQL (DDL + Analytics)
- Data Warehouse Modeling (Star Schema)
- Git/GitHub

---

## 📊 Example Queries

### Revenue Over Time
```sql
SELECT d.year, d.month,
       SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month
ORDER BY d.year, d.month;
```
---

### Top Products
```sql
SELECT p.name,
       SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.name
ORDER BY revenue DESC;
```
---

### Customer Lifetime Value
```sql
SELECT c.name,
       SUM(f.total_amount) AS lifetime_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.name
ORDER BY lifetime_value DESC;
```
---

## 🧠 Key Skills Demonstrated

- Dimensional modeling
- Star schema design
- SQL analytics
- Business intelligence thinking

---

## 🚀 Future Improvements

- dbt models
- ETL pipeline
- BI dashboard
- SCD Type 2 dimensions

for ER diagram I use https://dbdiagram.io/d
