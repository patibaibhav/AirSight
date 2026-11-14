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
pollutant/AQI values or PM2.5 above 1,500 were found. The planned AQI upper-bound
test needs explicit treatment during modeling; raw readings have not been altered.
