"""AirSight conversational analytics interface."""
import os

import streamlit as st

from charts import make_chart
from schema_context import SAMPLES, namespace
from service import answer, summarize

st.set_page_config(page_title='AirSight · Air quality, explained', page_icon='🌤️', layout='wide')
st.title('AirSight')
st.markdown('### Indian air quality, one question at a time')
st.caption('Historical CPCB dataset · 26 cities · January 2015–July 2020')

with st.sidebar:
    st.header('Explore the data')
    st.caption('Choose a question to begin, or type your own below.')
    selected = None
    for index, sample in enumerate(SAMPLES):
        if st.button(sample, key=f'sample_{index}', width='stretch'):
            selected = sample
    configured = bool(os.getenv('GEMINI_API_KEY') and os.getenv('GEMINI_MODEL'))
    use_gemini = st.toggle('Use Gemini', value=configured, disabled=not configured)
    st.caption('Gemini is ready.' if configured else 'Rule-based questions are ready. Add Gemini credentials to enable broader questions.')
    database, schema = namespace()
    st.caption(f'Data: {database}.{schema}')
    if st.button('Clear conversation'):
        st.session_state.messages = []
        st.rerun()

st.info('Missing AQI and 93 out-of-range readings are excluded from AQI averages. Original readings are retained. City coverage varies; these historical comparisons do not describe current air quality.')

if 'messages' not in st.session_state:
    st.session_state.messages = []


def render_result(result):
    st.write(summarize(result))
    st.caption(f'Question engine: {result.source} · maximum 200 result rows')
    if result.note:
        st.caption(result.note)
    with st.expander('View generated SQL'):
        st.code(result.sql, language='sql')
        if result.params:
            st.write('Bound values:', list(result.params))
    st.dataframe(result.frame, width='stretch', hide_index=True)
    chart = make_chart(result.frame, result.intent)
    if chart is not None:
        st.plotly_chart(chart, width='stretch')


for message in st.session_state.messages:
    with st.chat_message('user'):
        st.write(message['question'])
    with st.chat_message('assistant'):
        render_result(message['result'])

question = st.chat_input('Ask about a city, compare cities, or explore seasonal patterns…')
question = selected or question
if question:
    with st.chat_message('user'):
        st.write(question)
    with st.chat_message('assistant'):
        try:
            with st.spinner('Checking the air-quality data…'):
                result = answer(question, use_gemini=use_gemini)
            render_result(result)
            st.session_state.messages.append({'question': question, 'result': result})
            st.session_state.messages = st.session_state.messages[-10:]
        except ValueError as error:
            st.warning(str(error))
        except Exception:
            st.error('The data connection could not complete this question. Check the warehouse and your local BI credentials, then retry.')
