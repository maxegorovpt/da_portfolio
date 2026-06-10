# 📊 LTV vs CAC Marketing Dashboard

**Live Dashboard:** [View the App on Streamlit](https://daportfolio-hqxl7fspdra6eyqjs2qmhx.streamlit.app/)

## Overview
This project is an end-to-end data analytics portfolio project that calculates, tracks, and visualizes **Customer Acquisition Cost (CAC)** and **Lifetime Value (LTV)** across multiple marketing channels. Built with Python and Streamlit, it processes raw ad spend and purchase data to give stakeholders a clear view of unit economics, marketing efficiency, and cash flow trends for the year 2025.

## Key Features
- **Dynamic Granularity Tracking:** Time-series visualization of Costs vs. Revenue, switchable between Daily, Weekly, Monthly, and Quarterly views.
- **Multi-Dimensional Breakdowns:** Instantly slice overall performance by **Platform** (iOS/Android), **Ad Source** (Google, Meta, TikTok, etc.), or **Country**.
- **Interactive Global Filters:** Sidebar filters allow users to drill down into specific regions, platforms, or channels, updating all KPIs and charts simultaneously.

## Metrics & Definitions
The dashboard standardizes marketing metrics to provide a single source of truth:
- **Spend (Costs):** Total ad spend across all ingested sources.
- **Revenue:** Actual realized cash flow from purchases (sourced directly from `purchases.csv` to prevent group duplication).
- **Customers:** Count of unique users acquired.
- **CAC (Customer Acquisition Cost):** `Total Spend / New Customers`.
- **LTV (Lifetime Value):** `Total Revenue / Unique Customers`. 
- **LTV/CAC Ratio:** The golden ratio of marketing efficiency (`LTV / CAC`).

## Data Pipeline Architecture
The project is split into a robust backend calculation engine and a lightweight frontend visualization layer:

1. **Extraction & Loading (`src/loaders.py`):** Ingests and standardizes schemas from fragmented ad networks (Facebook, Google, TikTok, Affiliates) and transactional purchase data.
2. **Transformation & Metrics (`src/metrics.py`):** Maps users to their first purchase (cohort date), attributes them to ad sources, and calculates base unit economics while handling edge cases like missing campaign dates.
3. **Calculation Scripts (`data/calculations/`):** Standalone scripts that execute the pipeline and output clean, aggregated `cac.csv` and `ltv.csv` files.
4. **Visualization (`streamlit_app.py`):** The frontend application that reads the calculated files alongside raw cash flow data to render the interactive dashboard.

## Repository Structure
```text
├── data/
│   ├── calculations/
│   │   ├── cac_calculation.py    # Generates CAC summary
│   │   ├── ltv_calculation.py    # Generates LTV summary
│   │   ├── cac.csv               # Aggregated spend data (Output)
│   │   └── ltv.csv               # Aggregated cohort data (Output)
│   └── source_data/
│       ├── purchases.csv         # Raw transactional data
│       └── *_ads.csv             # Raw daily ad spend by network
├── src/
│   ├── loaders.py                # Data ingestion & normalization logic
│   └── metrics.py                # Core mathematical logic for unit economics
├── streamlit_app.py              # Main dashboard application
├── requirements.txt              # Python dependencies
└── README.md
```

## Local Setup
To run this project locally on your machine:

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <your-repo-folder>
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the calculation scripts to generate the latest aggregations:
   ```bash
   python data/calculations/cac_calculation.py
   python data/calculations/ltv_calculation.py
   ```
4. Launch the Streamlit dashboard:
   ```bash
   streamlit run streamlit_app.py
   ```