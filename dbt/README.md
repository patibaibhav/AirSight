# Rahul's local environment

Python 3.11 is installed in `dbt/.venv` using the existing Anaconda installation.
Run commands from the repository root; activation is optional when using these paths.

```sh
dbt/.venv/bin/python -m pip install -r dbt/requirements.txt
dbt/.venv/bin/python dbt/dev_tools/configure_credentials.py
dbt/.venv/bin/python dbt/dev_tools/check_connection.py
dbt/.venv/bin/python dbt/dev_tools/load_dev_raw.py
```

The configuration prompt hides password input and saves it only in the git-ignored
root `.env`, with owner-only file permissions. Enter the DBT_USER and BI_USER
passwords created in Snowsight. Do not enter your administrator password.
The connection check reads `.env` without variable interpolation, checks both
application users and their active roles, and does not modify warehouse data.

Versions: dbt-core 1.12.7, dbt-snowflake 1.9.0 (matching B's handoff).
App dependencies are pinned in `app/requirements.txt`. python-dotenv (already
required by dbt) loads local configuration; pyarrow supports pandas CSV uploads.

Development will read RAW_DEV and write DEV_STAGING/DEV_MARTS. Production
integration awaits B's RAW landed handoff. The loader creates only RAW_DEV.CITY_DAY,
retains original headers, loads raw fields as strings, and preserves missing values.
On repeat runs it validates the existing table's summary and headers without adding
rows or replacing data. Summary checks do not establish full row-by-row equality.

Verified development load: 29,531 rows, 26 cities, 2015-01-01 through 2020-07-01.
Source quality: 4,681 missing AQI values and 93 AQI readings above 1,000. No negative
pollutant/AQI values or PM2.5 above 1,500 were found. Rahul approved flagging and
excluding out-of-range AQI from analytics. Staging retains `aqi_reported` and
`aqi_bucket_reported`, sets `aqi_out_of_range`, and nulls only the cleaned AQI and
bucket for those readings. Rows, raw data and other pollutant readings are retained.
This is an explicit project rule, not a claim that the original source is erroneous.

## Build and validate

```sh
dbt/.venv/bin/python dbt/dev_tools/run_dbt.py build --target dev
dbt/.venv/bin/python dbt/dev_tools/verify_dev_models.py
```

The runner loads local `.env` safely and supplies the project/profile paths.
Airflow will invoke dbt directly with environment variables supplied by its container.
Targets: dev reads RAW_DEV and writes DEV_STAGING/DEV_MARTS; prod reads RAW and
writes STAGING/MARTS. Do not run prod until B's exact-column H4 handoff is available.

Models:
- `stg_city_day`: city/date deduplication, defensive typing, original AQI plus flags.
- `mart_monthly_city_summary`: monthly averages and explicit usable/missing/excluded day counts.
- `mart_pollution_trends`: complete calendar months, equal-month-weight three-month
  rolling AQI and same-month YoY differences. Null months are not filled with data.
- `mart_city_rankings`: daily-weighted AQI averages at `period_scope='overall'` or
  `'yearly'`. Filter this field to avoid mixing grains; rank 1 is most polluted.

Unhealthy shares use Poor/Very Poor/Severe buckets among usable AQI readings.
Monthly shares are 0–1; ranking percentages are 0–100. Historical city/year coverage
differs, so comparisons are descriptive and not controlled causal comparisons.

Verified: all four models built; the complete 26-test suite passed. Independent
pandas comparisons passed for all 1,005 monthly summaries, 26 overall city ranks,
and 1,005 trend rows (monthly averages, rolling averages and YoY changes).
