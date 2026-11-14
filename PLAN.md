# AirSight — Implementation Plan

> Smart Urban Air Quality Analytics · DE Microproject · Team: **Baibhav (B)** + **Rahul (R)**
> Demo/submission: **16–17 Nov 2026** · Target: pipeline done tonight / tomorrow morning, 16th = buffer + report + rehearsal.
> Agents: read `AGENTS.md` first. This file is the source of truth for *what* and *when*; AGENTS.md is the source of truth for *how to behave*.

---

## 1. Final tech stack (all free, no card)

| Layer | Tool | Notes |
|---|---|---|
| Source | Kaggle "Air Quality Data in India (2015–2020)" → `city_day.csv` | ~29.5k daily rows, 26 cities, real CPCB readings, many missing values (good for dbt tests). Committed to repo as `data/city_day.csv`, read by Airbyte through the GitHub **raw** URL (repo must be **public**). |
| Ingestion | **Airbyte Cloud** free trial | Source: *File* (CSV over HTTPS). Destination: Snowflake. Sync mode: **Full refresh – Overwrite** (static file, no MERGE needed). |
| Warehouse | **Snowflake** free trial (30 days / $400 credits, no card) | XS warehouse, auto-suspend 60 s. |
| Transform | **dbt Core + dbt-snowflake** (no dbt packages → fewer dependencies) | Tests are built-in + singular SQL tests. |
| Orchestration | **Apache Airflow 2.10.x** in ONE Docker container (`airflow standalone`, SQLite) | ~2 GB RAM, fits an 8 GB laptop. dbt lives in a **separate venv inside the image** (avoids dependency clashes). Fallback: GitHub Codespaces. |
| BI | **Streamlit + Gemini free tier** (`google-genai`) | NL → SQL on MARTS only, read-only role, with a **rule-based fallback** that needs no API key. |
| Collab | One public GitHub repo, folder ownership, `pull --rebase` | See AGENTS.md. |
| Report | Word/Google Docs, faculty format | Sections split per person. |

Free-tier facts to double check on signup (I could not verify them from official pages): Airbyte Cloud trial length (~14 days) and credits; Snowflake `TYPE = LEGACY_SERVICE` password users (Snowflake is tightening password logins — if the user creation or login fails, switch that user to key-pair auth); Gemini free-tier rate limits and current free "Flash" model name (we read it from env `GEMINI_MODEL`, never hard-code).

**Open-Meteo**: optional day-2 stretch only (Section 9). Not on the critical path.

---

## 2. Architecture & data flow

```
GitHub raw URL (city_day.csv)
      │  Airbyte Cloud (File source → Snowflake dest, full-refresh overwrite)
      ▼
Snowflake  AIRSIGHT.RAW.CITY_DAY ──► validate_raw.py ──► AIRSIGHT.OPS.INGESTION_LOG
      │                                   (Airflow task)
      │  dbt (Airflow task: dbt run → dbt test, --target prod)
      ▼
AIRSIGHT.STAGING.stg_city_day ──► AIRSIGHT.MARTS.{mart_monthly_city_summary, mart_pollution_trends, mart_city_rankings}
      │  read-only BI_ROLE
      ▼
Streamlit conversational BI (Gemini text-to-SQL + rule-based fallback + Plotly charts)

Airflow DAG `airsight_pipeline`:
 trigger_airbyte_sync → wait_for_sync → validate_raw → dbt_run → dbt_test → log_success
```

### Snowflake layout (the **contract** both of us code against — do not rename)

| Object | Purpose | Owner / writer |
|---|---|---|
| Warehouse `AIRSIGHT_WH` (XS) | all compute | R creates |
| Database `AIRSIGHT` | | R creates |
| Schema `RAW` | Airbyte lands `CITY_DAY` here (Airbyte also makes `airbyte_internal`) | role `AIRBYTE_ROLE` |
| Schema `RAW_DEV` | R's hand-loaded copy of the CSV for development **before** Airbyte works | `TRANSFORM_ROLE` |
| Schemas `STAGING`, `MARTS` | **prod** dbt output (written only by Airflow runs, `--target prod`) | `TRANSFORM_ROLE` |
| Schemas `DEV_STAGING`, `DEV_MARTS` | R's dev dbt output (`--target dev`) | `TRANSFORM_ROLE` |
| Schema `OPS` | `INGESTION_LOG`, `PIPELINE_ERRORS` | `AIRBYTE_ROLE` |
| Users | `AIRBYTE_USER` (B: Airbyte + validation + OPS), `DBT_USER` (R locally + Airflow dbt), `BI_USER` (Streamlit, SELECT on MARTS/DEV_MARTS only) | R creates |

**Dev/prod switch with zero code change:** dbt `--target dev` reads `RAW_DEV` and writes `DEV_*`; `--target prod` reads `RAW` and writes `STAGING/MARTS`. Streamlit reads schema from env `MARTS_SCHEMA` (`DEV_MARTS` → `MARTS`).

---

## 3. Repository structure & ownership

Ownership = who may edit. Anything not listed = B-owned shared file (R asks via handoff note).

```
airsight/
├── AGENTS.md                      [B] shared agent rules (copy from plan pack)
├── CLAUDE.md                      [B] one line: "@AGENTS.md"
├── PLAN.md                        [B]
├── README.md                      [B] setup + how to run + demo script
├── .gitignore  .env.example       [B] (all env vars defined up-front, see §5)
├── data/city_day.csv              [B]
├── sql/00_setup_snowflake.sql     [R]  run once by R in Snowsight
├── ingestion/                     [B]
│   ├── README.md                  Airbyte click-path + connection ID notes (no secrets)
│   └── validate_raw.py            counts / missing fields / cities / date range → OPS log
├── airflow/                       [B] except tasks/transformation.py
│   ├── Dockerfile, docker-compose.yml, requirements-airflow.txt
│   └── dags/
│       ├── airsight_pipeline.py   [B] DAG skeleton, imports both task modules
│       └── tasks/
│           ├── ingestion.py       [B] airbyte trigger/poll, validate, failure logging
│           └── transformation.py  [R] `build_transformation_group()` → dbt run/test
├── dbt/                           [R] whole folder
│   ├── dbt_project.yml, profiles.yml (env-var based), macros/generate_schema_name.sql
│   ├── models/sources.yml
│   ├── models/staging/stg_city_day.sql
│   ├── models/marts/{mart_monthly_city_summary,mart_pollution_trends,mart_city_rankings}.sql
│   ├── models/schema.yml          generic tests (not_null, accepted_values …)
│   ├── tests/*.sql                singular tests (no negatives, PM2.5 ≤ 1500, unique city+date …)
│   └── dev_tools/load_dev_raw.py  loads data/city_day.csv → RAW_DEV.CITY_DAY (read-only use of the CSV)
├── app/                           [R] Streamlit
│   ├── streamlit_app.py, nl2sql.py, rules.py, charts.py, schema_context.py, requirements.txt
└── docs/
    ├── handoff/B_to_R.md          [B] append-only notes to R
    ├── handoff/R_to_B.md          [R] append-only notes to B
    ├── report/B_sections.md       [B]   report/R_sections.md [R]   report/FINAL.docx [B compiles]
    └── screenshots/B_*.png        [B]   screenshots/R_*.png [R]
```

`airflow/dags/tasks/transformation.py` is the **only** cross-owner seam. Contract:

```python
# R owns. B's DAG does: from tasks.transformation import build_transformation_group
def build_transformation_group(dag) -> "TaskGroup":   # group_id="transform"; contains dbt_run >> dbt_test
```
The first scaffold commit contains a stub returning an `EmptyOperator` group, so B's DAG works from minute 1 and R later replaces the body.

dbt command used by Airflow (R writes it inside the group, B only needs it to exist):
`/opt/dbt-venv/bin/dbt run --target prod --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt` then the same with `test`.

---

## 4. Dependency map — who needs what from whom

Designed so **both of you start immediately and nothing blocks beyond ~20 min.**

| # | From → To | What | When | Blocks? |
|---|---|---|---|---|
| H1 | **R → B** | Snowflake account identifier (`orgname-accountname`) + `AIRBYTE_USER` password (private chat, never git) | ≈ T+0:20 | B needs it only for step B5; B does B1–B4 first |
| H2 | **B → R** | GitHub repo invite + scaffold commit (folders, stubs, AGENTS.md, `.env.example`, `data/city_day.csv`) | ≈ T+0:20 | R does Snowflake signup (R1–R2) meanwhile |
| H3 | **R → B** | `DBT_USER` password (for Airflow container `.env`) | T+0:20 (with H1) | needed at B9 only |
| H4 | **B → R** | "RAW landed": `docs/handoff/B_to_R.md` entry with row count + the **exact column names** Airbyte created in `RAW.CITY_DAY` | ≈ T+2:00 | R works on `RAW_DEV` until then; switching is one `--target prod` run + a one-line staging rename if column names differ |
| H5 | **R → B** | "dbt prod-ready": `dbt run/test --target prod` green + `transformation.py` pushed | ≈ T+3:30 | B uses the stub until then |
| H6 | **R → B** | Streamlit URL/run command + 3 screenshots for the report | ≈ T+4:30 | no |
| H7 | **B → R** | Airflow DAG green screenshot + run history + validation results for the report | ≈ T+4:30 | no |

Everything else (Airbyte config, Airflow image, validation, retries, dbt models, tests, marts, Streamlit, charts) is independent.

---

## 5. Secrets & config (never in git)

Each person has a local `.env` (git-ignored). `.env.example` (committed, B-owned, written once at scaffold time) contains **all** keys:

```
# Snowflake
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_WAREHOUSE=AIRSIGHT_WH
SNOWFLAKE_DATABASE=AIRSIGHT
AIRBYTE_USER=AIRBYTE_USER
AIRBYTE_PASSWORD=
DBT_USER=DBT_USER
DBT_PASSWORD=
BI_USER=BI_USER
BI_PASSWORD=
MARTS_SCHEMA=DEV_MARTS          # becomes MARTS after integration
# Airbyte Cloud (B only)
AIRBYTE_CLIENT_ID=
AIRBYTE_CLIENT_SECRET=
AIRBYTE_CONNECTION_ID=
# Gemini (R only)
GEMINI_API_KEY=
GEMINI_MODEL=
# validation
EXPECTED_ROW_COUNT=             # = data rows in data/city_day.csv
EXPECTED_CITY_COUNT=26
```
Share real values only via private chat. `.gitignore` must contain `.env`, `*.env`, `__pycache__/`, `.venv/`, `target/`, `logs/`, `dbt_packages/`, `airflow/airflow-data/`.

---

## 6. Baibhav — ordered steps (Ingestion & Orchestration)

**Phase 0 (T+0:00–0:20) — no dependencies**
- **B1** Create **public** GitHub repo `airsight`; add Rahul as collaborator.
- **B2** Download `city_day.csv` from Kaggle (needs a free Kaggle login). Put in `data/`. Compute row count → `EXPECTED_ROW_COUNT`.
- **B3** Create scaffold exactly as §3 (stubs: `tasks/transformation.py` returns an `EmptyOperator` TaskGroup; empty `dbt/`, `app/`), plus `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.env.example`. Commit + push to `main` → **H2**.
- **B4** Sign up **Airbyte Cloud** (trial). Create source: *File*; dataset name `city_day`; format `csv`; storage *HTTPS: public web*; URL = GitHub raw link of `data/city_day.csv`. Run "test source".

**Phase 1 (T+0:20–2:00)**
- **B5** On receiving **H1**: create destination *Snowflake* — host `<account>.snowflakecomputing.com`, role `AIRBYTE_ROLE`, warehouse `AIRSIGHT_WH`, database `AIRSIGHT`, default schema `RAW`, user `AIRBYTE_USER`. Connection: source→dest, stream `city_day`, **Full refresh | Overwrite**, schedule *manual* (Airflow triggers it). Run first sync.
- **B6** Verify in Snowsight (as `AIRBYTE_USER`): `AIRSIGHT.RAW.CITY_DAY` row count equals CSV; note exact column names/types → write **H4** entry to `docs/handoff/B_to_R.md`. Save the **connection ID** into local `.env`.
- **B7** Write `ingestion/validate_raw.py`: connect (snowflake-connector-python), check (a) row count == `EXPECTED_ROW_COUNT`, (b) distinct cities == `EXPECTED_CITY_COUNT`, (c) null % per column (report, fail only if `CITY` or `DATE` has nulls), (d) min/max date; insert one summary row into `OPS.INGESTION_LOG` (`run_ts, rows, cities, null_report_json, status`); exit non-zero on failure.
- **B8** Airbyte Cloud API app credentials (Settings → Applications) → `.env`. Write `airflow/dags/tasks/ingestion.py` using plain `requests` (no extra provider package): get token (`POST https://api.airbyte.com/v1/applications/token`), trigger job (`POST /v1/jobs {"connectionId", "jobType":"sync"}`), poll (`GET /v1/jobs/{jobId}`) until `succeeded`/`failed`.

**Phase 2 (T+1:30–3:30)**
- **B9** Airflow image: `airflow/Dockerfile` = `apache/airflow:2.10.x` (pin) + `/opt/dbt-venv` with `dbt-snowflake` (pin) + `snowflake-connector-python`, `requests`. `docker-compose.yml`: ONE service running `airflow standalone`, `mem_limit: 3g`, mounts `./dags`, `../dbt` → `/opt/airflow/dbt`, `../ingestion`, env from `.env`. On Windows/8 GB: set `%UserProfile%\.wslconfig` → `[wsl2] memory=4GB`. If it still crawls → run the same compose in Codespaces.
- **B10** `airsight_pipeline.py`: `default_args = {retries: 2, retry_delay: 1 min, on_failure_callback: log_failure, execution_timeout: 20 min}`; `schedule="@daily"`, `catchup=False`; tasks `trigger_sync >> wait_sync >> validate_raw >> transform (R's group) >> log_success`. `log_failure` writes to `OPS.PIPELINE_ERRORS` and Airflow log.
- **B11** Run the DAG end to end with the **stub** transform group. Screenshot Graph + Grid views (`docs/screenshots/B_*`).

**Phase 3 (T+3:30–5:00)**
- **B12** On **H5**: `git pull --rebase`, restart container, trigger DAG: full pipeline green. Set `MARTS_SCHEMA=MARTS` guidance in H6 note to R.
- **B13** Integration test checklist (README): (1) clean-clone rebuild, (2) force-fail a task (wrong connection ID) → retries + `PIPELINE_ERRORS` row, (3) re-run → success, (4) row counts raw vs staging reconcile.
- **B14** Monitoring evidence: Airflow Grid of ≥3 runs, `OPS.INGESTION_LOG` query screenshot.

**Phase 4**: **B15** report sections (Ingestion, Orchestration, validation, error handling), compile FINAL report, README demo script, rehearsal. **B16 (stretch)** Open-Meteo, Section 9.

---

## 7. Rahul — ordered steps (Transformation & Analytics)

**Phase 0 (T+0:00–0:20) — no dependencies**
- **R1** Sign up for Snowflake trial (cloud: AWS, region nearest; edition Standard). Note the account identifier.
- **R2** In a Snowsight worksheet run `sql/00_setup_snowflake.sql` (code in §8; you paste your own passwords, never commit them). Send **H1 + H3** to B. Also create `GEMINI_API_KEY` at Google AI Studio (free) and put it in your `.env`.
- **R3** After **H2**: clone repo, create `.venv`, `pip install dbt-snowflake streamlit plotly pandas snowflake-connector-python google-genai` (pin versions in `app/requirements.txt` and note dbt version in `dbt/README`).

**Phase 1 (T+0:20–2:00) — works on RAW_DEV, does not wait for Airbyte**
- **R4** `dbt/dev_tools/load_dev_raw.py`: read `data/city_day.csv`, `write_pandas` → `AIRSIGHT.RAW_DEV.CITY_DAY` keeping **original CSV headers verbatim** (`"PM2.5"`, `"Date"`, `"AQI_Bucket"` …) as Airbyte most likely does.
- **R5** dbt scaffold: `dbt_project.yml`, `profiles.yml` (targets `dev`/`prod`, env-var creds, role `TRANSFORM_ROLE`), `macros/generate_schema_name.sql` (prod → exact schema name; any other target → `DEV_` + name), `models/sources.yml` with `schema: "{{ 'RAW' if target.name == 'prod' else 'RAW_DEV' }}"`.
- **R6** `stg_city_day.sql`: **one** `renamed` CTE does all column mapping (so a name mismatch with Airbyte is a one-line fix): `try_to_date(to_varchar("Date"))`, `try_to_double(to_varchar(col))` for every pollutant; uppercase/trim city; dedupe on `(city, date)` with `qualify row_number()`; add `city_date_key`; add `aqi_bucket` cleaned, `year`, `month`. Materialize as `view`.
- **R7** Tests: `schema.yml` (not_null city/date/key, unique key, accepted_values for `aqi_bucket`), singular tests `tests/` (no negative pollutant values, PM2.5 ≤ 1500, AQI between 0 and 1000, no future dates). Missing pollutant values are **allowed** (reported, not failed) — document this in the report.

**Phase 2 (T+1:30–3:30)**
- **R8** Marts (materialized `table`): `mart_monthly_city_summary` (city, month_start, avg/max AQI, avg PM2.5/PM10/NO2/O3/CO, days_measured, share of Poor/Very Poor/Severe days), `mart_pollution_trends` (city, year, month, avg_aqi, 3-month rolling avg, YoY change, season label), `mart_city_rankings` (city, overall avg AQI, rank, best/worst month, pct of unhealthy days; rank also per year). Run `dbt build --target dev` green.
- **R9** On **H4**: run `dbt run/test --target prod` once from your laptop (writes `STAGING`/`MARTS`); fix any column-name drift in `renamed` CTE only. Push `tasks/transformation.py` (`BashOperator`s as in §3) → **H5**.

**Phase 3 (T+1:30–4:30, parallel with R8/R9)**
- **R10** `app/` Streamlit chat:
  - `schema_context.py`: table/column descriptions of the 3 marts + the AQI bucket legend, injected into the prompt.
  - `nl2sql.py`: Gemini → returns one `SELECT`; **guardrails**: reject anything not a single `SELECT`/`WITH`, reject DDL/DML keywords, force `LIMIT 200`, only schema = `MARTS_SCHEMA`; connects as `BI_USER` (read-only); on SQL error retry once with the error message fed back.
  - `rules.py`: fallback intents (compare two cities, worst/best cities, trend for a city, monthly pattern, "most polluted month") with regex → parameterised SQL; used automatically when no key/API error/quota.
  - `charts.py`: Plotly line (trend), bar (ranking), grouped bar (city compare), heatmap (city × month AQI).
  - UI: chat input, shows answer text + generated SQL (expander) + table + auto-chart; sidebar sample questions.
- **R11** Analytics validation: for 5 sample questions write the hand SQL, compare with the app output, record in `docs/report/R_sections.md` (table: question / SQL result / app result / match).
- **R12** Switch `.env` `MARTS_SCHEMA=MARTS`, re-run the 5 questions, take screenshots → **H6**.

**Phase 4**: **R13** report sections (DB design, dbt models/tests, marts, BI, validation), demo rehearsal. Optional deploy to Streamlit Community Cloud (free) using Streamlit secrets for backup demos.

---

## 8. `sql/00_setup_snowflake.sql` (R creates; replace `<<PW>>` locally)

```sql
USE ROLE ACCOUNTADMIN;
CREATE WAREHOUSE IF NOT EXISTS AIRSIGHT_WH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=TRUE;
CREATE RESOURCE MONITOR IF NOT EXISTS AIRSIGHT_RM WITH CREDIT_QUOTA=50 TRIGGERS ON 100 PERCENT DO SUSPEND;
ALTER WAREHOUSE AIRSIGHT_WH SET RESOURCE_MONITOR=AIRSIGHT_RM;

CREATE DATABASE IF NOT EXISTS AIRSIGHT;
CREATE SCHEMA IF NOT EXISTS AIRSIGHT.RAW;      CREATE SCHEMA IF NOT EXISTS AIRSIGHT.RAW_DEV;
CREATE SCHEMA IF NOT EXISTS AIRSIGHT.STAGING;  CREATE SCHEMA IF NOT EXISTS AIRSIGHT.MARTS;
CREATE SCHEMA IF NOT EXISTS AIRSIGHT.DEV_STAGING; CREATE SCHEMA IF NOT EXISTS AIRSIGHT.DEV_MARTS;
CREATE SCHEMA IF NOT EXISTS AIRSIGHT.OPS;

CREATE ROLE IF NOT EXISTS AIRBYTE_ROLE; CREATE ROLE IF NOT EXISTS TRANSFORM_ROLE; CREATE ROLE IF NOT EXISTS BI_ROLE;
GRANT USAGE ON WAREHOUSE AIRSIGHT_WH TO ROLE AIRBYTE_ROLE;
GRANT USAGE ON WAREHOUSE AIRSIGHT_WH TO ROLE TRANSFORM_ROLE;
GRANT USAGE ON WAREHOUSE AIRSIGHT_WH TO ROLE BI_ROLE;
GRANT USAGE ON DATABASE AIRSIGHT TO ROLE AIRBYTE_ROLE;
GRANT USAGE ON DATABASE AIRSIGHT TO ROLE TRANSFORM_ROLE;
GRANT USAGE ON DATABASE AIRSIGHT TO ROLE BI_ROLE;
GRANT CREATE SCHEMA ON DATABASE AIRSIGHT TO ROLE AIRBYTE_ROLE;   -- Airbyte makes airbyte_internal

-- Ownership
GRANT OWNERSHIP ON SCHEMA AIRSIGHT.RAW TO ROLE AIRBYTE_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AIRSIGHT.OPS TO ROLE AIRBYTE_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AIRSIGHT.RAW_DEV     TO ROLE TRANSFORM_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AIRSIGHT.STAGING     TO ROLE TRANSFORM_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AIRSIGHT.MARTS       TO ROLE TRANSFORM_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AIRSIGHT.DEV_STAGING TO ROLE TRANSFORM_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AIRSIGHT.DEV_MARTS   TO ROLE TRANSFORM_ROLE COPY CURRENT GRANTS;

-- dbt reads RAW (incl. tables Airbyte replaces later)
GRANT USAGE ON SCHEMA AIRSIGHT.RAW TO ROLE TRANSFORM_ROLE;
GRANT SELECT ON ALL TABLES    IN SCHEMA AIRSIGHT.RAW TO ROLE TRANSFORM_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA AIRSIGHT.RAW TO ROLE TRANSFORM_ROLE;

-- BI reads marts only
GRANT USAGE ON SCHEMA AIRSIGHT.MARTS     TO ROLE BI_ROLE;
GRANT USAGE ON SCHEMA AIRSIGHT.DEV_MARTS TO ROLE BI_ROLE;
GRANT SELECT ON ALL TABLES    IN SCHEMA AIRSIGHT.MARTS     TO ROLE BI_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA AIRSIGHT.MARTS     TO ROLE BI_ROLE;
GRANT SELECT ON ALL TABLES    IN SCHEMA AIRSIGHT.DEV_MARTS TO ROLE BI_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA AIRSIGHT.DEV_MARTS TO ROLE BI_ROLE;

-- Users (if TYPE=LEGACY_SERVICE errors on your account, drop that clause; if password login is refused, use key-pair)
CREATE USER IF NOT EXISTS AIRBYTE_USER PASSWORD='<<PW>>' DEFAULT_ROLE=AIRBYTE_ROLE   DEFAULT_WAREHOUSE=AIRSIGHT_WH MUST_CHANGE_PASSWORD=FALSE TYPE=LEGACY_SERVICE;
CREATE USER IF NOT EXISTS DBT_USER    PASSWORD='<<PW>>' DEFAULT_ROLE=TRANSFORM_ROLE DEFAULT_WAREHOUSE=AIRSIGHT_WH MUST_CHANGE_PASSWORD=FALSE TYPE=LEGACY_SERVICE;
CREATE USER IF NOT EXISTS BI_USER     PASSWORD='<<PW>>' DEFAULT_ROLE=BI_ROLE        DEFAULT_WAREHOUSE=AIRSIGHT_WH MUST_CHANGE_PASSWORD=FALSE TYPE=LEGACY_SERVICE;
GRANT ROLE AIRBYTE_ROLE   TO USER AIRBYTE_USER;
GRANT ROLE TRANSFORM_ROLE TO USER DBT_USER;
GRANT ROLE BI_ROLE        TO USER BI_USER;

-- OPS tables (B's validation + failure logging)
CREATE TABLE IF NOT EXISTS AIRSIGHT.OPS.INGESTION_LOG (run_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP, row_count NUMBER, city_count NUMBER, min_date DATE, max_date DATE, null_report VARIANT, status STRING);
CREATE TABLE IF NOT EXISTS AIRSIGHT.OPS.PIPELINE_ERRORS (ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP, dag_id STRING, task_id STRING, run_id STRING, message STRING);
```
(OPS tables are created by R as ACCOUNTADMIN → run `GRANT OWNERSHIP ON ALL TABLES IN SCHEMA AIRSIGHT.OPS TO ROLE AIRBYTE_ROLE COPY CURRENT GRANTS;` after creating them.)

---

## 9. Optional stretch — Open-Meteo (only after §6/§7 are green)

- **B**: Airbyte Cloud *Connector Builder* source: `https://air-quality-api.open-meteo.com/v1/air-quality` with `latitude/longitude` per city, `hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi`, `past_days=30`. Land in `RAW.OPENMETEO_HOURLY`; add to the same connection/DAG. No key needed.
- **R**: add `stg_openmeteo_hourly.sql` (aggregate to daily) and a **separate** `mart_recent_air_quality` — do **not** union it into the CSV marts (modelled data, US-AQI scale ≠ CPCB scale; label it "recent, modelled").
- Skip entirely if time is short; it is not required by the guide.

---

## 10. Timeline (hours from now; both tracks run in parallel)

| T+ | Baibhav | Rahul | Sync |
|---|---|---|---|
| 0:00–0:20 | B1–B4 repo, CSV, scaffold, Airbyte source | R1–R3 Snowflake, setup SQL, Gemini key | **H1/H3 R→B**, **H2 B→R** |
| 0:20–2:00 | B5–B8 destination, first sync, validation script, Airbyte API task | R4–R7 dev data, dbt scaffold, staging, tests | **H4 B→R** ≈ T+2 |
| 2:00–3:30 | B9–B11 Airflow image + DAG | R8–R10 marts, start Streamlit, push transformation.py | **H5 R→B** ≈ T+3:30 |
| 3:30–5:00 | B12–B14 integrate, failure tests, monitoring | R10–R12 finish chat, validation, prod switch | **H6/H7** ≈ T+4:30 |
| 5:00–7:00 (tonight or tomorrow AM) | B15 compile report, README | R13 report, rehearsal | final merge |
| 16th | buffer, backup video/screenshots, rehearse | same | demo |

---

## 11. Definition of done / demo script

1. `airsight_pipeline` triggered in Airflow UI → all tasks green (Airbyte sync → validate → dbt run → dbt test).
2. Snowsight shows `RAW.CITY_DAY`, `STAGING.STG_CITY_DAY`, three `MARTS` tables, `OPS.INGESTION_LOG`.
3. dbt test output shows pass + the documented "allowed missing values".
4. Streamlit: ask (a) "Which are the 5 most polluted cities?" (b) "Compare Delhi and Mumbai AQI over the years" (c) "Which month is worst in Delhi?" (d) "How did lockdown 2020 change Delhi's AQI?" — show SQL + chart.
5. Failure demo (optional): break the Airbyte connection ID → retries → `PIPELINE_ERRORS` row.
6. Backup: 2-minute screen recording + screenshots in `docs/screenshots/` in case Wi-Fi/trial hiccups.

## 12. Report mapping (faculty format)

| Section | Author |
|---|---|
| Cover, TOC, Abstract, 1 Problem & Objective, 5 Conclusion | B drafts, R reviews |
| 2 Architecture & Tech Stack (diagram §2) | B |
| 3 Implementation: Ingestion, Orchestration | B |
| 3 Implementation: Transformation, Warehouse & BI | R |
| 4 Key Results & Demo Output | B (pipeline, counts, DAG) + R (marts, chat answers) |

## 13. Risks & fallbacks

| Risk | Fallback |
|---|---|
| Snowflake refuses password users | Key-pair auth for that user (Airbyte, dbt and the Python connector all support it) |
| Airbyte column names differ from CSV headers | Fix only `renamed` CTE in `stg_city_day.sql` |
| Airbyte trial/credits problem | Load CSV via `dev_tools/load_dev_raw.py`-style script into `RAW` and document Airbyte screenshots already captured |
| Airflow too heavy on 8 GB | Codespaces with the same compose file |
| Gemini quota/key issue | `rules.py` fallback activates automatically |
| Snowflake trial ends (30 days) | Pipeline is fully reproducible from git + setup SQL; re-demo window is fine |
