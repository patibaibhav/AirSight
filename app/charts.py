"""Choose a chart from the result shape without inventing observations."""
import pandas as pd
import plotly.express as px

PALETTE = ['#087e8b', '#ed9b40', '#7659a3']


def polish(figure, height: int = 400):
    figure.update_layout(
        template='plotly_white', height=height,
        font=dict(family='Arial, sans-serif', color='#35535d', size=12),
        title=dict(font=dict(size=17, color='#163b42'), x=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=65, b=30),
        legend=dict(title_text='', orientation='h', y=1.12, x=0),
        hoverlabel=dict(bgcolor='white', font_size=13),
    )
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(gridcolor='#e4ecef', zeroline=False)
    return figure


def make_chart(frame: pd.DataFrame, intent: str):
    if frame.empty:
        return None
    data = frame.copy()
    month_columns = [f'm{month:02d}' for month in range(1, 13)]
    if 'city' in data and all(column in data for column in month_columns):
        matrix = data.set_index('city')[month_columns].astype(float)
        matrix.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        figure = px.imshow(matrix, aspect='auto', color_continuous_scale='YlOrRd',
                         labels={'color': 'Mean AQI', 'x': 'Calendar month', 'y': 'City'},
                         title='Seasonal AQI pattern')
        figure.update_traces(hovertemplate='%{y} · %{x}<br>Mean AQI %{z:.1f}<extra></extra>')
        return polish(figure, height=max(380, min(800, len(matrix) * 24 + 110)))
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
                         color_discrete_sequence=PALETTE,
                         labels={'value': 'AQI', 'month_start': 'Month'}, title='Monthly air-quality trend')
        figure.update_traces(connectgaps=False, line_width=2.5)
        names = {'avg_aqi': 'Monthly mean', 'rolling_3_month_avg': '3-month mean'}
        for trace in figure.data:
            trace.name = names.get(trace.name, trace.name.title())
        figure.update_layout(hovermode='x unified')
        return polish(figure)
    if 'year' in data:
        data['year'] = data.year.astype(str)
        figure = px.bar(data, x='year', y='avg_aqi', color='city' if 'city' in data else None,
                      color_discrete_sequence=PALETTE,
                      barmode='group', labels={'avg_aqi': 'Mean AQI', 'year': 'Year'},
                      title='AQI comparison · observed periods')
        return polish(figure)
    if 'month' in data:
        import calendar
        data = data.sort_values('month')
        data['month_label'] = data.month.map(lambda value: calendar.month_abbr[int(value)])
        figure = px.bar(data, x='month_label', y='avg_aqi', color_discrete_sequence=PALETTE,
                      labels={'avg_aqi': 'Mean AQI', 'month': 'Calendar month'},
                      title='Monthly pattern · daily-weighted across available years')
        figure.update_xaxes(title='Calendar month')
        return polish(figure)
    if 'city' in data:
        figure = px.bar(data, x='avg_aqi', y='city', orientation='h', color='avg_aqi',
                      color_continuous_scale=['#a2d8cf', '#087e8b', '#164751'],
                      labels={'avg_aqi': 'Mean AQI', 'city': 'City'}, title='City air-quality comparison')
        figure.update_yaxes(categoryorder='array', categoryarray=list(reversed(data.city.tolist())))
        figure.update_layout(coloraxis_showscale=False)
        figure.update_traces(hovertemplate='%{y}<br>Mean AQI %{x:.1f}<extra></extra>')
        return polish(figure, height=max(360, min(850, len(data) * 30 + 100)))
    return None
