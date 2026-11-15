"""Regression checks for explorer scope, session reuse and user interactions."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from explorer import VIEWS, build_explorer_query
from nl2sql import guard_sql
from schema_context import CITIES
from service import Answer
from ui import csv_export, result_metrics


class ExplorerTests(unittest.TestCase):
    def test_all_views_use_bound_scope_and_guardrail(self):
        for view in VIEWS:
            cities = ['DELHI', 'MUMBAI'] if view == 'Compare cities' else ['DELHI']
            with self.subTest(view=view):
                query = build_explorer_query(view, cities, (2018, 2019), 5)
                sql = guard_sql(query.sql)
                self.assertEqual(query.params, tuple(cities) + (2018, 2019))
                self.assertEqual(sql.count('?'), len(query.params))
                self.assertNotIn('DELHI', sql)
                self.assertIn('LIMIT ', sql)

    def test_rejects_invalid_filters(self):
        cases = [
            ('City trend', [], (2015, 2020), 10),
            ('City trend', ['PARIS'], (2015, 2020), 10),
            ('City trend', ['DELHI', 'MUMBAI'], (2015, 2020), 10),
            ('Compare cities', ['DELHI'], (2015, 2020), 10),
            ('City rankings', ['DELHI'], (2020, 2015), 10),
            ('City rankings', ['DELHI'], (2015, 2021), 10),
            ('City rankings', ['DELHI'], (2015, 2020), 200),
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                build_explorer_query(*args)

    def test_metrics_dont_average_averages_or_fill_missing(self):
        frame = pd.DataFrame({'city': ['DELHI', 'MUMBAI'], 'avg_aqi': [200, None]})
        metrics = dict(result_metrics(frame, 'ranking'))
        self.assertEqual(metrics['Highest mean AQI'], '200.0')
        self.assertEqual(metrics['Lowest mean AQI'], '200.0')
        self.assertEqual(metrics['Cities shown'], '2')

    def test_csv_preserves_numeric_readings_and_escapes_formula_labels(self):
        frame = pd.DataFrame({'label': ['=SUM(A1)', 'DELHI'], 'avg_aqi': [100.5, 0]})
        exported = csv_export(frame).decode()
        self.assertIn("'=SUM(A1)", exported)
        self.assertIn('100.5', exported)
        self.assertEqual(frame.label.iloc[0], '=SUM(A1)')


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'GEMINI_API_KEY': '', 'MARTS_SCHEMA': 'MARTS'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        frame = pd.DataFrame({'city': ['DELHI', 'MUMBAI'], 'year': [2020, 2020],
                              'avg_aqi': [200., 100.], 'days_measured': [120, 100]})
        self.answer = patch('service.answer', return_value=Answer(frame, 'SELECT city FROM AIRSIGHT.MARTS.MART_CITY_RANKINGS LIMIT 200', (), 'compare', 'Rules')).start()
        self.execute = patch('service.execute', return_value=(frame, 'SELECT city FROM AIRSIGHT.MARTS.MART_CITY_RANKINGS LIMIT 200')).start()
        self.addCleanup(patch.stopall)
        self.app = AppTest.from_file(str(Path(__file__).with_name('streamlit_app.py'))).run()
        self.assertFalse(self.app.exception)

    def test_initial_load_is_offline_and_samples_are_available(self):
        self.answer.assert_not_called()
        self.execute.assert_not_called()
        self.assertEqual(len(self.app.metric), 3)
        self.assertEqual(len([item for item in self.app.button if (item.key or '').startswith('sample_')]), 6)

    def test_repeat_question_cache_history_exports_and_clear(self):
        self.app.chat_input[0].set_value('Compare Delhi and Mumbai').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.answer.call_count, 1)
        self.app.chat_input[0].set_value('Compare Delhi and Mumbai').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.answer.call_count, 1)
        self.assertEqual(len(self.app.get('plotly_chart')), 1)
        self.assertEqual(len(self.app.get('download_button')), 2)
        self.assertEqual(len(self.app.session_state['messages']), 2)
        # An expired snapshot must fetch again rather than serving stale results.
        for entry in self.app.session_state['answer_cache'].values():
            entry['created'] -= 301
        self.app.chat_input[0].set_value('Compare Delhi and Mumbai').run()
        self.assertEqual(self.answer.call_count, 2)
        self.app.button(key='clear_results').click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.session_state['messages'])
        self.assertFalse(self.app.session_state['answer_cache'])

    def test_explorer_filters_submit_cache_refresh_and_return_to_chat(self):
        self.app.chat_input[0].set_value('Compare Delhi and Mumbai').run()
        self.app.get('button_group')[0].set_value('Explore data').run()
        self.assertFalse(self.app.exception)
        self.execute.assert_not_called()
        self.app.selectbox(key='explorer_view').set_value('City rankings').run()
        self.assertEqual(list(self.app.multiselect(key='explorer_cities').value), CITIES)
        self.execute.assert_not_called()
        self.app.slider(key='explorer_years').set_value((2018, 2019))
        self.app.button(key='explore_submit').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.execute.call_count, 1)
        self.assertEqual(self.execute.call_args.args[0].params[-2:], (2018, 2019))
        self.app.button(key='explore_submit').click().run()
        self.assertEqual(self.execute.call_count, 1)
        self.app.button(key='explore_refresh').click().run()
        self.assertEqual(self.execute.call_count, 2)
        self.app.get('button_group')[0].set_value('Ask AirSight').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.dataframe), 1)
        self.assertEqual(self.answer.call_count, 1)


if __name__ == '__main__':
    unittest.main()
