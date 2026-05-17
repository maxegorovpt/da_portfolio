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
- Store performance
- Salesperson contribution
- Sales by channel

This warehouse enables fast, consistent reporting across all business dimensions.

---

## 🏗️ Data Architecture

### ⭐ Star Schema

```text
                    dim_customer
                         |
                    dim_product
                         |
dim_date —— dim_store —— fact_sales —— dim_salesperson
                         |
                    dim_channel
```

The `fact_sales` table sits at the center of the model and connects to six dimension tables: `dim_date`, `dim_customer`, `dim_product`, `dim_store`, `dim_salesperson`, and `dim_channel`.

---

## 📌 Data Model Design

### 🧾 Fact Table: fact_sales

**Grain:** One row per product per order (line item level)

This table stores measurable sales events and links each transaction to the related date, customer, product, store, salesperson, and sales channel.

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
- day
- month
- year
- weekday

#### dim_store
- store_id (PK)
- store_name
- city
- country
- store_type

#### dim_salesperson
- salesperson_id (PK)
- name
- email
- region
- hire_date

#### dim_channel
- channel_id (PK)
- channel_name

---

## 🧱 Tech Stack

- PostgreSQL
- SQL (DDL + Analytics)
- Data Warehouse Modeling (Star Schema)
- Git/GitHub
- dbdiagram.io

---

## 🧠 Key Skills Demonstrated

- Dimensional modeling
- Star schema design
- SQL analytics
- Business intelligence thinking
- Fact and dimension relationship design

---

## 🚀 Future Improvements

- dbt models
- ETL pipeline
- BI dashboard
- SCD Type 2 dimensions

---

## 🔗 ER Diagram

For the ER diagram, this project uses [dbdiagram.io](https://dbdiagram.io/d).
