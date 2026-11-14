"""Prompt locally for credentials; input is hidden and never logged."""
from getpass import getpass
from pathlib import Path

from dotenv import set_key


def main() -> None:
    env_path = Path(__file__).resolve().parents[2] / '.env'
    if not env_path.exists():
        raise SystemExit('Create the local .env from .env.example first.')
    env_path.chmod(0o600)
    for key in ('DBT_PASSWORD', 'BI_PASSWORD'):
        password = getpass(f'Enter your saved {key} (hidden): ')
        if not password:
            raise SystemExit(f'{key} was empty; stopped.')
        set_key(str(env_path), key, password, quote_mode='always')
        env_path.chmod(0o600)
    print('Credentials saved in the git-ignored local .env.')


if __name__ == '__main__':
    main()
