"""Compare five app answers under BI_ROLE to hand-written staging SQL."""
from pathlib import Path
import argparse
import os

import pandas as pd
import snowflake.connector

from service import answer
from schema_context import namespace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema', choices=['DEV_MARTS', 'MARTS'], default='DEV_MARTS')
    args = parser.parse_args()
    os.environ['MARTS_SCHEMA'] = args.schema
    database, _ = namespace()
    staging = 'STAGING' if args.schema == 'MARTS' else 'DEV_STAGING'
    source = f'{database}.{staging}.STG_CITY_DAY'
    cases = [
        ('Which are the 5 most polluted cities?',
         f"select city, avg(aqi) as avg_aqi, dense_rank() over(order by avg(aqi) desc nulls last) as pollution_rank, "
         f"count(aqi) as days_measured, 100.0 * count_if(aqi is not null and aqi_bucket in ('Poor','Very Poor','Severe')) "
         f"/ nullif(count(aqi),0) as pct_unhealthy_days from {source} group by city having count(aqi)>0 order by avg_aqi desc, city limit 5"),
        ('Compare Delhi and Mumbai AQI over the years',
         f"select city, year, avg(aqi) as avg_aqi, count(aqi) as days_measured from {source} "
         "where city in ('DELHI','MUMBAI') group by city, year order by year, city"),
        ('Show the pollution trend for Delhi',
         f"with monthly as (select city, date_trunc('month',date)::date as month_start, avg(aqi) as avg_aqi, "
         f"count(aqi) as days_measured from {source} where city='DELHI' group by city,date_trunc('month',date)) "
         "select city, month_start, avg_aqi, avg(avg_aqi) over(order by month_start rows between 2 preceding and current row) "
         "as rolling_3_month_avg, days_measured from monthly order by month_start"),
        ('Which month is worst in Delhi?',
         f"select month, avg(aqi) as avg_aqi, count(aqi) as days_measured from {source} where city='DELHI' "
         "group by month having count(aqi)>0 order by avg_aqi desc, month"),
        ("How did lockdown 2020 change Delhi's AQI?",
         f"select year, avg(aqi) as avg_aqi, count(aqi) as days_measured from {source} "
         "where city='DELHI' and year in (2019,2020) and month between 3 and 5 group by year order by year"),
    ]
    entries = []
    with snowflake.connector.connect(
        account=os.environ['SNOWFLAKE_ACCOUNT'], user=os.getenv('DBT_USER', 'DBT_USER'),
        password=os.environ['DBT_PASSWORD'], role='TRANSFORM_ROLE', database=database,
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'AIRSIGHT_WH'), login_timeout=20, network_timeout=60,
    ) as connection:
        with connection.cursor() as cursor:
            for question, sql in cases:
                result = answer(question, use_gemini=False)
                cursor.execute(sql)
                expected = pd.DataFrame(cursor.fetchall(), columns=[item[0].lower() for item in cursor.description])
                actual = result.frame.copy()
                for column in expected:
                    if column == 'month_start':
                        expected[column] = pd.to_datetime(expected[column])
                        actual[column] = pd.to_datetime(actual[column])
                    elif column != 'city':
                        expected[column] = pd.to_numeric(expected[column]).astype(float)
                        actual[column] = pd.to_numeric(actual[column]).astype(float)
                pd.testing.assert_frame_equal(expected, actual, check_dtype=False, check_exact=False, rtol=1e-8, atol=1e-8)
                preview = ', '.join(f'{key}={value}' for key, value in expected.iloc[0].to_dict().items())
                print(f'PASS {args.schema}: {question} ({len(actual)} rows)')
                entries.append((question, len(actual), preview, sql))
    report = Path(__file__).resolve().parents[1] / 'docs/report/R_sections.md'
    with report.open('a') as handle:
        handle.write(f'\n## Five-question SQL/app validation — {args.schema}, 2026-11-14\n\n')
        handle.write('App queries ran as BI_USER/BI_ROLE; independent staging SQL ran as DBT_USER/TRANSFORM_ROLE. Gemini was disabled for reproducible fallback validation. All numeric values matched within 1e-8 tolerance.\n\n')
        handle.write('| Question | SQL result | App result | Match |\n|---|---|---|---|\n')
        for question, count, preview, _ in entries:
            handle.write(f'| {question} | {count} rows; first: {preview} | Same values and row order | Yes |\n')
        handle.write('\nHand-written reference queries:\n')
        for question, _, _, sql in entries:
            handle.write(f'\n{question}\n\n```sql\n{sql}\n```\n')


if __name__ == '__main__':
    main()
