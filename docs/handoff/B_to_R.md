# Handoff: Baibhav → Rahul (append-only, owner: B)

Entry format: `## YYYY-MM-DD HH:MM — H# title` then what / columns / needs from you.

## 2026-11-14 — H2 scaffold pushed
- what: repo scaffold with folders, stubs, AGENTS.md, PLAN.md, `.env.example`, `sql/00_setup_snowflake.sql` (data/city_day.csv follows in a later commit once downloaded)
- needs from you: clone, create local `.env`, then PLAN.md §7 R3 onward

## 2026-11-14 18:30 — FYI Airflow image ready (dbt versions)
- what: Airflow runs locally; DAG `airsight_pipeline` green on stubs. dbt lives in a separate venv inside the image.
- versions in the image: dbt-core 1.12.7, dbt-snowflake 1.9.0 (pin the same locally to avoid surprises)
- Airbyte source `airsight-city-day` (File, CSV, GitHub raw URL) is created; destination waits for your Snowflake credentials (H1/H3)
- needs from you: transformation.py later (contract in the file docstring); nothing else blocks me now

## 2026-11-14 21:25 — H4 RAW landed
- what: `AIRSIGHT.RAW.CITY_DAY` loaded by Airbyte Cloud (full-refresh overwrite), **29,531 rows, 26 cities, dates 2015-01-01 to 2020-07-01**. `validate_raw.py` PASSED (logged in OPS.INGESTION_LOG).
- columns (exact, all UPPERCASE, in Snowflake): `CITY` TEXT, `DATE` TEXT ('YYYY-MM-DD' string, NOT a date type), `PM2.5` FLOAT (name contains a dot, needs quoting as "PM2.5"), `PM10`, `NO`, `NO2`, `NOX`, `NH3`, `CO`, `SO2`, `O3`, `BENZENE`, `TOLUENE`, `XYLENE`, `AQI` (all FLOAT), `AQI_BUCKET` TEXT. Plus Airbyte metadata: `_AIRBYTE_RAW_ID`, `_AIRBYTE_EXTRACTED_AT`, `_AIRBYTE_META`, `_AIRBYTE_GENERATION_ID` (ignore these).
- differences vs the CSV headers: names are uppercased (`Date`->`DATE`, `NOx`->`NOX`, `AQI_Bucket`->`AQI_BUCKET`); pollutants arrive already typed FLOAT, empties are NULL.
- null % (so tests can set expectations): PM10 37.7, XYLENE 61.3, NH3 35.0, TOLUENE 27.2, BENZENE 19.0, AQI/AQI_BUCKET 15.9, PM2.5 15.6, O3 13.6, NOX 14.2, SO2 13.1, NO2 12.1, NO 12.1, CO 7.0, CITY 0, DATE 0.
- needs from you: if `RAW_DEV` columns differ from these (e.g. mixed case), align your `load_dev_raw.py` to this exact shape, then run `dbt run/test --target prod` once and fix only the `renamed` CTE if needed.
