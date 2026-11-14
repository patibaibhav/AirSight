# AirSight — Smart Urban Air Quality Analytics

Automated data-engineering pipeline for Indian city air quality:
CSV → **Airbyte Cloud** → **Snowflake** → **dbt Core** → **Streamlit** conversational BI, orchestrated by **Apache Airflow**. Everything runs on free tiers.

```
data/city_day.csv (GitHub raw) -> Airbyte Cloud -> Snowflake RAW.CITY_DAY -> validate_raw
   -> dbt run -> dbt test -> STAGING.STG_CITY_DAY -> MARTS.* -> Streamlit chat (Gemini / rule-based)
```

- Plan and ownership: [PLAN.md](PLAN.md) · Agent rules: [AGENTS.md](AGENTS.md)
- Team: Baibhav (ingestion and orchestration), Rahul (transformation and analytics)

## Repository layout
| Path | Owner | Contents |
|---|---|---|
| `data/` | B | `city_day.csv` (29,531 rows, 26 cities, 2015–2020) |
| `ingestion/` | B | `validate_raw.py`, `show_evidence.py`, Airbyte notes |
| `airflow/` | B | Dockerfile, compose file, DAG `airsight_pipeline` (`tasks/transformation.py` is Rahul's) |
| `dbt/` | R | staging model, marts, tests |
| `app/` | R | Streamlit conversational BI |
| `sql/` | R | Snowflake setup script |
| `docs/` | both | handoff notes, report sections, screenshots |

## Prerequisites
- Docker Desktop (about 4 GB RAM available; on Windows set `memory=4GB` in `%UserProfile%\.wslconfig`)
- A Snowflake account with the objects from `sql/00_setup_snowflake.sql`
- An Airbyte Cloud workspace with the source, destination and connection described in `ingestion/README.md`, plus an API application (client id and secret)
- Python 3.11 for the Streamlit app

## Setup
1. `cp .env.example .env` and fill in the values (get secrets from a teammate; **never commit `.env`**). Needed for Airflow: `SNOWFLAKE_ACCOUNT`, `AIRBYTE_*`, `DBT_*`, `AIRBYTE_CLIENT_ID/SECRET`, `AIRBYTE_CONNECTION_ID`, `EXPECTED_ROW_COUNT`.
2. Airflow:
   ```
   cd airflow
   docker compose up -d --build
   ```
   Open http://localhost:8080, log in as `admin`. The generated password is printed in the container logs:
   `docker compose logs airflow | Select-String "Login with"` (PowerShell).
3. Trigger the pipeline: open DAG `airsight_pipeline` → ▶ **Trigger DAG**. Or from a terminal:
   `docker compose exec airflow airflow dags trigger airsight_pipeline`
   A full run takes about 2.5 minutes. Run one at a time (Airbyte allows one sync per connection).
4. App (Rahul): see `dbt/README.md` and `app/`; `pip install -r app/requirements.txt` then `streamlit run app/streamlit_app.py` with `MARTS_SCHEMA=MARTS`.

Stop Airflow with `docker compose down` (from `airflow/`). After a restart a **new** admin password is generated.

## Demo script (about 5 minutes)
1. Show the architecture and the repo.
2. Airbyte Cloud: source (File CSV), destination (Snowflake), connection (manual, full refresh overwrite).
3. Airflow: trigger `airsight_pipeline`; show Graph view (expand `transform`) while it runs, then Grid and task logs (`wait_sync`, `dbt_test`).
4. Evidence: `docker compose exec airflow python /opt/airflow/ingestion/show_evidence.py` prints the raw row count, validation history and logged failures.
5. Snowflake: schemas `RAW`, `STAGING`, `MARTS`, `OPS` and the mart tables.
6. Streamlit: ask "Which are the 5 most polluted cities?", "Compare Delhi and Mumbai AQI over the years", "Which month is worst in Delhi?"; show the generated SQL and charts.
7. Failure handling (optional): point to `OPS.PIPELINE_ERRORS` and the retry settings in the DAG Code tab.

## Verification (what was tested)
- Full DAG run green on real services: Airbyte sync → `validate_raw` → `dbt run` → `dbt test` (`PASS=26 WARN=1 ERROR=0`; the warning is the intentional flag on 93 AQI readings above 1,000).
- Raw (29,531) equals staging (29,531); no duplicate (city, date) pairs; 26 cities.
- A fresh clone with no `.env` builds the Airflow image.

## Troubleshooting
- **Airflow login fails:** a new password is generated on every container restart; read it from the logs as above.
- **`trigger_sync` returns 401:** wrong or missing `AIRBYTE_CLIENT_ID/SECRET` in `.env`; recreate the container after editing (`docker compose up -d --force-recreate`).
- **Docker commands fail:** start Docker Desktop and wait for "Engine running".
- **Airbyte trial:** the 14-day trial starts at the first successful sync; Snowflake's trial lasts 30 days. The pipeline is fully reproducible from this repository and `sql/00_setup_snowflake.sql` if an account has to be recreated.
