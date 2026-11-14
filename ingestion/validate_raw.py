"""Validate AIRSIGHT.RAW.CITY_DAY after an Airbyte sync (owner: B).

Checks: row count, distinct cities, CITY/DATE nulls, per-column null report, date range.
Logs one row to AIRSIGHT.OPS.INGESTION_LOG (PASSED or FAILED). Raises ValidationError on
failure; the CLI exits non-zero. Config only from env vars (see .env.example).
"""
import json
import logging
import os
import sys

import snowflake.connector

log = logging.getLogger("validate_raw")

RAW_TABLE = "AIRSIGHT.RAW.CITY_DAY"
LOG_TABLE = "AIRSIGHT.OPS.INGESTION_LOG"


class ValidationError(Exception):
    pass


def connect():
    """Snowflake connection as AIRBYTE_USER / AIRBYTE_ROLE (owner of RAW and OPS)."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["AIRBYTE_USER"],
        password=os.environ["AIRBYTE_PASSWORD"],
        role="AIRBYTE_ROLE",
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "AIRSIGHT_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "AIRSIGHT"),
    )


def _data_columns(cur) -> list[str]:
    cur.execute(
        "SELECT column_name FROM AIRSIGHT.INFORMATION_SCHEMA.COLUMNS "
        "WHERE table_schema = 'RAW' AND table_name = 'CITY_DAY' "
        "AND NOT STARTSWITH(UPPER(column_name), '_AIRBYTE') ORDER BY ordinal_position"
    )
    return [r[0] for r in cur.fetchall()]


def _find(cols: list[str], name: str) -> str:
    for c in cols:
        if c.upper() == name:
            return c
    raise ValidationError(f"column {name} not found in {RAW_TABLE}; columns={cols}")


def _log_result(cur, status: str, rows=None, cities=None, min_d=None, max_d=None, nulls=None):
    cur.execute(
        f"INSERT INTO {LOG_TABLE} (row_count, city_count, min_date, max_date, null_report, status) "
        "SELECT %s, %s, %s, %s, PARSE_JSON(%s), %s",
        (rows, cities, min_d, max_d, json.dumps(nulls or {}), status),
    )


def validate() -> dict:
    expected_rows = int(os.environ["EXPECTED_ROW_COUNT"])
    expected_cities = int(os.environ.get("EXPECTED_CITY_COUNT", "26"))
    conn = connect()
    try:
        cur = conn.cursor()
        cols = _data_columns(cur)
        if not cols:
            _log_result(cur, "FAILED")
            raise ValidationError(f"{RAW_TABLE} missing or empty of columns")
        city, date = _find(cols, "CITY"), _find(cols, "DATE")

        null_exprs = ", ".join(f'COUNT_IF("{c}" IS NULL) AS "{c}"' for c in cols)
        cur.execute(
            f'SELECT COUNT(*), COUNT(DISTINCT "{city}"), '
            f'MIN(TRY_TO_DATE(TO_VARCHAR("{date}"))), MAX(TRY_TO_DATE(TO_VARCHAR("{date}"))), '
            f"{null_exprs} FROM {RAW_TABLE}"
        )
        row = cur.fetchone()
        rows, cities, min_d, max_d = row[0], row[1], row[2], row[3]
        nulls = {c: round(100.0 * n / rows, 2) if rows else 100.0 for c, n in zip(cols, row[4:])}
        result = {"rows": rows, "cities": cities, "min_date": str(min_d), "max_date": str(max_d),
                  "null_pct": nulls}

        problems = []
        if rows != expected_rows:
            problems.append(f"row count {rows} != expected {expected_rows}")
        if cities != expected_cities:
            problems.append(f"city count {cities} != expected {expected_cities}")
        for key_col in (city, date):
            if nulls.get(key_col, 0) > 0:
                problems.append(f"nulls in key column {key_col}: {nulls[key_col]}%")

        status = "FAILED" if problems else "PASSED"
        _log_result(cur, status, rows, cities, min_d, max_d, nulls)
        log.info("validation %s: %s", status, json.dumps(result))
        if problems:
            raise ValidationError("; ".join(problems))
        return result
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        validate()
    except ValidationError as exc:
        log.error("VALIDATION FAILED: %s", exc)
        sys.exit(1)
