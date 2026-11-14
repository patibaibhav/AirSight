"""Deterministic natural-language intents with bound query parameters."""
from dataclasses import dataclass
import re

from schema_context import CITIES, namespace


@dataclass(frozen=True)
class Query:
    sql: str
    params: tuple = ()
    intent: str = 'custom'


def cities_in(question: str) -> list[str]:
    text = question.upper().replace('BANGALORE', 'BENGALURU').replace('GURGAON', 'GURUGRAM')
    return sorted([city for city in CITIES if re.search(r'\b' + re.escape(city) + r'\b', text)],
                  key=text.index)


def build_query(question: str) -> Query:
    text = question.lower()
    cities = cities_in(question)
    years = tuple(sorted(set(int(value) for value in re.findall(r'\b20\d{2}\b', text))))
    if re.search(r'\b(pm2\.?5|pm10|no2|ozone|carbon monoxide|benzene)\b', text):
        raise ValueError('Rule-based questions currently cover AQI. Enable Gemini for other pollutant questions.')
    if any(word in text for word in ('compare', 'versus', ' vs ')) and len(cities) < 2 and 'lockdown' not in text:
        raise ValueError('For a city comparison, name two cities from the dataset, such as Delhi and Mumbai.')
    database, schema = namespace()
    table = lambda name: f'{database}.{schema}.{name}'
    if 'heatmap' in text:
        # 26 x 12 rows fit the 200-row cap by returning twelve month columns per city.
        columns = ', '.join(
            f'sum(case when month(month_start) = {month} then avg_aqi * days_measured end) '
            f'/ nullif(sum(case when month(month_start) = {month} then days_measured end), 0) as m{month:02d}'
            for month in range(1, 13)
        )
        return Query(f'select city, {columns} from {table("MART_MONTHLY_CITY_SUMMARY")} group by city order by city', intent='heatmap')
    if 'lockdown' in text and cities:
        return Query(
            f'select year(month_start) as year, sum(avg_aqi * days_measured) / nullif(sum(days_measured), 0) as avg_aqi, '
            f'sum(days_measured) as days_measured from {table("MART_MONTHLY_CITY_SUMMARY")} '
            'where city = ? and year(month_start) in (2019, 2020) and month(month_start) between 3 and 5 '
            'group by year(month_start) order by year', (cities[0],), 'lockdown')
    if len(cities) >= 2 and any(word in text for word in ('compare', 'versus', ' vs ', 'and')):
        year_filter = (' and year in (' + ', '.join('?' for _ in years) + ')') if years else ''
        return Query(
            f'select city, year, avg_aqi, days_measured from {table("MART_CITY_RANKINGS")} '
            "where period_scope = 'yearly' and city in (?, ?)" + year_filter + ' order by year, city',
            tuple(cities[:2]) + years, 'compare')
    if cities and ('month' in text or 'season' in text) and not ('trend' in text or 'over time' in text):
        direction = 'asc' if any(word in text for word in ('best', 'cleanest', 'lowest')) else 'desc'
        year_filter = (' and year(month_start) in (' + ', '.join('?' for _ in years) + ')') if years else ''
        return Query(
            f'select month(month_start) as month, sum(avg_aqi * days_measured) / nullif(sum(days_measured), 0) as avg_aqi, '
            f'sum(days_measured) as days_measured from {table("MART_MONTHLY_CITY_SUMMARY")} '
            'where city = ?' + year_filter + ' group by month(month_start) having sum(days_measured) > 0 '
            f'order by avg_aqi {direction}, month', (cities[0],) + years, 'monthly')
    if cities:
        year_filter = (' and year in (' + ', '.join('?' for _ in years) + ')') if years else ''
        return Query(
            f'select city, month_start, avg_aqi, rolling_3_month_avg, days_measured '
            f'from {table("MART_POLLUTION_TRENDS")} where city = ?' + year_filter + ' order by month_start',
            (cities[0],) + years, 'trend')
    if any(word in text for word in ('cities', 'ranking', 'polluted', 'cleanest')):
        match = re.search(r'\b([1-9][0-9]?)\b', text)
        limit = min(int(match.group(1)), 26) if match else 5
        direction = 'asc' if any(word in text for word in ('best', 'cleanest', 'least', 'lowest')) else 'desc'
        return Query(
            f'select city, avg_aqi, pollution_rank, days_measured, pct_unhealthy_days '
            f'from {table("MART_CITY_RANKINGS")} where period_scope = \'overall\' and avg_aqi is not null '
            f'order by avg_aqi {direction}, city limit {limit}', intent='ranking')
    raise ValueError('Try a sample question, or name a city for a monthly pollution trend.')
