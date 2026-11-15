"""Bound, deterministic queries for the visual data explorer."""
from rules import Query
from schema_context import CITIES, namespace

VIEWS = ['City trend', 'Compare cities', 'City rankings', 'Seasonal pattern', 'City heatmap']


def build_explorer_query(view: str, cities: list[str], years: tuple[int, int], top_n: int = 10,
                         cleanest: bool = False) -> Query:
    if view not in VIEWS:
        raise ValueError('Choose a supported analysis.')
    if not cities or any(city not in CITIES for city in cities):
        raise ValueError('Choose at least one city from the dataset.')
    start, end = years
    if not 2015 <= start <= end <= 2020:
        raise ValueError('Choose years between 2015 and 2020.')
    database, schema = namespace()
    city_filter = ', '.join('?' for _ in cities)
    params = tuple(cities) + (start, end)
    monthly = f'{database}.{schema}.MART_MONTHLY_CITY_SUMMARY'
    where = f'city in ({city_filter}) and year(month_start) between ? and ?'
    if view == 'City trend':
        if len(cities) != 1:
            raise ValueError('Choose one city for a monthly trend.')
        return Query(
            'select city, month_start, avg_aqi, rolling_3_month_avg, days_measured '
            f'from {database}.{schema}.MART_POLLUTION_TRENDS where {where} order by month_start',
            params, 'trend')
    if view == 'Compare cities':
        if not 2 <= len(cities) <= 3:
            raise ValueError('Choose two or three cities to compare.')
        return Query(
            'select city, year, avg_aqi, days_measured '
            f'from {database}.{schema}.MART_CITY_RANKINGS '
            f"where period_scope = 'yearly' and city in ({city_filter}) and year between ? and ? "
            'order by year, city', params, 'compare')
    if view == 'City rankings':
        if not 1 <= top_n <= 26:
            raise ValueError('Choose between 1 and 26 results.')
        direction = 'asc' if cleanest else 'desc'
        return Query(
            'with selected as (select city, '
            'sum(avg_aqi * days_measured) / nullif(sum(days_measured), 0) as avg_aqi, '
            'sum(days_measured) as days_measured, '
            '100.0 * sum(unhealthy_day_share * days_measured) / nullif(sum(days_measured), 0) as pct_unhealthy_days '
            f'from {monthly} where {where} group by city having sum(days_measured) > 0) '
            'select city, avg_aqi, dense_rank() over(order by avg_aqi desc) as pollution_rank, '
            f'days_measured, pct_unhealthy_days from selected order by avg_aqi {direction}, city limit {top_n}',
            params, 'ranking')
    if view == 'Seasonal pattern':
        if len(cities) != 1:
            raise ValueError('Choose one city for a seasonal pattern.')
        return Query(
            'select month(month_start) as month, '
            'sum(avg_aqi * days_measured) / nullif(sum(days_measured), 0) as avg_aqi, '
            f'sum(days_measured) as days_measured from {monthly} where {where} '
            'group by month(month_start) having sum(days_measured) > 0 order by avg_aqi desc, month',
            params, 'monthly')
    columns = ', '.join(
        f'sum(case when month(month_start) = {month} then avg_aqi * days_measured end) '
        f'/ nullif(sum(case when month(month_start) = {month} then days_measured end), 0) as m{month:02d}'
        for month in range(1, 13)
    )
    return Query(f'select city, {columns} from {monthly} where {where} group by city order by city',
                 params, 'heatmap')


def explorer_title(view: str, cities: list[str], years: tuple[int, int]) -> str:
    selected = ', '.join(city.title() for city in cities) if len(cities) <= 3 else f'{len(cities)} cities'
    return f'{view} · {selected} · {years[0]}–{years[1]}'
