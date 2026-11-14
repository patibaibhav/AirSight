"""Check application logins without displaying credentials or changing data."""
from pathlib import Path
import os
import sys

from dotenv import load_dotenv
import snowflake.connector


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / '.env', interpolate=False)
    required = ('SNOWFLAKE_ACCOUNT', 'DBT_PASSWORD', 'BI_PASSWORD')
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print('Fill these entries in the local .env first: ' + ', '.join(missing))
        return 1
    for prefix, role in (('DBT', 'TRANSFORM_ROLE'), ('BI', 'BI_ROLE')):
        try:
            with snowflake.connector.connect(
                account=os.environ['SNOWFLAKE_ACCOUNT'],
                user=os.getenv(prefix + '_USER', prefix + '_USER'),
                password=os.environ[prefix + '_PASSWORD'],
                role=role,
                login_timeout=20,
                network_timeout=30,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('select current_user(), current_role()')
                    user, active_role = cursor.fetchone()
                    if active_role != role:
                        print(f'{prefix}: unexpected active role')
                        return 1
                    print(f'{prefix}: connected as {user} with {active_role}')
        except snowflake.connector.errors.Error as error:
            print(f'{prefix}: connection failed (code {error.errno}, SQLSTATE {error.sqlstate}).')
            print('Check the account identifier, password, role grants, and network access.')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
