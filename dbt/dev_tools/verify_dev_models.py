"""Compare dev mart results with independent pandas calculations on the CSV."""
from pathlib import Path
import logging
import os

from dotenv import load_dotenv
import pandas as pd
import snowflake.connector

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    load_dotenv(ROOT / '.env', interpolate=False)
    source = pd.read_csv(ROOT / 'data/city_day.csv')
    source['city'] = source.City.str.strip().str.upper()
    source['month_start'] = pd.to_datetime(source.Date).dt.to_period('M').dt.to_timestamp()
    source['aqi'] = source.AQI.where(source.AQI.between(0, 1000))
    source['excluded'] = source.AQI.notna() & ~source.AQI.between(0, 1000)
    monthly = source.groupby(['city', 'month_start']).agg(
        avg_aqi=('aqi', 'mean'), days_recorded=('aqi', 'size'),
        days_measured=('aqi', 'count'), excluded_aqi_days=('excluded', 'sum'),
    ).reset_index()
    ranking = source.groupby('city').agg(avg_aqi=('aqi', 'mean')).reset_index()
    ranking['pollution_rank'] = ranking.avg_aqi.rank(method='dense', ascending=False)

    with snowflake.connector.connect(
        account=os.environ['SNOWFLAKE_ACCOUNT'], user=os.getenv('DBT_USER', 'DBT_USER'),
        password=os.environ['DBT_PASSWORD'], role='TRANSFORM_ROLE',
        database=os.getenv('SNOWFLAKE_DATABASE', 'AIRSIGHT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'AIRSIGHT_WH'),
        login_timeout=20, network_timeout=60,
    ) as connection:
        with connection.cursor() as cursor:
            def query(sql: str) -> pd.DataFrame:
                cursor.execute(sql)
                result = cursor.fetch_pandas_all()
                result.columns = result.columns.str.lower()
                return result

            actual = query('select city, month_start, avg_aqi, days_recorded, days_measured, '
                           'excluded_aqi_days from DEV_MARTS.MART_MONTHLY_CITY_SUMMARY')
            actual['month_start'] = pd.to_datetime(actual.month_start)
            pd.testing.assert_frame_equal(
                monthly.sort_values(['city', 'month_start']).reset_index(drop=True),
                actual.sort_values(['city', 'month_start']).reset_index(drop=True),
                check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-9,
            )
            print(f'PASS: all {len(monthly)} monthly city averages and coverage counts match CSV calculations')
            actual_ranking = query("select city, avg_aqi, pollution_rank from DEV_MARTS.MART_CITY_RANKINGS "
                                   "where period_scope = 'overall'")
            pd.testing.assert_frame_equal(
                ranking.sort_values('city').reset_index(drop=True),
                actual_ranking.sort_values('city').reset_index(drop=True),
                check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-9,
            )
            print(f'PASS: all {len(ranking)} overall city averages and ranks match CSV calculations')
            parts = []
            for city, group in monthly.groupby('city'):
                series = group.set_index('month_start').avg_aqi.asfreq('MS')
                parts.append(pd.DataFrame({
                    'city': city, 'month_start': series.index, 'avg_aqi': series.values,
                    'rolling_3_month_avg': series.rolling(3, min_periods=1).mean().values,
                    'yoy_change': (series - series.shift(12)).values,
                }))
            expected_trends = pd.concat(parts, ignore_index=True)
            actual_trends = query('select city, month_start, avg_aqi, rolling_3_month_avg, yoy_change '
                                  'from DEV_MARTS.MART_POLLUTION_TRENDS')
            actual_trends['month_start'] = pd.to_datetime(actual_trends.month_start)
            pd.testing.assert_frame_equal(
                expected_trends.sort_values(['city', 'month_start']).reset_index(drop=True),
                actual_trends.sort_values(['city', 'month_start']).reset_index(drop=True),
                check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-9,
            )
            print(f'PASS: all {len(expected_trends)} monthly trends, rolling averages and YoY changes match CSV calculations')
            print(f'Approved AQI exclusions: {int(source.excluded.sum())}; original readings retained in staging')


if __name__ == '__main__':
    logging.getLogger('snowflake.connector').setLevel(logging.WARNING)
    main()
