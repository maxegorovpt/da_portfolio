# Multi-Touch Attribution Pipeline

This Streamlit-first project uses local CSV files instead of dbt models.

## Structure

- `data/ads/`: daily 2025 ad source files with unified schema
- `data/purchases/purchases.csv`: full-year purchases data
- `data/ltv/ltv.csv`: user-level lifetime value aggregates
- `src/loaders.py`: data loading helpers
- `src/metrics.py`: CAC, LTV, and LTV:CAC calculations
- `src/charts.py`: chart helper functions

## Core datasets

### Ads schema
`date_day, ad_source, campaign_id, campaign_name, country, platform, spend_usd, impressions, clicks, installs, conversions, revenue_usd`

### Purchases schema
`user_id, purchase_date, platform, ad_source, purchase_amount, country`

### LTV schema
`user_id, ad_source, platform, country, total_revenue, purchase_count, first_purchase_date, last_purchase_date, ltv_usd`

## Suggested next app features

1. Load all datasets from `src/loaders.py`
2. Add 2025 filters for date, platform, source, and country
3. Build CAC by source, platform, and country
4. Build average LTV and LTV:CAC ratio comparisons
5. Add geo distribution charts for spend, customers, and ratio