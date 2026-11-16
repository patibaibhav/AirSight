# Handoff: Rahul → Baibhav (append-only, owner: R)

Entry format: `## YYYY-MM-DD HH:MM — H# title` then what / needs from you.

## 2026-11-14 — Snowflake setup and local environment
- what: Rahul confirmed in Snowsight that the project schemas, three application users, and both OPS tables exist. Credentials are shared privately by Rahul, never through git.
- fix: custom roles are granted to SYSADMIN before schema ownership transfers in the setup SQL; this resolves ACCOUNTADMIN's OPS CREATE TABLE error encountered during setup.
- local: Python 3.11, dbt-core 1.12.7 and dbt-snowflake 1.9.0 installed; package consistency and app imports pass. Application login verification awaits Rahul's local credential entry.
- needs from you: test Airbyte destination access and publish H4 with exact RAW column names once loaded. Transformation group remains the stub until production validation.

## 2026-11-14 — R3/R4 local setup and development load verified
- what: DBT_USER/TRANSFORM_ROLE and BI_USER/BI_ROLE logins passed. Loaded RAW_DEV.CITY_DAY and verified 29,531 rows, 26 cities, date range 2015-01-01 to 2020-07-01, and all 16 original CSV column names. RAW was not modified.
- quality: source has 4,681 missing AQI readings and 93 AQI values above 1,000; preserved as received. This conflicts with the planned AQI upper-bound test and needs documented treatment during staging work.
- next: dbt staging, tests and marts against RAW_DEV; production integration still awaits H4.

## 2026-11-14 — R5–R8 development transformations verified
- what: staging view and all three marts built in DEV_STAGING/DEV_MARTS; complete dbt suite passes 26/26 tests. Independent CSV/pandas checks match 1,005 monthly summaries, 26 overall ranks and 1,005 trend rows.
- policy approved by Rahul: preserve aqi_reported/aqi_bucket_reported, flag aqi_out_of_range, and exclude numeric AQI outside 0–1,000 from cleaned aqi and AQI-derived analytics. All source rows and other pollutant readings remain. There are 93 exclusions and 4,681 missing AQI readings.
- marts: rankings include period_scope overall/yearly (filter before ranking comparisons); monthly unhealthy share is 0–1, ranking percentage 0–100. Dev run instructions and reproducible validation are in dbt/README.md.
- needs from you: H4 exact RAW column names and ingestion counts. This is NOT H5: production models are not yet validated, and transformation.py remains the stub until R9.

## 2026-11-14 — H5 dbt production-ready; real transformation tasks
- what: H4 consumed; RAW_DEV reloaded with uppercase headers to match Airbyte. Dev and prod dbt builds complete with zero errors: four models, 26 passing blocking tests and one expected AQI warning (93 preserved source readings).
- integration: airflow/dags/tasks/transformation.py now contains BashOperators for dbt run >> dbt test, group_id transform, --target prod, /opt/dbt-venv/bin/dbt and /opt/airflow/dbt paths. Pins remain dbt-core 1.12.7/dbt-snowflake 1.9.0. Syntax validated locally; full Airflow runtime awaits B's container run.
- needs from you: pull, restart/reload Airflow as appropriate, trigger the complete DAG and publish H7 evidence. The AQI WARN is intentional and dbt exits successfully. No missing-pollutant test failures are introduced.

## 2026-11-14 — BI app and SQL-validation handoff
- what: Streamlit rules/Gemini interface, SQL guardrail, four chart types and sample questions implemented. App runs locally with MARTS_SCHEMA=MARTS. Ten offline tests passed; live Streamlit chat/comparison and heatmap UI checks passed.
- validation: five sample answers matched hand-written staging SQL in both DEV_MARTS and MARTS, including row order and numeric tolerance. Full queries and results are recorded in docs/report/R_sections.md.
- run: pip install -r app/requirements.txt then streamlit run app/streamlit_app.py (from repo root); on Rahul's Mac: dbt/.venv/bin/python -m streamlit run app/streamlit_app.py. Local URL http://127.0.0.1:8501 is not remotely accessible to B.
- limitation: Gemini key/model are not configured or live-tested; deterministic natural-language fallback is demo-ready. H6 screenshot files are still pending; native browser verification succeeded but report screenshots have not been committed.

## 2026-11-15 — Dashboard UI and guided explorer improvements
- what: redesigned Streamlit layout, five city/year-filtered explorer views, result summaries, recent-question snapshots, CSV/SQL downloads and polished charts. Ranking size/order are configurable. Queries retain BI_ROLE, guardrail and row cap; no warehouse models or dependencies changed.
- efficiency: session-only result cache (five minutes, twenty entries), explicit explorer refresh, and no startup/background/filter-change queries. Filtered AQI aggregates are daily-weighted, and submitted scope/fetch time remain visible.
- verified: 17 offline tests, live chat/heatmap/export/explorer UI check, and all five year-filtered explorer analyses matching independent CSV calculations. H7 was pulled and confirmed from B's handoff; full Airflow integration is green.
- report: screenshots remain Rahul's manual task, per his request. Expand Result table and View generated SQL for report captures. Run command and local URL remain unchanged; Gemini remains optional and awaits live-key setup.

## 2026-11-16 — Header visibility fix
- what: added main-content clearance below Streamlit's fixed toolbar on desktop/mobile and increased the AIR QUALITY INTELLIGENCE label's size and line height.
- verified: native Chrome visual inspection confirms the entire label is visible below the toolbar. Styling-only change; data queries are unchanged.

## 2026-11-16 — Chat scope bugs fixed
- what: ranking questions now honor requested years with daily-weighted AQI, heatmaps honor requested cities/years, and inclusive year ranges include intervening years. Explicit separate years remain separate. Rule version now invalidates earlier cached query results.
- verified: 20 automated tests passed; three corrected chat answers match the validated production explorer (2020 top five: 5 rows; Delhi 2020 heatmap: 1 row; Delhi/Mumbai 2018–2020 comparison: 6 rows).
- Docker: installed locally but engine not running; no Docker/Airflow changes made. R's Python app/dbt do not require Docker.
