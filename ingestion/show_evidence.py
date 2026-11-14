"""Print pipeline evidence tables for report screenshots (owner: B). Read-only.

Run in the Airflow container:
  docker compose exec airflow python /opt/airflow/ingestion/show_evidence.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_raw import connect  # noqa: E402


def show(cur, title: str, sql: str) -> None:
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = [[str(v) for v in r] for r in cur.fetchall()]
    widths = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(cols)]
    print(f"\n=== {title} ===")
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(v.ljust(w) for v, w in zip(r, widths)))


def main() -> None:
    conn = connect()
    cur = conn.cursor()
    show(cur, "RAW.CITY_DAY loaded by Airbyte (row count, cities, date range)",
         'SELECT COUNT(*) AS TOTAL_ROWS, COUNT(DISTINCT CITY) AS CITIES, MIN(DATE) AS FIRST_DAY, MAX(DATE) AS LAST_DAY '
         "FROM AIRSIGHT.RAW.CITY_DAY")
    show(cur, "RAW.CITY_DAY sample rows",
         'SELECT CITY, DATE, "PM2.5", PM10, NO2, AQI, AQI_BUCKET FROM AIRSIGHT.RAW.CITY_DAY LIMIT 5')
    show(cur, "OPS.INGESTION_LOG (validation history, newest first)",
         "SELECT RUN_TS, ROW_COUNT, CITY_COUNT, MIN_DATE, MAX_DATE, STATUS "
         "FROM AIRSIGHT.OPS.INGESTION_LOG ORDER BY RUN_TS DESC LIMIT 8")
    show(cur, "OPS.PIPELINE_ERRORS (logged task failures)",
         "SELECT TS, TASK_ID, LEFT(MESSAGE, 70) AS MESSAGE FROM AIRSIGHT.OPS.PIPELINE_ERRORS ORDER BY TS")
    conn.close()


if __name__ == "__main__":
    main()
