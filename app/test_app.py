"""Offline regression checks for SQL boundaries, fallback and chart rendering."""
import os
import unittest
from unittest.mock import patch

import pandas as pd
import snowflake.connector

from charts import make_chart
from nl2sql import guard_sql
from rules import build_query
from schema_context import SAMPLES
from service import answer


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'SNOWFLAKE_DATABASE': 'AIRSIGHT', 'MARTS_SCHEMA': 'DEV_MARTS'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.table = 'AIRSIGHT.DEV_MARTS.MART_CITY_RANKINGS'

    def test_supported_rules_preserve_parameters_and_add_limit(self):
        for question in SAMPLES:
            with self.subTest(question=question):
                query = build_query(question)
                sql = guard_sql(query.sql)
                self.assertIn('LIMIT ', sql)
                self.assertEqual(sql.count('?'), len(query.params))

    def test_cte_is_allowed_but_every_physical_source_is_checked(self):
        sql = guard_sql(f'with x as (select city from {self.table}) select city from x')
        self.assertTrue(sql.endswith('LIMIT 200'))
        with self.assertRaises(ValueError):
            guard_sql('with x as (select * from AIRSIGHT.RAW.CITY_DAY) select * from x')

    def test_rejects_cross_schema_functions_side_effects_and_statements(self):
        attacks = [
            f'select * from {self.table}; drop table anything',
            'select * from AIRSIGHT.RAW.CITY_DAY',
            'select * from OTHER.DEV_MARTS.MART_CITY_RANKINGS',
            'select * from MART_CITY_RANKINGS',
            f'select system$wait(60) from {self.table}',
            f'select custom_udf(city) from {self.table}',
            f'select * into new_table from {self.table}',
            f'select * from {self.table} join table(generator(rowcount => 1000000)) on true',
            f'select (select max(AQI) from AIRSIGHT.RAW.CITY_DAY) from {self.table}',
            f'select * from {self.table} limit ?',
            f'with hidden as (select * from AIRSIGHT.RAW.CITY_DAY) select * from {self.table}',
        ]
        for sql in attacks:
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                guard_sql(sql)

    def test_limit_clamped(self):
        self.assertTrue(guard_sql(f'select * from {self.table} limit 50000').endswith('LIMIT 200'))
        self.assertTrue(guard_sql(f'select * from {self.table} limit 5').endswith('LIMIT 5'))

    def test_model_failure_uses_bound_rules(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'GEMINI_MODEL': 'test'}), \
             patch('service.generate_sql', side_effect=RuntimeError('quota')), \
             patch('service.execute', return_value=(pd.DataFrame({'avg_aqi': [100]}), 'safe SQL')) as execute:
            result = answer('Show trend for Delhi')
            self.assertEqual(result.source, 'Rules')
            self.assertEqual(execute.call_args.args[0].params, ('DELHI',))

    def test_city_values_are_bound(self):
        query = build_query("Show Delhi's trend; drop table x")
        self.assertNotIn('drop', query.sql.lower())
        self.assertNotIn('DELHI', query.sql)
        self.assertEqual(query.params, ('DELHI',))

    def test_requested_years_are_bound(self):
        for question in ['Trend Delhi in 2020', 'Worst month in Delhi in 2020',
                         'Compare Delhi and Mumbai in 2020']:
            query = build_query(question)
            self.assertEqual(query.params[-1], 2020)
            self.assertIn('?', guard_sql(query.sql))

    def test_unsupported_metrics_and_cities_are_not_silently_reinterpreted(self):
        for question in ['Compare Delhi and Paris', 'PM2.5 trend in Delhi']:
            with self.assertRaises(ValueError):
                build_query(question)

    def test_sql_error_gets_exactly_one_model_retry(self):
        sql = f'select city from {self.table}'
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'GEMINI_MODEL': 'test'}), \
             patch('service.generate_sql', return_value=sql) as generate, \
             patch('service.execute', side_effect=[snowflake.connector.errors.ProgrammingError(msg='bad column'),
                                                   (pd.DataFrame({'city': ['DELHI']}), sql)]):
            result = answer('Show cities')
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(result.source, 'Gemini')

    def test_chart_shapes(self):
        frames = [
            (pd.DataFrame({'city': ['DELHI'], 'avg_aqi': [200]}), 'ranking'),
            (pd.DataFrame({'year': [2019, 2020], 'avg_aqi': [200, 100]}), 'lockdown'),
            (pd.DataFrame({'month_start': ['2020-01-01'], 'avg_aqi': [100], 'rolling_3_month_avg': [110]}), 'trend'),
            (pd.DataFrame({'city': ['DELHI'], **{f'm{i:02d}': [100.] for i in range(1, 13)}}), 'heatmap'),
        ]
        for frame, intent in frames:
            with self.subTest(intent=intent):
                self.assertIsNotNone(make_chart(frame, intent))


if __name__ == '__main__':
    unittest.main()
