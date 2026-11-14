# Rahul — Warehouse, transformation and analytics

## Database design

The implementation follows the repository's Snowflake warehouse architecture.
RAW holds production ingestion and RAW_DEV holds a development CSV copy. dbt's
development target writes DEV_STAGING views and DEV_MARTS tables; production
writes STAGING and MARTS. AIRBYTE_ROLE loads data, TRANSFORM_ROLE builds models,
and BI_ROLE can read the marts. Warehouse AIRSIGHT_WH is X-Small with a configured
60-second auto-suspend. Application credentials remain outside version control.

## Cleaning and data-quality policy

The 29,531-row CSV covers 26 cities from 2015-01-01 to 2020-07-01. Raw headers
and source readings are retained. Staging standardizes city labels, converts date
and numeric fields defensively, and enforces one city/date row. No missing
pollutant measurements are imputed. The source has 4,681 missing AQI readings
and 93 numeric readings above the project's specified upper limit of 1,000.

On 2026-11-14 Rahul approved retaining original AQI in `aqi_reported`, marking
out-of-range values with `aqi_out_of_range`, and excluding these values from the
cleaned AQI field and AQI-derived averages/shares. The corresponding original
bucket is also retained separately. This policy does not remove rows or other
pollutant values, and does not establish that the source readings are erroneous.

dbt tests cover null city/date/keys, duplicate keys, accepted buckets/seasons,
negative pollutant readings, PM2.5 > 1,500, cleaned AQI outside 0–1,000, future
dates, preservation of flagged measurements, raw-to-staging city/date coverage,
and reconciliation of monthly summaries to daily readings. All 26 tests passed
against the development models on 2026-11-14.

## Analytical marts

| Mart | Grain and interpretation |
|---|---|
| mart_monthly_city_summary | City and month; AQI/pollutant means, maximum AQI, usable and excluded coverage, unhealthy share |
| mart_pollution_trends | City and calendar month; equal-weight monthly rolling average over three calendar months, same-month YoY change and broad season |
| mart_city_rankings | City and period_scope, plus year for yearly rows; daily-weighted mean AQI, pollution rank, best/worst observed month and unhealthy percentage |

Ranks must be filtered by period_scope to avoid mixing overall and yearly results.
AQI averages ignore missing/flagged AQI, and coverage is shown explicitly. Rolling
averages ignore null monthly means and report how many months contribute.
Different historical coverage and seasonal climates limit city comparability.

## Development verification evidence

Four dbt models built successfully. Independent pandas calculations from the
original CSV matched all 1,005 monthly city summaries (AQI averages and coverage
counts), all 26 overall city averages and dense ranks, and all 1,005 monthly trend
rows (AQI, three-month rolling mean and same-calendar-month YoY differences).
Reproduce with `dbt/dev_tools/verify_dev_models.py` after the development build.

Production verification, the Streamlit interface, charts and the five-question
SQL-versus-app validation are pending. Development results are not evidence of
completed Airbyte/Airflow integration.
