"""Load the source CSV into RAW_DEV only, retaining original headers and nulls."""
from pathlib import Path
import logging
import os

from dotenv import load_dotenv
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


def main() -> None:
    load_dotenv(ROOT / '.env', interpolate=False)
    for key in ('SNOWFLAKE_ACCOUNT', 'DBT_PASSWORD'):
        if not os.getenv(key):
            raise SystemExit(f'Missing {key} in local .env')
    # Raw fields remain strings; staging performs defensive type conversion.
    frame = pd.read_csv(ROOT / 'data/city_day.csv', dtype=str)
    frame = frame.where(frame.notna(), None)
    if frame[['City', 'Date']].isna().any().any():
        raise SystemExit('Source CSV contains a missing City or Date')
    expected = (
        len(frame), frame['City'].nunique(),
        frame['Date'].min(), frame['Date'].max(),
    )
    with snowflake.connector.connect(
        account=os.environ['SNOWFLAKE_ACCOUNT'],
        user=os.getenv('DBT_USER', 'DBT_USER'),
        password=os.environ['DBT_PASSWORD'],
        role='TRANSFORM_ROLE',
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'AIRSIGHT_WH'),
        database=os.getenv('SNOWFLAKE_DATABASE', 'AIRSIGHT'),
        schema='RAW_DEV',
        login_timeout=20, network_timeout=60,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("show tables like 'CITY_DAY' in schema RAW_DEV")
            exists = bool(cursor.fetchall())
            if exists:
                LOGGER.info('RAW_DEV.CITY_DAY already exists; validating without inserting again')
            else:
                success, _, written, _ = write_pandas(
                    connection, frame, table_name='CITY_DAY', schema='RAW_DEV',
                    auto_create_table=True, overwrite=False, quote_identifiers=True,
                )
                if not success or written != len(frame):
                    raise RuntimeError('Upload did not complete; inspect RAW_DEV before retrying')
                LOGGER.info('Loaded %d rows; preserved all %d CSV headers', written, len(frame.columns))
            cursor.execute(
                'select count(*), count(distinct "City"), '
                'min("Date"), max("Date") from RAW_DEV.CITY_DAY'
            )
            actual = cursor.fetchone()
            if actual != expected:
                raise RuntimeError(f'RAW_DEV summary mismatch: expected {expected}, got {actual}')
            cursor.execute('select * from RAW_DEV.CITY_DAY limit 0')
            headers = [column[0] for column in cursor.description]
            if headers != list(frame.columns):
                raise RuntimeError('RAW_DEV column names differ from original CSV headers')
            LOGGER.info('Verified %d rows, %d cities, dates %s to %s', *actual)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    # Connector debug logs are unnecessary; never log connection arguments.
    logging.getLogger('snowflake.connector').setLevel(logging.WARNING)
    main()
