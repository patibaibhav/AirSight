"""Presentation helpers and scoped styles for the Streamlit interface."""
import pandas as pd

STYLE = '''
<style>

:root { --air-teal: #087e8b; --air-ink: #163b42; }
.stApp { background: #f5f8fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1320px; }
/* Streamlit's fixed toolbar occupies the top of the main viewport. */
[data-testid="stMainBlockContainer"] { padding-top: 4.75rem; }
h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; letter-spacing: -.035em; color: #163b42; }
h1 { font-size: clamp(2rem, 4vw, 3.2rem) !important; line-height: 1.15 !important; }
[data-testid="stSidebar"] { background: #edf3f5; border-right: 1px solid #dce7eb; }
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
[data-testid="stMetric"] { background: #fff; border: 1px solid #dce7eb; border-radius: 16px; padding: 1rem 1.2rem; }
[data-testid="stMetricLabel"] { color: #53717b; }
[data-testid="stMetricValue"] { color: #163b42; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
[data-testid="stChatMessage"] { background: #fff; border: 1px solid #e0e9ed; border-radius: 16px; }
[data-testid="stChatInput"] { border-radius: 16px; border-color: #b5d4db; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button { border-radius: 10px; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] { background: #087e8b; border-color: #087e8b; color: white; }
[data-testid="stExpander"] { background: #fff; border-radius: 12px; }
.air-brand { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 1.65rem; font-weight: 800; color: #163b42; letter-spacing: -.07em; }
.air-brand span { color: #087e8b; }
.air-eyebrow { color: #087e8b; letter-spacing: .14em; font-size: .8rem; line-height: 1.5; font-weight: 800; margin-bottom: .55rem; }
.air-lede { color: #58717c; font-size: 1.04rem; max-width: 680px; line-height: 1.65; margin-bottom: 1.25rem; }
.air-pill { display: inline-block; border: 1px solid #bedad9; background: #e9f6f2; color: #17615a; border-radius: 100px; padding: .25rem .65rem; font-size: .76rem; font-weight: 600; }
.air-empty { background: linear-gradient(125deg,#e8f4f3,#f1f6fd); border: 1px solid #dce9ec; padding: 1.4rem 1.6rem; border-radius: 18px; margin: 1rem 0; }
.air-empty h3 { margin: 0 0 .3rem; font-size: 1.2rem; }
.air-empty p { color: #58717c; margin: 0; line-height: 1.6; }
@media(max-width: 700px) { .block-container { padding: 1rem 1rem 3rem; } [data-testid="stMainBlockContainer"] { padding-top: 4.5rem; } [data-testid="stMetric"] { padding: .7rem; } }
@media(prefers-color-scheme: dark) { .stApp { color-scheme: light; } }
</style>
'''


def result_metrics(frame: pd.DataFrame, intent: str) -> list[tuple[str, str]]:
    """Summarize observed results without averaging averages or filling missing values."""
    if frame.empty:
        return []
    metrics = [('Result rows', f'{len(frame):,}')]
    if 'city' in frame:
        metrics.append(('Cities shown', str(frame.city.nunique())))
    if 'avg_aqi' in frame:
        values = pd.to_numeric(frame.avg_aqi, errors='coerce').dropna()
        if not values.empty:
            metrics.append(('Highest mean AQI', f'{values.max():.1f}'))
            metrics.append(('Lowest mean AQI', f'{values.min():.1f}'))
    elif intent == 'heatmap':
        months = [column for column in frame if column.startswith('m') and column[1:].isdigit()]
        if months:
            metrics.append(('Months shown', str(len(months))))
            metrics.append(('Measured cells', f'{int(frame[months].notna().sum().sum()):,}'))
    return metrics[:4]


def csv_export(frame: pd.DataFrame) -> bytes:
    # Formula-like labels are escaped for spreadsheet applications. Numeric values stay numeric.
    safe = frame.copy()
    for column in safe.select_dtypes(include=['object', 'string']).columns:
        safe[column] = safe[column].map(
            lambda value: "'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@')) else value
        )
    return safe.to_csv(index=False).encode('utf-8')
