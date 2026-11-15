# AirSight — Smart Urban Air Quality Analytics

AirSight is an automated data engineering pipeline for Indian urban air quality. It loads a public dataset of daily pollution readings for 26 cities into a cloud data warehouse, cleans and models the data with tested SQL, and lets users explore it through a conversational interface and an interactive explorer. The whole chain runs on a schedule and uses only free-tier tools.

**Stack:** Airbyte Cloud · Snowflake · dbt Core · Apache Airflow · Streamlit (with optional Gemini)

---

## Contents
1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [Tech stack](#tech-stack)
4. [The dataset](#the-dataset)
5. [Data model](#data-model)
6. [Repository structure](#repository-structure)
7. [Prerequisites](#prerequisites)
8. [Setup](#setup)
9. [Running the pipeline](#running-the-pipeline)
10. [Using the app](#using-the-app)
11. [Data quality and testing](#data-quality-and-testing)
12. [Configuration reference](#configuration-reference)
13. [Troubleshooting](#troubleshooting)
14. [Limitations and future work](#limitations-and-future-work)

---

## What it does
- **Ingests** a CSV of daily air quality readings (29,531 rows, 26 cities, January 2015 to July 2020) into Snowflake with Airbyte Cloud.
- **Validates** every load: row count, city count, key columns, date range and a per-column missing-value report, logged to the warehouse.
- **Transforms** the raw table with dbt into a cleaned staging view and three analytics tables: monthly city summaries, pollution trends and city rankings.
- **Tests** the result with 27 dbt data-quality tests.
- **Orchestrates** everything with one Airflow DAG: sync, wait, validate, build, test. It has retries, timeouts and failure logging.
- **Answers questions** in plain English through a Streamlit app, with a guided data explorer, charts, downloads and the SQL behind every answer.

## Architecture

```
city_day.csv (public GitHub raw URL)
        |
        v   Airbyte Cloud (File source -> Snowflake destination)
Snowflake  AIRSIGHT.RAW.CITY_DAY
        |
        v   validate_raw.py  ->  AIRSIGHT.OPS.INGESTION_LOG
        |
        v   dbt run + dbt test (--target prod)
AIRSIGHT.STAGING.STG_CITY_DAY  ->  AIRSIGHT.MARTS.*
        |
        v   read-only BI role
Streamlit app: chat (rules or Gemini) + data explorer
```

The pipeline follows the ELT pattern: raw data is loaded first and transformed inside the warehouse. Apache Airflow runs the DAG `airsight_pipeline`:

```
trigger_sync -> wait_sync -> validate_raw -> transform.dbt_run -> transform.dbt_test -> log_success
```

A full run takes about 2 to 3.5 minutes. Each task retries twice (one minute apart) and has a 20-minute timeout. Failures are recorded in `AIRSIGHT.OPS.PIPELINE_ERRORS`.

## Tech stack

| Layer | Tool | Role |
|---|---|---|
| Ingestion | Airbyte Cloud (free trial) | File (CSV over HTTPS) source to Snowflake destination, started through the Airbyte API |
| Warehouse | Snowflake (free trial) | Layered schemas, role-based access, cost controls |
| Transformation | dbt Core 1.12 with dbt-snowflake 1.9 | Staging model, marts and tests |
| Orchestration | Apache Airflow 2.10 in Docker | Scheduling, retries, monitoring |
| Interface | Streamlit, Plotly, optional Gemini | Chat and explorer on the marts |

## The dataset
Kaggle "Air Quality Data in India (2015–2020)", file `city_day.csv`, derived from the Central Pollution Control Board (CPCB) network. It is committed at `data/city_day.csv`.

| Column | Meaning |
|---|---|
| City, Date | City and day |
| PM2.5, PM10 | Particulate matter |
| NO, NO2, NOx, NH3 | Nitrogen oxides and ammonia |
| CO, SO2, O3 | Carbon monoxide, sulphur dioxide, ozone |
| Benzene, Toluene, Xylene | Volatile organic compounds |
| AQI, AQI_Bucket | Indian Air Quality Index and its category (Good to Severe) |

Real data is messy. Many readings are missing (for example Xylene 61%, PM10 38%, NH3 35%, AQI 16%) and 93 AQI values exceed 1,000, which is impossible on the official 0 to 500 scale. AirSight never fills missing values. Out-of-range AQI readings are kept as `aqi_reported`, flagged, and excluded from AQI averages.

## Data model

| Schema | Contents |
|---|---|
| `RAW` | `CITY_DAY` as loaded by Airbyte (uppercase column names, `"PM2.5"` needs quoting) |
| `STAGING` | `STG_CITY_DAY` view: typed, de-duplicated by (city, date), AQI flagged |
| `MARTS` | `MART_MONTHLY_CITY_SUMMARY`, `MART_POLLUTION_TRENDS`, `MART_CITY_RANKINGS` |
| `OPS` | `INGESTION_LOG` (validation history), `PIPELINE_ERRORS` (task failures) |
| `RAW_DEV`, `DEV_STAGING`, `DEV_MARTS` | A safe development copy; dbt `--target dev` uses these |

**Marts**
- `MART_MONTHLY_CITY_SUMMARY`: one row per city and month with average and maximum AQI, average pollutants, days recorded, days measured, missing and excluded AQI days, and the share of unhealthy days.
- `MART_POLLUTION_TRENDS`: a full month calendar per city with a 3-month rolling AQI, same-month year-over-year change and an Indian season label.
- `MART_CITY_RANKINGS`: overall and yearly average AQI, dense pollution rank (1 is most polluted), percentage of unhealthy days, and best and worst month. Filter on `period_scope` to avoid mixing overall and yearly rows.

**Roles:** `AIRBYTE_ROLE` writes `RAW` and `OPS`; `TRANSFORM_ROLE` reads `RAW` and builds staging and marts; `BI_ROLE` has read-only access to the marts and is the only role the app uses.

## Repository structure

```
.
├── data/                  city_day.csv
├── sql/                   00_setup_snowflake.sql (warehouse, schemas, roles, users, OPS tables)
├── ingestion/             validate_raw.py, show_evidence.py, Airbyte setup notes
├── airflow/               Dockerfile, docker-compose.yml, DAG and task modules
│   └── dags/              airsight_pipeline.py, tasks/ingestion.py, tasks/transformation.py
├── dbt/                   dbt project: models, tests, macros, profiles, dev tools
├── app/                   Streamlit app: chat, explorer, charts, SQL guardrails, tests
├── docs/                  report drafts and screenshots
├── .env.example           All configuration keys (copy to .env)
├── PLAN.md, AGENTS.md     Project plan and rules for AI coding agents
```

## Prerequisites
- **Docker Desktop** (about 4 GB of RAM for the Airflow container). On Windows, a `%UserProfile%\.wslconfig` with `memory=4GB` keeps Docker within limits.
- **Python 3.11** for dbt dev tools and the app.
- **A Snowflake account** (a free trial is enough; no card required).
- **An Airbyte Cloud workspace** with an API application (client ID and secret).
- **Internet access**: every service except Airflow runs in the cloud.
- Optional: a Google AI Studio key for Gemini.

## Setup

### 1. Snowflake
Run `sql/00_setup_snowflake.sql` once in a Snowsight worksheet as `ACCOUNTADMIN`, after replacing each `<<PW>>` with a password of your choice. It creates the warehouse (X-Small, auto-suspend 60 s), a resource monitor, the database, schemas, roles, three service users and the OPS tables. If Snowflake rejects `TYPE=LEGACY_SERVICE` or password logins on your account, switch those users to key-pair authentication.

### 2. Airbyte Cloud
Follow the details in [ingestion/README.md](ingestion/README.md):
- **Source:** File connector, dataset name `city_day`, format `csv`, storage provider *HTTPS: Public Web*, URL = the raw GitHub link of `data/city_day.csv`. The repository must be public for this URL to work.
- **Destination:** Snowflake with role `AIRBYTE_ROLE`, warehouse `AIRSIGHT_WH`, database `AIRSIGHT`, default schema `RAW`, user `AIRBYTE_USER`.
- **Connection:** stream `city_day`, sync mode **Full refresh | Overwrite**, schedule **Manual**, destination namespace default, no stream prefix.
- **API application:** user menu, Settings, Applications, Create an application. Copy the client ID and secret, and note the connection ID from the connection's URL.

Run the first sync once from the Airbyte UI to confirm that `RAW.CITY_DAY` appears.

### 3. Configuration
```
cp .env.example .env
```
Fill in `.env` (see the [reference](#configuration-reference)). Never commit it; it is git-ignored.

### 4. Optional: Python environment for dbt and the app
```
python -m venv .venv
# macOS/Linux: source .venv/bin/activate      Windows: .venv\Scripts\activate
pip install -r dbt/requirements.txt -r app/requirements.txt
```

## Running the pipeline

### With Airflow (recommended)
```
cd airflow
docker compose up -d --build
```
Open http://localhost:8080 and log in as `admin`. The password is generated on every container start; read it with:
```
docker compose logs airflow | grep "Login with"        # PowerShell: Select-String "Login with"
```
Trigger the DAG from the UI (the play button on `airsight_pipeline`) or from a terminal:
```
docker compose exec airflow airflow dags trigger airsight_pipeline
```
Run one sync at a time, because Airbyte does not allow concurrent syncs on one connection. The DAG is scheduled `@daily` with `catchup=False`.

Stop it with `docker compose down` (the run history resets at the next start).

### Inspecting the results
```
docker compose exec airflow python /opt/airflow/ingestion/show_evidence.py
```
This prints the raw row count, a sample, the validation history from `OPS.INGESTION_LOG` and any logged task failures from `OPS.PIPELINE_ERRORS`. The Airflow UI shows run history (Grid), the task graph and per-task logs.

### dbt on its own (development)
Develop against the safe copy `RAW_DEV` so production tables are untouched:
```
python dbt/dev_tools/load_dev_raw.py
python dbt/dev_tools/run_dbt.py build --target dev
python dbt/dev_tools/verify_dev_models.py
```
`--target prod` reads `RAW` and writes `STAGING` and `MARTS`; Airflow always uses `prod`. More detail: [dbt/README.md](dbt/README.md).

## Using the app
```
streamlit run app/streamlit_app.py
```
Set `MARTS_SCHEMA=MARTS` in `.env` to read the production marts (the default `DEV_MARTS` reads the development copy). The app opens at http://localhost:8501.

**Ask AirSight (chat).** Type a question or pick a sample:
- Which are the 5 most polluted cities?
- Compare Delhi and Mumbai AQI over the years
- Show the pollution trend for Delhi
- Which month is worst in Delhi?
- How did lockdown 2020 change Delhi's AQI?
- Show a city month heatmap

Every answer shows a summary, the generated SQL, the result table and a chart.

**Explore data.** Pick a view (city trend, compare cities, city rankings, seasonal pattern or heatmap), choose cities and a year range, and submit. Results can be downloaded as CSV or SQL.

**Two question engines**
- *Rule-based* (always available, no key): common question types become parameterised SQL.
- *Gemini* (optional): set `GEMINI_API_KEY` and `GEMINI_MODEL` to answer broader questions. Gemini receives only the question and the table descriptions, never credentials or result rows. If it fails, the app falls back to the rules.

**Safety.** All generated SQL passes a guardrail: one `SELECT` only, only the mart tables, no DDL or DML, no external functions, a 200-row limit and a 30-second timeout. Queries run as the read-only `BI_USER`. Results are cached in the session for up to five minutes, and nothing queries the warehouse in the background. More detail: [app/README.md](app/README.md).

## Data quality and testing
- **Ingestion validation** (`ingestion/validate_raw.py`): row count equals the expected 29,531, exactly 26 cities, no nulls in `CITY` and `DATE`, date range recorded, and a per-column null report. Results are logged to `OPS.INGESTION_LOG`; failures stop the pipeline.
- **dbt tests:** 27 tests. They cover keys, accepted values, no negative pollutants, valid ranges, raw-to-staging reconciliation, monthly reconciliation and AQI exclusion consistency. A normal run reports `PASS=26 WARN=1 ERROR=0`; the one warning lists the 93 preserved out-of-range AQI readings and does not fail the pipeline.
- **Reconciliation:** raw rows (29,531) equal staging rows (29,531), with no duplicate (city, date) pairs and 26 cities.
- **App tests:**
  ```
  python -m unittest discover -s app -p "test_*.py" -v
  python app/validate_analytics.py --schema MARTS
  ```

## Configuration reference

| Variable | Used by | Description |
|---|---|---|
| `SNOWFLAKE_ACCOUNT` | all | Account identifier (`orgname-accountname`) |
| `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE` | all | Default `AIRSIGHT_WH`, `AIRSIGHT` |
| `AIRBYTE_USER`, `AIRBYTE_PASSWORD` | validation, Airbyte | Snowflake user that owns `RAW` and `OPS` |
| `DBT_USER`, `DBT_PASSWORD` | dbt | Snowflake user for transformations |
| `BI_USER`, `BI_PASSWORD` | app | Read-only Snowflake user for the app |
| `MARTS_SCHEMA` | app | `MARTS` (production) or `DEV_MARTS` |
| `AIRBYTE_CLIENT_ID`, `AIRBYTE_CLIENT_SECRET` | Airflow | Airbyte API application credentials |
| `AIRBYTE_CONNECTION_ID` | Airflow | The Airbyte connection to trigger |
| `EXPECTED_ROW_COUNT`, `EXPECTED_CITY_COUNT` | validation | Expected 29,531 rows and 26 cities |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | app (optional) | Enable Gemini; the model name is always read from config |

## Troubleshooting
- **Airflow login fails:** a new admin password is generated on every container start. Read it from the logs as shown above.
- **`trigger_sync` fails with 401:** the Airbyte client ID or secret in `.env` is missing or wrong. After editing `.env`, run `docker compose up -d --force-recreate` so the container picks it up.
- **Docker commands fail:** start Docker Desktop and wait for "Engine running".
- **Airbyte cannot read the CSV:** the repository must be public and the raw URL must open in a browser.
- **Snowflake login refused:** the account may require key-pair authentication for service users.
- **Times differ between Airflow and Snowflake:** Airflow shows UTC while Snowflake's session clock is Pacific time.
- **Trials:** the Airbyte Cloud trial starts at the first successful sync and Snowflake's lasts 30 days. If either ends, the project can be rebuilt from this repository and `sql/00_setup_snowflake.sql`.

## Limitations and future work
- The source is a static file ending in July 2020, so results describe history, not current air quality. A live source such as the Open-Meteo air quality API could be added as a second Airbyte source, kept in its own mart because it is modelled data on a different AQI scale.
- Airflow runs in a single container with SQLite, which suits a laptop. A production deployment would use a PostgreSQL metadata database and a real executor.
- City coverage differs, so comparisons are descriptive, not causal. The app says so.
- Possible additions: alerting from the failure callback, a published dbt docs site, and incremental syncs once a live source exists.

## Development notes
Project plan: [PLAN.md](PLAN.md). Rules for AI coding agents working in this repository: [AGENTS.md](AGENTS.md). Secrets stay in the git-ignored `.env`; only `.env.example` is committed.
