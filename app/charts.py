"""Choose a chart from the result shape without inventing observations."""
import pandas as pd
import plotly.express as px


def make_chart(frame: pd.DataFrame, intent: str):
    if frame.empty:
        return None
    data = frame.copy()
    month_columns = [f'm{month:02d}' for month in range(1, 13)]
    if 'city' in data and all(column in data for column in month_columns):
        matrix = data.set_index('city')[month_columns].astype(float)
        matrix.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return px.imshow(matrix, aspect='auto', color_continuous_scale='YlOrRd',
                         labels={'color': 'Mean AQI', 'x': 'Calendar month', 'y': 'City'},
                         title='Seasonal AQI pattern · available years combined')
    if 'avg_aqi' not in data:
        return None
    data['avg_aqi'] = pd.to_numeric(data.avg_aqi)
    if 'month_start' in data:
        data['month_start'] = pd.to_datetime(data.month_start)
        series = ['avg_aqi']
        if 'rolling_3_month_avg' in data and data.get('city', pd.Series(dtype=str)).nunique() <= 1:
            data['rolling_3_month_avg'] = pd.to_numeric(data.rolling_3_month_avg)
            series.append('rolling_3_month_avg')
        figure = px.line(data.sort_values('month_start'), x='month_start', y=series,
                         color='city' if len(series) == 1 and 'city' in data else None,
                         labels={'value': 'AQI', 'month_start': 'Month'}, title='Monthly air-quality trend')
        figure.update_traces(connectgaps=False)
        return figure
    if 'year' in data:
        return px.bar(data, x='year', y='avg_aqi', color='city' if 'city' in data else None,
                      barmode='group', labels={'avg_aqi': 'Mean AQI', 'year': 'Year'},
                      title='AQI comparison · observed periods')
    if 'month' in data:
        return px.bar(data.sort_values('month'), x='month', y='avg_aqi',
                      labels={'avg_aqi': 'Mean AQI', 'month': 'Calendar month'},
                      title='Monthly pattern · daily-weighted across available years')
    if 'city' in data:
        return px.bar(data, x='city', y='avg_aqi', color='avg_aqi', color_continuous_scale='YlOrRd',
                      labels={'avg_aqi': 'Mean AQI', 'city': 'City'}, title='City air-quality comparison')
    return None
