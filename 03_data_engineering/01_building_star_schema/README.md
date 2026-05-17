# Building a Simple Sales Data Warehouse Star Schema

This project demonstrates how to design and build a small retail sales data warehouse from scratch in PostgreSQL using a classic star schema model.

The solution organizes transactional sales data into one central fact table and several surrounding dimension tables so that analytical queries stay simple and performant.

## Project goal

The objective is to model store sales data for reporting use cases such as:

- Revenue by month
- Sales by product category
- Customer segmentation
- Store performance

The project uses PostgreSQL as the database platform and places warehouse objects inside a dedicated schema.

## Folder structure

```text
01_building_star_schema/
├── README.md
├── ddl/
│   └── star_schema.sql
├── erd/
│   └── star_schema.dbml
├── sample_data/
│   └── sample_inserts.sql
└── queries/
    └── analytics_examples.sql
```

This structure keeps the project easy to review because DDL, ER modeling, sample data, and analytical SQL are separated into clear subfolders. It is also useful for a portfolio project because a reviewer can understand the scope quickly.

## Business scenario

A retail store records transactions at the line-item level, where one transaction may contain multiple products.

For analytics, the warehouse should answer questions such as:

- Which categories drive revenue?
- Which stores perform best?
- How do sales evolve over time?
- Which customers generate the most value?

## Data model choice

A star schema is appropriate because it places measurable business events in a central fact table and descriptive attributes in dimension tables around it.

This structure is widely used in analytical systems because it makes BI queries easier to write and understand than highly normalized transactional schemas.

## Fact table

The central table is `fact_sales`.

Each row represents one sold product line within a transaction, which defines the grain of the model.

### Suggested measures

- `quantity`
- `unit_price`
- `discount_amount`
- `gross_amount`
- `net_amount`

## Dimension tables

The surrounding dimensions provide descriptive context for reporting.

- `dim_date` for calendar reporting such as month, quarter, and year
- `dim_product` for category, subcategory, brand, and product analysis
- `dim_customer` for customer-level analysis and segmentation
- `dim_store` for location and store performance reporting

## Recommended grain

The recommended grain is: **one row in `fact_sales` equals one product line in one transaction**.

Declaring the grain early is essential because every measure and dimension relationship depends on it.

## PostgreSQL implementation

PostgreSQL supports creation of separate schemas inside a database by using `CREATE SCHEMA`.

In this project, the warehouse objects should be created under a schema such as `dwh`, which keeps analytical objects organized and distinct from other database objects.

### Example setup

```sql
CREATE SCHEMA IF NOT EXISTS dwh;
```

### Core implementation principles

- Use surrogate keys in dimension tables for clean joins in the fact table
- Use primary keys on all dimensions and foreign keys from `fact_sales` to each dimension
- Add indexes on fact foreign key columns to support joins and filtering efficiently
- Keep descriptive attributes in dimensions and numeric measures in the fact table

## Logical schema

A minimal logical schema for this portfolio project can look like this:

```text
                 dim_date
                    |
dim_customer --- fact_sales --- dim_product
                    |
                 dim_store
```

This ER shape reflects the standard star schema pattern, where dimension tables connect directly to the fact table and not to each other.

## ER visualization

The project should include a visual ER diagram showing the central fact table and its one-to-many relationships to the dimensions.

Recommended ERD annotations:

- Highlight `fact_sales` as the central fact table
- Mark primary and foreign keys clearly
- Add a note describing the grain of the fact table
- Keep the diagram business-readable, not only technical

## Sample analytics questions

The warehouse should support simple analytical queries such as:

- Revenue by month and quarter
- Sales by product category and brand
- Top-performing stores by net sales
- Customer purchase frequency and total spend

These use cases align well with the strengths of a star schema because the joins remain predictable and dimension attributes are easy to group by.

## What to include in the portfolio

A complete portfolio-ready version of this folder should contain:

- PostgreSQL DDL for schema and table creation
- ERD source file, for example DBML for dbdiagram.io
- Sample insert statements or CSV-based seed data
- Example analytical queries
- A short explanation of modeling decisions, grain, measures, and dimensions

## Suggested files

### `ddl/star_schema.sql`

Contains all `CREATE TABLE`, `PRIMARY KEY`, `FOREIGN KEY`, and index statements for the warehouse schema.

### `erd/star_schema.dbml`

Contains DBML source that can be pasted into dbdiagram.io to render the ER diagram.

### `sample_data/sample_inserts.sql`

Contains a small amount of test data for dimensions and fact rows so the model can be demonstrated locally.

### `queries/analytics_examples.sql`

Contains example queries such as monthly revenue, sales by category, and store ranking.

## Optional extensions

To make the project stronger, add a staging table such as `stg_sales_raw` and show a simple load path from staging into dimensions and facts.

That addition demonstrates not only dimensional modeling but also basic warehouse thinking around data preparation and loading.
