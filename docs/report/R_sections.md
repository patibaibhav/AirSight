# Rahul — Warehouse, transformation and analytics

## 2026-11-15 interface update

The final interface adds a guided explorer alongside conversational questions.
Five analyses support explicit city/year selection: city trends, annual city
comparisons, rankings, seasonal patterns and a city/month heatmap. Ranking size
and ordering are configurable. All explorer values are calculated from existing
read-only marts; the warehouse model contracts remain unchanged.

Result cards display the submitted scope, fetch time, observed range summaries,
chart, expandable table/SQL and downloadable CSV/query. Recent questions retain
up to ten snapshots. A five-minute, twenty-entry session cache avoids repeating
identical requests, and the user can explicitly refresh explorer data. No warehouse
query runs at startup or merely because a filter is changed.

Validation: 17 offline tests passed for query boundaries, filtered scopes, cache
reuse/expiry/refresh, history/navigation and exports. The live Streamlit smoke
check exercised city comparison, heatmap, downloads and filtered rankings. All
five explorer analyses for a selected 2019 interval matched independent pandas
calculations on the original CSV, within numeric tolerance 1e-8. Report screenshots
remain manual; these results do not imply that screenshot files are complete.

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
and reconciliation of monthly summaries to daily readings. All 26 blocking tests
passed in development and production on 2026-11-14. A 27th, warning-only test
reports the 93 original out-of-range AQI readings without blocking the pipeline.

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

Production models were built successfully against Airbyte's RAW table. Development
headers were aligned to uppercase to match H4; no source readings were changed.
The real Airflow dbt run/test task group is implemented. Its Python syntax was
checked locally; B must confirm the full running DAG in his Airflow container.

## Conversational BI and visualizations

Streamlit accepts natural-language questions and displays a concise response,
generated SQL, bound city/year values, result table and chart. The six deterministic
sample intents cover rankings, two-city annual comparisons, city trends, seasonal
month patterns, a descriptive lockdown-period comparison and a 26-city heatmap.
Charts include rankings, grouped city bars, time-series lines and a month heatmap.

Gemini support reads its model and key from environment configuration. It receives
schema context and the question, never warehouse credentials or result rows. One
SQL-error correction is allowed before automatic fallback. Live Gemini validation
is pending credentials; the reproducible demo uses the rule-based path. Ten offline
tests cover query boundaries, injected SQL, CTE source checking, row limits,
fallback, a single model retry, parameter binding, requested years and chart shapes.

The parser permits one SELECT/WITH query on the configured marts, disallows
DDL/DML, table functions and unrecognized functions, and caps results at 200 rows.
Execution uses BI_USER/BI_ROLE with a 30-second statement timeout. This read-only
role is an additional boundary beyond SQL validation.

Live Streamlit AppTest verified the chat input, 12-row Delhi/Mumbai comparison,
heatmap sample button, 26-city result table and both rendered chart elements.
Native Chrome inspection also confirmed a live top-five-city question, table and
bar chart against production MARTS. Screenshot files and full Airflow run evidence
remain to be collected for the final report.

## Five-question SQL/app validation — MARTS, 2026-11-14

App queries ran as BI_USER/BI_ROLE; independent staging SQL ran as DBT_USER/TRANSFORM_ROLE. Gemini was disabled for reproducible fallback validation. All numeric values matched within 1e-8 tolerance.

| Question | SQL result | App result | Match |
|---|---|---|---|
| Which are the 5 most polluted cities? | 5 rows; first: city=AHMEDABAD, avg_aqi=388.34407735697016, pollution_rank=1.0, days_measured=1241.0, pct_unhealthy_days=80.499597 | Same values and row order | Yes |
| Compare Delhi and Mumbai AQI over the years | 12 rows; first: city=DELHI, year=2015.0, avg_aqi=297.02465753424656, days_measured=365.0 | Same values and row order | Yes |
| Show the pollution trend for Delhi | 67 rows; first: city=DELHI, month_start=2015-01-01 00:00:00, avg_aqi=342.2903225806452, rolling_3_month_avg=342.2903225806452, days_measured=31.0 | Same values and row order | Yes |
| Which month is worst in Delhi? | 12 rows; first: month=11.0, avg_aqi=401.9533333333333, days_measured=150.0 | Same values and row order | Yes |
| How did lockdown 2020 change Delhi's AQI? | 2 rows; first: year=2019.0, avg_aqi=217.5108695652174, days_measured=92.0 | Same values and row order | Yes |

Hand-written reference queries:

Which are the 5 most polluted cities?

```sql
select city, avg(aqi) as avg_aqi, dense_rank() over(order by avg(aqi) desc nulls last) as pollution_rank, count(aqi) as days_measured, 100.0 * count_if(aqi is not null and aqi_bucket in ('Poor','Very Poor','Severe')) / nullif(count(aqi),0) as pct_unhealthy_days from AIRSIGHT.STAGING.STG_CITY_DAY group by city having count(aqi)>0 order by avg_aqi desc, city limit 5
```

Compare Delhi and Mumbai AQI over the years

```sql
select city, year, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.STAGING.STG_CITY_DAY where city in ('DELHI','MUMBAI') group by city, year order by year, city
```

Show the pollution trend for Delhi

```sql
with monthly as (select city, date_trunc('month',date)::date as month_start, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.STAGING.STG_CITY_DAY where city='DELHI' group by city,date_trunc('month',date)) select city, month_start, avg_aqi, avg(avg_aqi) over(order by month_start rows between 2 preceding and current row) as rolling_3_month_avg, days_measured from monthly order by month_start
```

Which month is worst in Delhi?

```sql
select month, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.STAGING.STG_CITY_DAY where city='DELHI' group by month having count(aqi)>0 order by avg_aqi desc, month
```

How did lockdown 2020 change Delhi's AQI?

```sql
select year, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.STAGING.STG_CITY_DAY where city='DELHI' and year in (2019,2020) and month between 3 and 5 group by year order by year
```

## Five-question SQL/app validation — DEV_MARTS, 2026-11-14

App queries ran as BI_USER/BI_ROLE; independent staging SQL ran as DBT_USER/TRANSFORM_ROLE. Gemini was disabled for reproducible fallback validation. All numeric values matched within 1e-8 tolerance.

| Question | SQL result | App result | Match |
|---|---|---|---|
| Which are the 5 most polluted cities? | 5 rows; first: city=AHMEDABAD, avg_aqi=388.34407735697016, pollution_rank=1.0, days_measured=1241.0, pct_unhealthy_days=80.499597 | Same values and row order | Yes |
| Compare Delhi and Mumbai AQI over the years | 12 rows; first: city=DELHI, year=2015.0, avg_aqi=297.02465753424656, days_measured=365.0 | Same values and row order | Yes |
| Show the pollution trend for Delhi | 67 rows; first: city=DELHI, month_start=2015-01-01 00:00:00, avg_aqi=342.2903225806452, rolling_3_month_avg=342.2903225806452, days_measured=31.0 | Same values and row order | Yes |
| Which month is worst in Delhi? | 12 rows; first: month=11.0, avg_aqi=401.9533333333333, days_measured=150.0 | Same values and row order | Yes |
| How did lockdown 2020 change Delhi's AQI? | 2 rows; first: year=2019.0, avg_aqi=217.5108695652174, days_measured=92.0 | Same values and row order | Yes |

Hand-written reference queries:

Which are the 5 most polluted cities?

```sql
select city, avg(aqi) as avg_aqi, dense_rank() over(order by avg(aqi) desc nulls last) as pollution_rank, count(aqi) as days_measured, 100.0 * count_if(aqi is not null and aqi_bucket in ('Poor','Very Poor','Severe')) / nullif(count(aqi),0) as pct_unhealthy_days from AIRSIGHT.DEV_STAGING.STG_CITY_DAY group by city having count(aqi)>0 order by avg_aqi desc, city limit 5
```

Compare Delhi and Mumbai AQI over the years

```sql
select city, year, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.DEV_STAGING.STG_CITY_DAY where city in ('DELHI','MUMBAI') group by city, year order by year, city
```

Show the pollution trend for Delhi

```sql
with monthly as (select city, date_trunc('month',date)::date as month_start, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.DEV_STAGING.STG_CITY_DAY where city='DELHI' group by city,date_trunc('month',date)) select city, month_start, avg_aqi, avg(avg_aqi) over(order by month_start rows between 2 preceding and current row) as rolling_3_month_avg, days_measured from monthly order by month_start
```

Which month is worst in Delhi?

```sql
select month, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.DEV_STAGING.STG_CITY_DAY where city='DELHI' group by month having count(aqi)>0 order by avg_aqi desc, month
```

How did lockdown 2020 change Delhi's AQI?

```sql
select year, avg(aqi) as avg_aqi, count(aqi) as days_measured from AIRSIGHT.DEV_STAGING.STG_CITY_DAY where city='DELHI' and year in (2019,2020) and month between 3 and 5 group by year order by year
```
