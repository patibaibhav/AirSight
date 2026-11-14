"""Run dbt with the local .env loaded, without shell-expanding passwords."""
from pathlib import Path
import os
import subprocess
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    load_dotenv(ROOT / '.env', interpolate=False)
    if not os.getenv('DBT_PASSWORD'):
        raise SystemExit('Fill DBT_PASSWORD in local .env first.')
    executable = Path(sys.executable).with_name('dbt')
    arguments = sys.argv[1:] or ['build', '--target', 'dev']
    return subprocess.run(
        [str(executable), *arguments, '--project-dir', str(ROOT / 'dbt'),
         '--profiles-dir', str(ROOT / 'dbt')],
        cwd=ROOT / 'dbt', check=False,
    ).returncode


if __name__ == '__main__':
    sys.exit(main())
