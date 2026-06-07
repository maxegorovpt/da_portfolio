# Multi-Touch Attribution Pipeline

An end-to-end analytics engineering project that ingests paid marketing data from Google Ads, Meta Ads, and LinkedIn Ads, joins it with HubSpot CRM conversion data, and applies three attribution models to measure channel performance across $X in ad spend.

## Architecture

```
Sources                 Ingestion        Staging          Intermediate     Mart
──────────────────────  ───────────────  ───────────────  ───────────────  ──────────────────
Google Ads API    ────► Fivetran ──────► stg_google_ads ─►
Meta Ads API      ────► Fivetran ──────► stg_meta_ads   ─► int_touchpoints ─► fct_attribution
LinkedIn Ads API  ────► Fivetran ──────► stg_linkedin_ads►
HubSpot CRM       ────► Fivetran ──────► stg_hubspot    ─►
```

## Attribution models

| Model | Logic |
|---|---|
| First-touch | 100% credit to the first channel a contact interacted with |
| Last-touch | 100% credit to the channel immediately before conversion |
| Linear | Equal credit split across all touchpoints in the journey |
| Time-decay | Exponentially more credit to touchpoints closer to conversion (bonus macro included) |

## Stack

- **Ingestion**: Fivetran
- **Warehouse**: BigQuery (Snowflake config included in `profiles.yml`)
- **Transformation**: dbt Core 1.7
- **Testing**: dbt tests + Elementary
- **CI/CD**: GitHub Actions
- **BI**: Looker Studio / Tableau

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/attribution-pipeline.git
cd attribution-pipeline

# 2. Install dbt and dependencies
pip install dbt-bigquery==1.7.*
dbt deps

# 3. Configure your warehouse connection
cp profiles.yml ~/.dbt/profiles.yml
# Edit ~/.dbt/profiles.yml with your credentials

# 4. Set environment variables
export DBT_DATABASE=your_gcp_project

# 5. Run the pipeline
dbt build
```

## Project structure

```
attribution_pipeline/
├── models/
│   ├── staging/
│   │   ├── sources.yml              # Fivetran source declarations + freshness SLAs
│   │   ├── schema.yml               # Column tests for all staging models
│   │   ├── stg_google_ads.sql       # Cleans Google Ads; converts cost_micros → USD
│   │   ├── stg_meta_ads.sql         # Cleans Meta Ads; extracts conversions from JSON
│   │   ├── stg_linkedin_ads.sql     # Cleans LinkedIn; converts cost cents → USD
│   │   └── stg_hubspot_contacts.sql # Cleans HubSpot; converts epoch ms → timestamps
│   ├── intermediate/
│   │   └── int_touchpoints.sql      # Unions all ad sources into one touchpoints table
│   └── marts/
│       └── fct_attribution.sql      # Applies all three attribution models
├── macros/
│   └── attribution_models.sql       # Reusable Jinja macros for each attribution model
├── tests/
│   └── test_attribution_no_double_counting.sql
├── .github/workflows/
│   └── dbt_ci.yml                   # CI: dbt build on every PR (modified models only)
├── dbt_project.yml
├── packages.yml
└── profiles.yml                     # Template — do not commit real credentials
```

## Key design decisions

- **cost_micros → USD**: Google Ads reports cost in millionths of a dollar. Division by 1,000,000 happens in `stg_google_ads` so downstream models never see raw micros.
- **Meta conversions from JSON**: Meta stores action types in a JSON array. The staging model extracts `purchase` actions only, matching the finance team's revenue definition.
- **HubSpot epoch ms**: HubSpot timestamps are epoch milliseconds, not seconds. `timestamp_millis()` is used explicitly to avoid silent wrong-date bugs.
- **Linear as default**: Linear attribution is used as the default in the dashboard because it avoids over-crediting brand campaigns (first-touch) or retargeting (last-touch). The mart exposes all three so the marketing team can compare.
- **Surrogate keys**: `dbt_utils.generate_surrogate_key` is used on `int_touchpoints` to create a stable `touchpoint_id` across union sources.

## Dashboard metrics

| Metric | Definition |
|---|---|
| Blended ROAS | SUM(attributed_revenue) / SUM(spend_usd) |
| CAC | SUM(spend_usd) / COUNT(DISTINCT contact_id) |
| Revenue by channel | SUM(linear_credit) GROUP BY channel |
| Attribution model comparison | First vs last vs linear side-by-side |
| Budget pacing | spend_to_date / monthly_budget_target |
