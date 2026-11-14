"""Generate SQL with Gemini and enforce a restricted read-only SQL contract."""
import os
import re

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from schema_context import TABLES, namespace, schema_prompt


def guard_sql(sql: str) -> str:
    if not sql or len(sql) > 20000:
        raise ValueError('SQL is empty or too long')
    # Deliberately conservative: even forbidden keywords in strings are rejected.
    if re.search(r'\b(insert|update|delete|drop|create|alter|truncate|merge|copy|call|put|get|grant|revoke|execute|use|into)\b', sql, re.I):
        raise ValueError('Only read-only SELECT queries are allowed')
    try:
        statements = [item for item in sqlglot.parse(sql, read='snowflake') if item is not None]
    except sqlglot.errors.ParseError as error:
        raise ValueError('SQL could not be parsed') from error
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError('Expected a single SELECT or WITH query')
    tree = statements[0]
    if tree.find(exp.Into) or tree.args.get('locks'):
        raise ValueError('SELECT side effects are not allowed')
    database, schema = namespace()
    physical_tables = 0
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                physical_tables += 1
                if (not isinstance(source.this, exp.Identifier)
                    or source.catalog.upper() != database or source.db.upper() != schema
                    or source.name.upper() not in TABLES):
                    raise ValueError('Query must use only the configured, fully qualified marts')
    if not physical_tables:
        raise ValueError('Query must read a permitted mart')
    for function in tree.find_all(exp.Func):
        if isinstance(function, exp.Anonymous) and function.name.upper() not in {'COUNT_IF', 'EQUAL_NULL'}:
            raise ValueError('Unrecognized or external SQL functions are not permitted')
    # Block qualified UDFs and stage/external data access, including parser fallbacks.
    if tree.find(exp.Dot) or tree.find(exp.Command) or tree.find(exp.UDTF):
        raise ValueError('Unsupported SQL construct')
    requested = tree.args.get('limit')
    limit = 200
    if requested:
        value = requested.expression
        if not isinstance(value, exp.Literal) or not value.is_int:
            raise ValueError('LIMIT must be an integer')
        limit = max(0, min(int(value.this), 200))
    return tree.limit(limit).sql(dialect='snowflake')


def generate_sql(question: str, previous_error: str | None = None) -> str:
    key, model = os.getenv('GEMINI_API_KEY'), os.getenv('GEMINI_MODEL')
    if not key or not model:
        raise ValueError('Gemini is not configured')
    from google import genai
    from google.genai import types
    prompt = schema_prompt() + '\nQuestion: ' + question
    if previous_error:
        prompt += '\nThe prior query failed. Return corrected SQL. Error: ' + previous_error[:500]
    with genai.Client(api_key=key, http_options=types.HttpOptions(timeout=20000)) as client:
        response = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=1500),
        )
    sql = (response.text or '').strip()
    if sql.startswith('```'):
        sql = re.sub(r'^```(?:sql)?\s*|\s*```$', '', sql, flags=re.I)
    return guard_sql(sql)
