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
