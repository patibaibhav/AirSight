"""Exercise the actual Streamlit interface against the configured warehouse."""
from pathlib import Path
import os

from streamlit.testing.v1 import AppTest


def main() -> None:
    # Keep this check deterministic and avoid consuming Gemini quota.
    os.environ['GEMINI_API_KEY'] = ''
    app = AppTest.from_file(str(Path(__file__).with_name('streamlit_app.py')))
    app.run(timeout=30)
    assert not app.exception, app.exception
    app.chat_input[0].set_value('Compare Delhi and Mumbai AQI over the years').run(timeout=45)
    assert not app.exception, app.exception
    assert not app.error, app.error
    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 12
    assert len(app.get('plotly_chart')) == 1
    app.button(key='sample_5').click().run(timeout=45)
    assert not app.exception, app.exception
    assert not app.error, app.error
    assert len(app.dataframe[-1].value) == 26
    assert len(app.get('plotly_chart')) == 1
    assert len(app.get('download_button')) == 2
    app.get('button_group')[0].set_value('Explore data').run(timeout=30)
    app.selectbox(key='explorer_view').set_value('City rankings').run(timeout=30)
    app.slider(key='explorer_years').set_value((2019, 2019))
    app.button(key='explore_submit').click().run(timeout=45)
    assert not app.exception, app.exception
    assert not app.error, app.error
    assert len(app.dataframe[0].value) == 10
    assert app.session_state['explorer_result']['result'].params[-2:] == (2019, 2019)
    print('PASS: live chat, city comparison, 26-city heatmap, exports and year-filtered ranking explorer')


if __name__ == '__main__':
    main()
