# ✈️ Flight Analytics — dbt Project

> Analytics engineering practice built on real flight data. Clean models, tested sources, documented schemas — the full stack.

[![dbt](https://img.shields.io/badge/dbt-FF694B?style=flat&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQL](https://img.shields.io/badge/SQL-003B57?style=flat&logo=sqlite&logoColor=white)](#)

---

## 🗂️ About

This project is part of a broader analytics engineering portfolio, focused specifically on **flight data** — built to demonstrate dbt best practices in a clean, standalone repository.

It covers the full analytics engineering workflow: raw source ingestion → staging → marts, with tests and documentation at every layer.

🔗 **Repository:** [github.com/maxegorovpt/airport_practice](https://github.com/maxegorovpt/airport_practice)

---

## 📦 What's Inside

| Layer | What it does |
|-------|-------------|
| **Sources** | Raw flight data defined and documented in `schema.yml` |
| **Models** | Staged and transformed models across the medallion layers |
| **Tests** | `not_null`, `unique`, `accepted_values`, and relationship tests |
| **Docs** | Auto-generated dbt documentation for all models and columns |
| **Notes** | Project experiments, learnings, and design decisions |

---

## 🏗️ Project Structure

```
airport_practice/
├── models/
│   ├── staging/          # Clean, typed source models
│   └── marts/            # Business-ready output models
├── tests/                # Custom data tests
├── macros/               # Reusable SQL logic
├── seeds/                # Static reference data
├── dbt_project.yml       # Project config
└── packages.yml          # dbt packages
```

---

## 🛠️ Tech Stack

- **[dbt](https://getdbt.com)** — transformation, testing, and documentation
- **PostgreSQL** — data warehouse backend
- **SQL** — the bread and butter
- **GitHub** — version control and collaboration

---

## 🚀 Getting Started

### Prerequisites

- dbt Core installed (`pip install dbt-postgres`)
- A running PostgreSQL instance
- Profiles configured at `~/.dbt/profiles.yml`

### Run the project

```bash
# Clone the repo
git clone https://github.com/maxegorovpt/airport_practice.git
cd airport_practice

# Install dbt packages
dbt deps

# Test your connection
dbt debug

# Run all models
dbt run

# Run tests
dbt test

# Generate and serve documentation
dbt docs generate && dbt docs serve
```

---

## 🧪 Testing Strategy

Tests are defined at the source and model level using dbt's built-in test framework:

- **Uniqueness** — primary keys are unique across all models
- **Not null** — critical fields never contain nulls
- **Accepted values** — categorical columns contain only valid entries
- **Relationships** — foreign keys reference valid records in upstream models

---

## 📖 Documentation

This project uses dbt's built-in documentation system. Every source, model, and column is described in `schema.yml` files throughout the project.

To view the docs locally:

```bash
dbt docs generate
dbt docs serve
```

Then open [http://localhost:8080](http://localhost:8080).

---

## 💡 Key Concepts Demonstrated

- **Layered modelling** — staging → intermediate → mart separation
- **Source freshness** — monitoring data recency with `dbt source freshness`
- **DRY SQL** — using `ref()`, `source()`, and macros to avoid repetition
- **Schema testing** — data quality enforced at every layer
- **Column-level documentation** — self-documenting data warehouse

---

## 🗺️ Related Work

This project is part of a broader analytics portfolio. Check out the main profile for other projects across Python, SQL, and data engineering.
