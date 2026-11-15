"""Check filtered explorer values against independent calculations on the source CSV."""
from pathlib import Path

import pandas as pd

from explorer import build_explorer_query
from service import execute


def main() -> None:
    source = pd.read_csv(Path(__file__).resolve().parents[1] / 'data/city_day.csv')
    source['city'] = source.City.str.upper().str.strip()
    source['year'] = pd.to_datetime(source.Date).dt.year
    source['month'] = pd.to_datetime(source.Date).dt.month
    source['month_start'] = pd.to_datetime(source.Date).dt.to_period('M').dt.to_timestamp()
    source['aqi'] = source.AQI.where(source.AQI.between(0, 1000))
    source['unhealthy'] = source.aqi.notna() & source.AQI_Bucket.isin(['Poor', 'Very Poor', 'Severe'])
    years = (2019, 2019)
    cities = ['DELHI', 'MUMBAI', 'BENGALURU']
    selected = source[source.city.isin(cities) & source.year.eq(2019)]
    cases = []

    trend = source[source.city.eq('DELHI')].groupby(['city', 'month_start']).agg(
        avg_aqi=('aqi', 'mean'), days_measured=('aqi', 'count')).reset_index()
    trend['rolling_3_month_avg'] = trend.avg_aqi.rolling(3, min_periods=1).mean()
    trend = trend[trend.month_start.dt.year.eq(2019)]
    cases.append(('City trend', ['DELHI'], trend[['city', 'month_start', 'avg_aqi', 'rolling_3_month_avg', 'days_measured']]))

    compare = selected[selected.city.isin(cities[:2])].groupby(['city', 'year']).agg(
        avg_aqi=('aqi', 'mean'), days_measured=('aqi', 'count')).reset_index().sort_values(['year', 'city'])
    cases.append(('Compare cities', cities[:2], compare))

    ranking = selected.groupby('city').agg(avg_aqi=('aqi', 'mean'), days_measured=('aqi', 'count'),
                                          unhealthy=('unhealthy', 'sum')).reset_index()
    ranking = ranking[ranking.days_measured.gt(0)]
    ranking['pct_unhealthy_days'] = 100.0 * ranking.unhealthy / ranking.days_measured
    ranking['pollution_rank'] = ranking.avg_aqi.rank(method='dense', ascending=False)
    ranking = ranking[['city', 'avg_aqi', 'pollution_rank', 'days_measured', 'pct_unhealthy_days']].sort_values(['avg_aqi', 'city'], ascending=[False, True])
    cases.append(('City rankings', cities, ranking))

    season = selected[selected.city.eq('DELHI')].groupby('month').agg(
        avg_aqi=('aqi', 'mean'), days_measured=('aqi', 'count')).reset_index()
    season = season[season.days_measured.gt(0)].sort_values(['avg_aqi', 'month'], ascending=[False, True])
    cases.append(('Seasonal pattern', ['DELHI'], season))

    heatmap = selected.groupby(['city', 'month']).aqi.mean().unstack().reindex(columns=range(1, 13))
    heatmap.columns = [f'm{month:02d}' for month in range(1, 13)]
    cases.append(('City heatmap', cities, heatmap.reset_index().sort_values('city')))

    for view, selected_cities, expected in cases:
        actual, _ = execute(build_explorer_query(view, selected_cities, years, top_n=3))
        expected = expected.copy().reset_index(drop=True)
        for column in expected:
            if column == 'month_start':
                expected[column] = pd.to_datetime(expected[column])
                actual[column] = pd.to_datetime(actual[column])
            elif column != 'city':
                expected[column] = pd.to_numeric(expected[column]).astype(float)
                actual[column] = pd.to_numeric(actual[column]).astype(float)
        pd.testing.assert_frame_equal(expected, actual, check_dtype=False, check_exact=False, rtol=1e-8, atol=1e-8)
        print(f'PASS: {view}, 2019 filter, {len(actual)} rows match source CSV calculations')


if __name__ == '__main__':
    main()
