# Baibhav — Ingestion, orchestration and pipeline sections (report draft)

> Owner: B. Draft text for the faculty report format. Screenshot files are in `docs/screenshots/`.
> Items in [square brackets] must be filled by the team (cover page details, names, roll numbers).

---

## Cover Page
[Use the faculty "Common Format" front page. Project title: **AirSight — Smart Urban Air Quality Analytics**. Group of 2: Baibhav Pati, Rahul Patil. Course: Data Engineering Microproject. Date of demo: 16–17 November 2026.]

## Abstract
AirSight is an automated, end-to-end data engineering pipeline for Indian urban air quality. A public CPCB-derived dataset of daily air pollution readings for 26 cities (2015–2020, 29,531 rows) is ingested by Airbyte Cloud into a Snowflake warehouse, validated, transformed by dbt Core into a staging layer and three analytical data marts, and orchestrated end to end by Apache Airflow. A Streamlit conversational interface lets users ask natural-language questions about pollution trends, city rankings and monthly patterns. The entire stack runs on free tiers and the full pipeline completes in about two and a half minutes.

---

## 1. Problem Statement & Objective
Air pollution data for Indian cities is published as large, inconsistent files with many missing readings, so it is hard for non-technical users to compare cities or see trends. Manual cleaning and ad-hoc analysis are slow and not repeatable.

**Objective:** design and implement an automated end-to-end data pipeline that ingests, validates, transforms, stores and queries air quality data using a modern data stack (Airflow, Airbyte, dbt, Snowflake), ending in a simple conversational BI interface, entirely on free-tier tools.

---

## 2. Architecture & Tech Stack

| Layer | Tool | Role |
|---|---|---|
| Source data | Kaggle "Air Quality Data in India (2015–2020)", `city_day.csv` | 29,531 daily rows, 26 cities, 16 columns (PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3, Benzene, Toluene, Xylene, AQI, AQI_Bucket) |
| Ingestion | Airbyte Cloud (free trial) | File source (CSV over HTTPS, hosted on GitHub raw) to Snowflake destination |
| Warehouse | Snowflake (free trial) | Database `AIRSIGHT`; schemas `RAW`, `STAGING`, `MARTS`, `OPS` (and dev copies) |
| Transformation | dbt Core + dbt-snowflake | Staging model, three marts, data-quality tests |
| Orchestration | Apache Airflow 2.10 (Docker) | DAG `airsight_pipeline` scheduled daily |
| BI / interface | Streamlit (+ Gemini free tier, rule-based fallback) | Conversational analytics and charts |
| Collaboration | GitHub, folder-ownership workflow | Two people working in parallel without merge conflicts |

**Data flow:**
`city_day.csv` (GitHub raw URL) → Airbyte Cloud → Snowflake `RAW.CITY_DAY` → validation → dbt run → dbt test → `STAGING.STG_CITY_DAY` → `MARTS.*` → Streamlit conversational BI

**Role-based security in Snowflake:** three least-privilege roles — `AIRBYTE_ROLE` (writes `RAW`, `OPS`), `TRANSFORM_ROLE` (reads `RAW`, owns staging and marts), `BI_ROLE` (read-only on marts, used by the chat app). Secrets live only in git-ignored `.env` files.

---

## 3. Implementation Details (ingestion and orchestration)

### 3.1 Ingestion (Airbyte Cloud)
- **Source:** Airbyte "File (CSV, JSON, Excel, Feather, Parquet)" connector, dataset name `city_day`, format CSV, storage provider *HTTPS: Public Web*, pointing at the raw GitHub URL of `data/city_day.csv`. (Screenshots: `B_airbyte_source_form.png`, `B_airbyte_source_created.png`.)
- **Destination:** Snowflake, role `AIRBYTE_ROLE`, warehouse `AIRSIGHT_WH` (X-Small, auto-suspend 60 s), database `AIRSIGHT`, default schema `RAW`.
- **Connection:** stream `city_day`, sync mode *Full refresh | Overwrite* (the file is static, so no incremental merge is needed), schedule *Manual* because Airflow triggers every sync through the Airbyte API. (Screenshot: `B_airbyte_connection_config.png`.)
- **Result:** table `AIRSIGHT.RAW.CITY_DAY` with 29,531 rows. Airbyte typed the pollutant columns as FLOAT, kept `CITY`, `DATE` and `AQI_BUCKET` as text, and added its own metadata columns. (Screenshots: `B_airbyte_first_sync.png`, `B_airbyte_sync.png`.)

### 3.2 Orchestration (Apache Airflow)
Airflow runs in a single lightweight Docker container (`airflow standalone`, SQLite, 3 GB memory limit; about 1.7 GB used in practice) so that it fits on an 8 GB laptop. dbt runs in a separate Python virtual environment inside the same image, which avoids dependency conflicts with Airflow.

The DAG `airsight_pipeline` (scheduled `@daily`, `catchup=False`) has these tasks:

| Task | What it does |
|---|---|
| `trigger_sync` | Obtains a fresh Airbyte API token and starts a sync job for the connection |
| `wait_sync` | Polls the Airbyte job every 15 s until it succeeds (fails on failed or cancelled, times out after 15 min) |
| `validate_raw` | Runs data-validation checks on `RAW.CITY_DAY` (section 3.3) |
| `transform.dbt_run` | Runs the dbt models against the production schemas |
| `transform.dbt_test` | Runs the dbt data-quality tests |
| `log_success` | Marks the run complete |

(Screenshots: `B_airflow_graph.png`, `B_airflow_graph_dbt.png`, `B_airflow_grid_graph.png`.)

The ingestion half of the DAG and the dbt half were written by different team members and joined through a single interface: the DAG imports a `build_transformation_group(dag)` function from a separate file. This seam is what allowed both people to work in parallel without edit conflicts.

### 3.3 Ingestion validation
After every sync, `validate_raw.py` checks the loaded table and logs the result to `OPS.INGESTION_LOG`:
- row count equals the expected 29,531;
- 26 distinct cities;
- no missing values in the key columns `CITY` and `DATE`;
- minimum and maximum dates (2015-01-01 to 2020-07-01);
- a per-column missing-value percentage report.

If any check fails, the task raises an error, the DAG run fails and the failure is recorded. Missing pollutant readings are expected in this dataset and are reported, not treated as failures. Measured missing rates: Xylene 61%, PM10 38%, NH3 35%, Toluene 27%, Benzene 19%, AQI 16%, PM2.5 16%, O3 14%, NOx 14%, SO2 13%, NO2 12%, NO 12%, CO 7%.
(Screenshot: `B_snowflake_evidence.png`.)

### 3.4 Error handling
- Every task has `retries = 2`, `retry_delay = 1 minute` and a 20-minute execution timeout.
- A failure callback writes the DAG, task, run id and error message to `OPS.PIPELINE_ERRORS` and never masks the original error.
- Evidence: before the Airbyte credentials had been configured, two scheduled runs failed at `trigger_sync` with `401 Unauthorized`; both failures were recorded in `OPS.PIPELINE_ERRORS`. After the credentials were added the pipeline succeeded.

### 3.5 Pipeline monitoring
- The Airflow UI (Grid, Graph, Event Log, task logs) tracks each run and task. (Screenshots: `B_airflow_grid_graph.png`, `B_airflow_event_log.png`.)
- `OPS.INGESTION_LOG` keeps the history of validation results and `OPS.PIPELINE_ERRORS` the history of failures; a helper script (`ingestion/show_evidence.py`) prints them.
- The Airbyte connection timeline shows every triggered sync.

### 3.6 Integration testing
- **End-to-end run:** the full DAG ran successfully with a real Airbyte sync, validation, dbt run and dbt test in about 2.5 minutes, repeated several times.
- **dbt results in Airflow:** `PASS=26 WARN=1 ERROR=0`; the single warning is the intentional flag on 93 source AQI readings above 1,000, which are preserved and reported.
- **Reconciliation:** raw rows (29,531) equal staging rows (29,531), with no duplicate (city, date) pairs and 26 cities.
- **Reproducibility:** a fresh clone of the repository with no local configuration builds the Airflow image successfully.

---

## 4. Key Results & Demo Output (pipeline part)
- 29,531 records for 26 cities ingested, validated and transformed automatically.
- One-click (or daily scheduled) orchestration: sync → validate → transform → test, about 2.5 minutes end to end.
- Production tables: `STAGING.STG_CITY_DAY` (29,531 rows), `MARTS.MART_MONTHLY_CITY_SUMMARY` (1,005 rows), `MARTS.MART_POLLUTION_TRENDS` (1,005 rows), `MARTS.MART_CITY_RANKINGS` (129 rows).
- Complete audit trail of validation runs and failures inside the warehouse.
[Rahul's section 4 covers the sample insights and conversational BI answers.]

---

## 5. Conclusion & Learning Outcomes
We built an automated enterprise-style pipeline that ingests, validates, transforms and serves air quality analytics with free tools only.

Key learnings:
- **Orchestration:** designing a DAG with polling, retries, timeouts and failure logging; combining work from two developers through a clean interface.
- **Modern ELT:** loading raw data first and transforming in the warehouse with dbt; keeping raw data immutable and cleaning in a staging layer.
- **Cloud data warehousing:** role-based access, separate schemas per layer and cost control (X-Small warehouse, auto-suspend, resource monitor).
- **Data quality:** validating at ingestion and testing after transformation, and handling real-world missing values explicitly.
- **Practical engineering:** working within free-tier limits, secrets management, and a folder-ownership workflow that avoids merge conflicts.

**Limitations / future work:** the source file is static (data ends July 2020), so each scheduled run reloads the same data; a live source such as the Open-Meteo air quality API could be added as a second Airbyte source for fresh data.
