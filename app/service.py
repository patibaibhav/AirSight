"""Bounded BI queries under BI_USER, plus automatic rule-based fallback."""
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv
import pandas as pd
import snowflake.connector

from nl2sql import generate_sql, guard_sql
from rules import Query, build_query
from schema_context import namespace

load_dotenv(Path(__file__).resolve().parents[1] / '.env', interpolate=False)


@dataclass
class Answer:
    frame: pd.DataFrame
    sql: str
    params: tuple
    intent: str
    source: str
    note: str = ''


def execute(query: Query) -> tuple[pd.DataFrame, str]:
    safe_sql = guard_sql(query.sql)
    database, schema = namespace()
    if not os.getenv('SNOWFLAKE_ACCOUNT') or not os.getenv('BI_PASSWORD'):
        raise ValueError('Complete the Snowflake BI credentials in your local .env first.')
    with snowflake.connector.connect(
        account=os.environ['SNOWFLAKE_ACCOUNT'],
        user=os.getenv('BI_USER', 'BI_USER'), password=os.environ['BI_PASSWORD'],
        role='BI_ROLE', warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'AIRSIGHT_WH'),
        database=database, schema=schema, paramstyle='qmark',
        login_timeout=20, network_timeout=40,
        session_parameters={'STATEMENT_TIMEOUT_IN_SECONDS': 30, 'QUERY_TAG': 'airsight_bi'},
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(safe_sql, query.params if query.params else None)
            rows = cursor.fetchmany(200)
            columns = [item[0].lower() for item in cursor.description]
            return pd.DataFrame(rows, columns=columns), safe_sql


def answer(question: str, use_gemini: bool = True) -> Answer:
    if not question.strip() or len(question) > 1000:
        raise ValueError('Enter a question of 1–1,000 characters.')
    configured = bool(os.getenv('GEMINI_API_KEY') and os.getenv('GEMINI_MODEL'))
    fallback_note = ''
    if use_gemini and configured:
        try:
            sql = generate_sql(question)
            try:
                frame, sql = execute(Query(sql))
            except snowflake.connector.errors.ProgrammingError as error:
                # One SQL-error correction, then fall back; no unbounded retries.
                sql = generate_sql(question, previous_error=error.msg)
                frame, sql = execute(Query(sql))
            return Answer(frame, sql, (), 'custom', 'Gemini')
        except Exception:
            fallback_note = 'Gemini was unavailable or its query was rejected; used a supported rule-based question.'
    query = build_query(question)
    frame, sql = execute(query)
    return Answer(frame, sql, query.params, query.intent, 'Rules', fallback_note)


def summarize(result: Answer) -> str:
    data = result.frame
    if data.empty:
        return 'No matching observations were found for this question.'
    if result.intent == 'ranking':
        row = data.iloc[0]
        return f"{row['city'].title()} is first in this result, with mean AQI {float(row['avg_aqi']):.1f} across {int(row['days_measured']):,} usable days."
    if result.intent == 'monthly':
        row = data.iloc[0]
        import calendar
        return f"{calendar.month_name[int(row['month'])]} is first in this ordering, with a daily-weighted mean AQI of {float(row['avg_aqi']):.1f} across the available years."
    if result.intent == 'lockdown':
        return 'March–May 2019 and March–May 2020 are compared below. This descriptive comparison does not establish a causal lockdown effect.'
    return f'Returned {len(data):,} rows from the historical air-quality marts. The table and chart show the measured values.'
