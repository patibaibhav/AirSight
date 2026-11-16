"""AirSight: conversational BI and a guided historical AQI explorer."""
from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

import streamlit as st

from charts import make_chart
from explorer import VIEWS, build_explorer_query, explorer_title
from schema_context import CITIES, SAMPLES, namespace
from rules import RULES_VERSION
from service import Answer, answer, execute, summarize
from ui import STYLE, csv_export, result_metrics

st.set_page_config(page_title='AirSight · Air quality, explained', page_icon='🌤️',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown(STYLE, unsafe_allow_html=True)

for key, value in {'messages': [], 'answer_cache': {}, 'active_message': None,
                   'explorer_result': None, 'workspace': 'Ask AirSight'}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def queue_question(question: str) -> None:
    st.session_state.pending_question = question
    st.session_state.workspace = 'Ask AirSight'


def reset_explorer_cities() -> None:
    view = st.session_state.explorer_view
    if view in {'City rankings', 'City heatmap'}:
        st.session_state.explorer_cities = list(CITIES)
    elif view == 'Compare cities':
        st.session_state.explorer_cities = ['DELHI', 'MUMBAI']
    else:
        st.session_state.explorer_cities = ['DELHI']


def cache_key(kind: str, payload: tuple) -> tuple:
    return (RULES_VERSION, kind, namespace(), os.getenv('GEMINI_MODEL', ''), *payload)


def run_cached(key: tuple, operation, refresh: bool = False):
    now = time.monotonic()
    cache = st.session_state.answer_cache
    hit = not refresh and key in cache and now - cache[key]['created'] < 300
    if hit:
        entry = dict(cache[key])
    else:
        started = time.perf_counter()
        result = operation()
        entry = {'result': result, 'created': time.monotonic(),
                 'elapsed': time.perf_counter() - started,
                 'fetched': datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d %b · %H:%M IST')}
        cache[key] = entry
        while len(cache) > 20:
            del cache[next(iter(cache))]
    return {**entry, 'cache_hit': hit}


def handle_error(error: Exception) -> None:
    if isinstance(error, ValueError):
        st.warning(str(error))
    else:
        st.error('Could not reach the data warehouse. Check your connection and try again. Your previous result is preserved.')


with st.sidebar:
    st.markdown('<div class="air-brand">air<span>sight</span> ◌</div>', unsafe_allow_html=True)
    st.caption('A clearer view of urban air.')
    st.divider()
    st.markdown('**Try a question**')
    labels = ['Most polluted cities', 'Delhi vs Mumbai', 'Delhi pollution trend',
              'Worst month in Delhi', 'The 2020 comparison', 'City × month heatmap']
    for index, (label, sample) in enumerate(zip(labels, SAMPLES)):
        st.button(label, key=f'sample_{index}', width='stretch',
                  on_click=queue_question, args=(sample,))
    st.divider()
    configured = bool(os.getenv('GEMINI_API_KEY') and os.getenv('GEMINI_MODEL'))
    use_gemini = st.toggle('Use Gemini', value=configured, disabled=not configured, key='use_gemini')
    st.caption('Broader questions with Gemini.' if configured else 'Guided questions work without an API key.')
    database, schema = namespace()
    st.caption('Production data' if schema == 'MARTS' else 'Development data')
    st.caption('Repeated requests reuse results for up to 5 minutes. Queries run only when you ask or explore.')
    if st.button('Clear saved results', key='clear_results', width='stretch'):
        st.session_state.messages = []
        st.session_state.answer_cache = {}
        st.session_state.active_message = None
        st.session_state.explorer_result = None
        st.rerun()
    with st.expander('About the dataset'):
        st.write('Daily CPCB readings from 26 Indian cities, January 2015 to July 1, 2020. City coverage varies; 2020 is a partial year.')
        st.write('Missing AQI and 93 out-of-range readings are excluded from AQI averages. Originals remain preserved; other pollutants are not filled in.')
        st.caption(f'Source: {database}.{schema} · Read-only BI role')

header, badge = st.columns([4, 1], vertical_alignment='center')
with header:
    st.markdown('<div class="air-eyebrow">AIR QUALITY INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title('Understand the air. Explore the story.')
    st.markdown('<p class="air-lede">Compare cities, uncover seasonal patterns, and turn historical air-quality data into answers you can inspect.</p>', unsafe_allow_html=True)
with badge:
    st.markdown('<span class="air-pill">● Historical dataset</span>', unsafe_allow_html=True)

for column, (label, value, help_text) in zip(st.columns(3), [
    ('Cities in the source', '26', 'Coverage differs between cities.'),
    ('Daily source observations', '29,531', 'Includes missing readings, preserved in the source.'),
    ('Observation period', '2015–2020', 'Ends July 1, 2020. These are not live readings.'),
]):
    column.metric(label, value, help=help_text)
st.caption('Historical observations, not current conditions. AQI averages exclude missing and flagged readings. Read the dataset notes in the sidebar.')

mode = st.segmented_control('Workspace', ['Ask AirSight', 'Explore data'], key='workspace', required=True,
                            label_visibility='collapsed')


def render_result(entry: dict, key: str) -> None:
    result = entry['result']
    st.write(summarize(result))
    if result.note:
        st.caption(result.note)
    status = 'Session cache' if entry['cache_hit'] else f"Answered in {entry['elapsed']:.1f}s"
    st.caption(f"{result.source} · {status} · Fetched {entry['fetched']}")
    metrics = result_metrics(result.frame, result.intent)
    if metrics:
        for column, (label, value) in zip(st.columns(len(metrics)), metrics):
            column.metric(label, value)
    if len(result.frame) >= 200:
        st.warning('Showing at most 200 rows. Narrow your question to avoid a truncated result.')
    chart = make_chart(result.frame, result.intent)
    if chart is not None:
        st.plotly_chart(chart, width='stretch', key=f'{key}_chart',
                        config={'displaylogo': False, 'scrollZoom': False})
    with st.expander('Result table', expanded=chart is None):
        st.dataframe(result.frame, width='stretch', hide_index=True,
                     column_config={'avg_aqi': st.column_config.NumberColumn('Mean AQI', format='%.1f'),
                                    'days_measured': st.column_config.NumberColumn('Usable AQI days', format='%d')})
    with st.expander('View generated SQL'):
        st.code(result.sql, language='sql')
        if result.params:
            st.write('Bound values:', list(result.params))
    downloads = st.columns(2)
    downloads[0].download_button('Download data · CSV', csv_export(result.frame),
                                file_name=f'airsight_{result.intent}.csv', mime='text/csv',
                                key=f'{key}_csv', on_click='ignore', width='stretch')
    sql_file = result.sql + ('\n\n-- Bound values (in order): ' + repr(result.params) if result.params else '')
    downloads[1].download_button('Download query · SQL', sql_file, file_name=f'airsight_{result.intent}.sql',
                                mime='text/plain', key=f'{key}_sql', on_click='ignore', width='stretch')


if mode == 'Ask AirSight':
    question = st.session_state.pop('pending_question', None)
    if not st.session_state.messages and not question:
        st.markdown('<div class="air-empty"><h3>What would you like to discover?</h3><p>Ask a question below, choose a sidebar prompt, or use Explore data for city and year filters.</p></div>', unsafe_allow_html=True)
        for column, label, sample in zip(st.columns(3),
                                        ['Find city rankings →', 'Compare two cities →', 'Explore seasonal patterns →'],
                                        [SAMPLES[0], SAMPLES[1], SAMPLES[3]]):
            column.button(label, key=f'quick_{sample}', on_click=queue_question, args=(sample,), width='stretch')
    typed_question = st.chat_input('Ask about a city, a comparison, or a seasonal pattern…', key='question_input', max_chars=1000)
    question = question or typed_question
    if question:
        try:
            with st.spinner('Finding your answer…'):
                entry = run_cached(cache_key('chat', (question.strip().lower(), use_gemini)),
                                   lambda: answer(question, use_gemini=use_gemini))
            message_id = st.session_state.get('next_message_id', 0)
            st.session_state.next_message_id = message_id + 1
            st.session_state.messages.append({**entry, 'question': question, 'id': message_id})
            st.session_state.messages = st.session_state.messages[-10:]
            st.session_state.active_message = message_id
        except Exception as error:
            handle_error(error)
    if st.session_state.messages:
        messages = {message['id']: message for message in st.session_state.messages}
        if st.session_state.active_message not in messages:
            st.session_state.active_message = next(reversed(messages))
        st.selectbox('Recent questions', list(reversed(messages)),
                     format_func=lambda key: messages[key]['question'], key='active_message')
        entry = messages[st.session_state.active_message]
        with st.chat_message('user'):
            st.write(entry['question'])
        with st.chat_message('assistant'):
            render_result(entry, key=f"chat_{entry['id']}")
else:
    st.subheader('Your cities. Your time period.')
    st.caption('Filters apply to this explorer. Use the chat workspace for natural-language questions.')
    view = st.selectbox('Analysis', VIEWS, key='explorer_view', on_change=reset_explorer_cities)
    if 'explorer_cities' not in st.session_state:
        reset_explorer_cities()
    with st.form('explorer_filters'):
        years = st.slider('Year range', min_value=2015, max_value=2020,
                          value=(2015, 2020), key='explorer_years')
        cities = st.multiselect('Cities', CITIES, format_func=str.title,
                               key='explorer_cities', help='Trend/season: one city. Compare: two or three. Rankings/heatmap: any selection.')
        top_n, order = 10, 'Most polluted first'
        if view == 'City rankings':
            ranking_columns = st.columns([1, 1])
            top_n = ranking_columns[0].slider('Ranking size', 1, 26, 10, key='explorer_top')
            order = ranking_columns[1].selectbox('Ranking order', ['Most polluted first', 'Cleanest first'], key='explorer_order')
        st.caption('For rankings or a heatmap, select every city you want included. 2020 ends in July; comparisons reflect available observations.')
        run_column, refresh_column = st.columns([1, 1])
        submitted = run_column.form_submit_button('Explore selection', type='primary', width='stretch', key='explore_submit')
        refresh = refresh_column.form_submit_button('Refresh from warehouse', width='stretch', key='explore_refresh')
    if submitted or refresh:
        try:
            query = build_explorer_query(view, cities, years, top_n, order == 'Cleanest first')
            def explore():
                frame, sql = execute(query)
                return Answer(frame, sql, query.params, query.intent, 'Explorer')
            with st.spinner('Exploring your selection…'):
                entry = run_cached(cache_key('explorer', (query.sql, query.params)), explore, refresh=refresh)
            st.session_state.explorer_result = {**entry, 'title': explorer_title(view, cities, years)}
        except Exception as error:
            handle_error(error)
    if st.session_state.explorer_result:
        entry = st.session_state.explorer_result
        st.subheader(entry['title'])
        st.caption('Result below reflects the last submitted selection. Submit again after changing filters.')
        render_result(entry, key='explorer')
    else:
        st.markdown('<div class="air-empty"><h3>Build your own view</h3><p>Choose an analysis, city selection and year range, then select Explore selection. Changing filters alone will not run a query.</p></div>', unsafe_allow_html=True)
