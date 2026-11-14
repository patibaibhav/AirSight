# AirSight — Smart Urban Air Quality Analytics

Automated data-engineering pipeline for Indian city air quality:
CSV → **Airbyte Cloud** → **Snowflake** → **dbt Core** → **Streamlit** conversational BI, orchestrated by **Apache Airflow**.

- Plan: [PLAN.md](PLAN.md) · Agent rules: [AGENTS.md](AGENTS.md)
- Team: Baibhav (ingestion & orchestration), Rahul (transformation & analytics)

## Quick start
1. `cp .env.example .env` and fill values (get secrets from teammate, never commit).
2. Rahul: run `sql/00_setup_snowflake.sql` once in Snowsight.
3. Airflow (Baibhav): `cd airflow && docker compose up --build` → http://localhost:8080
4. dbt (Rahul): see `dbt/README.md` (added by Rahul).
5. App (Rahul): `pip install -r app/requirements.txt && streamlit run app/streamlit_app.py`

(Full run/demo instructions are filled in by Baibhav at the end — PLAN.md B15.)
