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
