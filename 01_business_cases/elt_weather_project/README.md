# 🌤️ Germany Weather ETL — Airflow Project
> End-to-end data engineering practice built on real weather data. Historical backfill, hourly orchestration, idempotent loads, and a live dashboard — the full pipeline.

[![Airflow](https://img.shields.io/badge/Airflow-017CEE?style=flat&logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)

---

## 🗂️ About

This project is part of a broader data engineering portfolio, focused specifically on **weather data across Germany's 10 largest cities** — built to demonstrate practical Airflow orchestration in a clean, standalone repository.

It covers the full ETL workflow: extract from public APIs → transform and validate → load into Postgres, with a 3-year historical backfill sitting alongside a live hourly pipeline, and an interactive dashboard on top.

🔗 **Repository:** [github.com/maxegorovpt/weather-etl-airflow](https://github.com/maxegorovpt/weather-etl-airflow)

---

## 📦 What's Inside

| Layer | What it does |
|-------|-------------|
| **Extract** | Pulls hourly current weather for 10 cities from OpenWeatherMap |
| **Backfill** | One-time load of ~3 years of hourly history per city from Open-Meteo |
| **Transform** | Cleans, validates, and flattens raw API responses |
| **Load** | Idempotent upserts into Postgres (`ON CONFLICT` — safe to retry/backfill) |
| **Data quality** | Row count, null, and sane-range checks as a DAG task |
| **Dashboard** | Streamlit app: historical analytics + live 7-day forecast |

---

## 🏗️ Project Structure

```
weather-etl-airflow/
├── dags/
│   └── weather_etl_dag.py     # TaskFlow DAG: extract → transform → load → quality check
├── plugins/weather/
│   ├── extract.py             # OpenWeatherMap API calls
│   ├── transform.py           # Cleaning, validation, dedup
│   └── load.py                # Idempotent Postgres upserts
├── scripts/
│   └── backfill_cities.py     # One-time 3-year historical backfill (Open-Meteo)
├── sql/
│   └── create_tables.sql      # Star schema: dim_city + fact_weather
├── dashboard/
│   ├── app.py                 # Streamlit dashboard
│   └── Dockerfile
├── tests/
│   └── test_transform.py      # Unit tests for transform logic
├── docker-compose.yaml
├── Dockerfile                 # Airflow image
└── requirements.txt
```

---

## 🛠️ Tech Stack

- **[Apache Airflow](https://airflow.apache.org)** (TaskFlow API) — orchestration
- **PostgreSQL** — data warehouse (star schema: `dim_city` + `fact_weather`)
- **Streamlit + Plotly** — interactive dashboard, including a live city map
- **Docker Compose** — local infra for the full stack
- **OpenWeatherMap & Open-Meteo APIs** — live and historical weather data

---

## 🚀 Getting Started

### Prerequisites
- Docker Desktop installed and running
- Python 3 (for the one-time backfill script)
- A free [OpenWeatherMap API key](https://openweathermap.org/api)

### Run the project

```bash
# Clone the repo
git clone https://github.com/maxegorovpt/weather-etl-airflow.git
cd weather-etl-airflow

# Configure environment variables
cp .env.example .env   # then add your OpenWeatherMap API key

# Build and start everything
docker-compose build
docker-compose up airflow-init
docker-compose up -d

# Create the database schema
docker cp sql/create_tables.sql weather_warehouse:/create_tables.sql
docker exec -it weather_warehouse psql -U weather_user -d weather -f /create_tables.sql

# Run the one-time historical backfill (3 years, all 10 cities)
python3 -m venv .venv && source .venv/bin/activate
pip install requests psycopg2-binary
python3 scripts/backfill_cities.py
```

Then in the Airflow UI ([localhost:8080](http://localhost:8080)), add the `owm_api_key` Variable and `weather_warehouse` Postgres connection, unpause the `weather_etl` DAG, and trigger a run. Full step-by-step instructions are in the repo's own README.

View the dashboard at [localhost:8501](http://localhost:8501).

---

## 🧪 Data Quality Strategy

Validation happens at two points in the pipeline:

- **Transform-level** — missing fields, out-of-range temperatures, and duplicate `(city, timestamp)` pairs are caught and dropped before loading
- **DAG-level** — a dedicated `data_quality_check` task runs after every load, failing the run if zero rows loaded, nulls appear in required fields, or values fall outside sane bounds

Loads themselves are idempotent (`ON CONFLICT ... DO UPDATE`), so retries, backfills, and DAG re-runs never produce duplicate rows.

---

## 📖 Dashboard

The Streamlit dashboard has two tabs:

- **Historical Data** — country overview, an interactive city map (bubble size = population, color = avg temperature), comparison charts across all 10 cities, and a per-city deep dive (temperature trend, monthly distribution)
- **Current Weather** — live conditions and a 7-day forecast styled after iOS weather widgets, pulling from Open-Meteo's free forecast API on demand

---

## 💡 Key Concepts Demonstrated

- **Backfill + incremental load** — one-time historical seed alongside an ongoing hourly pipeline, both writing to the same schema
- **Idempotency** — upserts keyed on `(city_id, observed_at)` make retries and backfills safe
- **TaskFlow API** — modern Airflow DAG authoring with automatic XCom passing
- **Data quality as code** — validation baked into the DAG, not left to manual checks
- **Dimensional modeling** — a minimal star schema (`dim_city` + `fact_weather`) instead of one flat table

---

## 🗺️ Related Work

This project is part of a broader data engineering portfolio. Check out the main profile for other projects across Python, SQL, and analytics engineering.