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
    app.button[5].click().run(timeout=45)
    assert not app.exception, app.exception
    assert not app.error, app.error
    assert len(app.dataframe[-1].value) == 26
    assert len(app.get('plotly_chart')) == 2
    print('PASS: live Streamlit chat, 12-row city comparison, sample-button heatmap, 26-city table and two charts')


if __name__ == '__main__':
    main()
