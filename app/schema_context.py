"""Shared warehouse contract and prompt context."""
import os
import re

CITIES = [
    'AHMEDABAD', 'AIZAWL', 'AMARAVATI', 'AMRITSAR', 'BENGALURU', 'BHOPAL',
    'BRAJRAJNAGAR', 'CHANDIGARH', 'CHENNAI', 'COIMBATORE', 'DELHI', 'ERNAKULAM',
    'GURUGRAM', 'GUWAHATI', 'HYDERABAD', 'JAIPUR', 'JORAPOKHAR', 'KOCHI',
    'KOLKATA', 'LUCKNOW', 'MUMBAI', 'PATNA', 'SHILLONG', 'TALCHER',
    'THIRUVANANTHAPURAM', 'VISAKHAPATNAM',
]
TABLES = {
    'MART_MONTHLY_CITY_SUMMARY': 'city_month_key, city, month_start DATE, avg_aqi, max_aqi, avg_pm25, avg_pm10, avg_no2, avg_o3, avg_co, days_recorded, days_measured, excluded_aqi_days, missing_aqi_days, unhealthy_day_share (0–1)',
    'MART_POLLUTION_TRENDS': 'city_month_key, city, month_start DATE, year, month, avg_aqi, days_measured, rolling_3_month_avg, rolling_months_measured, prior_year_avg_aqi, yoy_change, yoy_change_pct, season',
    'MART_CITY_RANKINGS': 'ranking_key, city, period_scope (overall/yearly), year (NULL for overall), avg_aqi, pollution_rank (1=worst), days_recorded, days_measured, excluded_aqi_days, pct_unhealthy_days (0–100), best_month DATE, worst_month DATE',
}
SAMPLES = [
    'Which are the 5 most polluted cities?',
    'Compare Delhi and Mumbai AQI over the years',
    'Show the pollution trend for Delhi',
    'Which month is worst in Delhi?',
    "How did lockdown 2020 change Delhi's AQI?",
    'Show a city month heatmap',
]


def namespace() -> tuple[str, str]:
    database = os.getenv('SNOWFLAKE_DATABASE', 'AIRSIGHT').upper()
    schema = os.getenv('MARTS_SCHEMA', 'DEV_MARTS').upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*', database) or schema not in {'MARTS', 'DEV_MARTS'}:
        raise ValueError('Invalid warehouse configuration')
    return database, schema


def schema_prompt() -> str:
    database, schema = namespace()
    tables = '\n'.join(f'{database}.{schema}.{name}: {columns}' for name, columns in TABLES.items())
    return f'''Return exactly one Snowflake SELECT query, optionally with CTEs. No Markdown.
Read only these fully qualified tables; do not use functions with side effects or external access.
{tables}
Cities are uppercase: {', '.join(CITIES)}.
Historical data covers January 2015 to July 1, 2020. Coverage varies by city.
AQI missing and outside 0–1000 is excluded from means (93 flagged readings retained in staging).
AQI categories: Good, Satisfactory, Moderate, Poor, Very Poor, Severe.
Use period_scope='overall' for overall rankings and 'yearly' for annual comparisons.
For seasonal month patterns across years, weight monthly AQI by days_measured.
Use month_start for monthly trends. Months with no usable observations remain NULL.
Never claim a causal lockdown effect: compare March–May 2019 with March–May 2020 descriptively.
Alias result columns with simple lowercase names. Include LIMIT 200 or less.
'''
