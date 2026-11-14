# AGENTS.md — AirSight agent rulebook

Every AI coding agent working in this repo MUST read this file and `PLAN.md` before doing anything. If this file and a user chat message disagree, the user wins — but never silently violate the ownership rules below; ask.

## 1. Project context (so you don't have to guess)

- **AirSight**: automated data-engineering pipeline for Indian city air quality. College DE microproject, group of 2, demo **16–17 Nov 2026**. Speed matters; scope is deliberately small.
- **Flow**: CSV (`data/city_day.csv`, Kaggle India AQI 2015–2020, 26 cities, daily) → **Airbyte Cloud** (File source, full-refresh overwrite) → **Snowflake** (`AIRSIGHT.RAW.CITY_DAY`) → **dbt Core** (staging + marts) → **Streamlit** conversational BI (Gemini free tier text-to-SQL + rule-based fallback). **Airflow** orchestrates trigger → validate → dbt run → dbt test.
- **Everything must be free** (Snowflake trial, Airbyte Cloud trial, Gemini free tier, GitHub, local/Codespaces). Do not add paid services, cloud resources that need a card, or heavy dependencies. Prefer standard library / already-listed packages. Pin versions of anything new.
- **Two humans, two machines, working at the same time.** Baibhav = **B** (Windows, 8 GB RAM: keep Airflow light). Rahul = **R** (Mac, 16 GB).
- Snowflake contract (names are fixed, do not rename): DB `AIRSIGHT`; schemas `RAW`, `RAW_DEV`, `STAGING`, `MARTS`, `DEV_STAGING`, `DEV_MARTS`, `OPS`; warehouse `AIRSIGHT_WH`; roles `AIRBYTE_ROLE`, `TRANSFORM_ROLE`, `BI_ROLE`; users `AIRBYTE_USER`, `DBT_USER`, `BI_USER`. dbt `--target dev` → reads `RAW_DEV`, writes `DEV_*`. `--target prod` → reads `RAW`, writes `STAGING`/`MARTS`.

## 2. Who are you working for?

The first message of your session says "I am Baibhav" or "I am Rahul". If it does not, **ask**. Then apply your owner's column below.

| Path | Owner |
|---|---|
| `ingestion/`, `airflow/` (except the file below), `data/`, `docs/handoff/B_to_R.md`, `docs/report/B_sections.md`, `docs/report/FINAL*`, `docs/screenshots/B_*`, root files (`README.md`, `PLAN.md`, `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.env.example`) | **B** |
| `dbt/`, `app/`, `sql/`, `airflow/dags/tasks/transformation.py`, `docs/handoff/R_to_B.md`, `docs/report/R_sections.md`, `docs/screenshots/R_*` | **R** |

### Hard rules
1. **Only edit files your owner owns.** Need a change elsewhere? Append a request to *your* handoff file (`B_to_R.md` or `R_to_B.md`) and tell the human. Never "just fix" the other person's file.
2. **Never create files outside your owned paths.** New file inside your folder is fine.
3. **No secrets in git, ever.** Real passwords/keys/tokens live only in the local `.env` (git-ignored). Never print them in logs, docs, screenshots, commit messages or chat. Only `.env.example` with empty values is committed. If a secret is needed and missing, ask the human.
4. **Don't change shared contracts** (Snowflake names above, `build_transformation_group(dag)` signature, `.env` key names, schema/table names of marts) without a written note in the handoff file and the human's OK.
5. **No new dependency** unless unavoidable; if added, pin the version in the right requirements file and tell the human.
6. **No destructive actions**: no `git push --force`, no `git reset --hard` on shared work, no `DROP`/`TRUNCATE`/`DELETE` in Snowflake outside objects your owner owns, no deleting the other person's files, no turning on paid features.
7. **Stay on free tier**: XS warehouse, auto-suspend 60 s. Don't leave long-running queries or loops. Don't hit Gemini in loops (free quota).
8. Don't invent data. Missing pollutant values are expected in the dataset; handle them, don't impute silently (document any imputation).

## 3. Git workflow (how we avoid merge conflicts)

- Single branch `main`, **trunk-based**, because ownership is by folder so edits never overlap.
- Before you start working and before every push: `git pull --rebase origin main`.
- Small commits, prefix with your letter: `[B] add validate_raw.py`, `[R] stg_city_day dedupe`.
- Push often (at least after every finished step in PLAN.md) so the other side can pull.
- If a rebase reports a conflict, **stop**. It means someone edited a non-owned file. Don't resolve by guessing; tell the human which file, and follow rule 1.
- Handoff files are **append-only**: add a dated entry at the bottom, never rewrite old ones.
- Generated/runtime output (`target/`, `logs/`, `.venv/`, `__pycache__/`, `.env`, Airflow DB) is git-ignored; never commit it.

Handoff entry format:
```
## 2026-11-14 18:40 — H4 RAW landed
- what: RAW.CITY_DAY loaded, 29531 rows
- columns: "City","Date","PM2.5",... (exact, as seen in Snowsight)
- needs from you: switch dbt prod run, adjust renamed CTE if names differ
```

## 4. Definition of done for any task

- It does what PLAN.md step says, runs locally, and you ran it (not just wrote it).
- Tests/validation relevant to your area pass (B: validate script + DAG run; R: `dbt build`, app answers sample questions).
- No secrets, no stray files, `git status` clean except intended changes, pulled + pushed.
- You appended the handoff note if the step is a handoff (H1–H7 in PLAN.md).
- You told the human in 2–3 lines what changed, how you verified, and what's next.

## 5. Coding standards (keep it simple — this is a 1-day build)

- Python 3.11, type hints where cheap, small functions, clear logging (`logging`, not `print`, in pipeline code). Config only from env vars (names in `.env.example`).
- SQL: Snowflake dialect, lowercase keywords OK but consistent; CTE-per-step; no `select *` in marts.
- dbt: staging = `view`, marts = `table`; every model has a description in `schema.yml`; mapping of raw column names happens in **one** `renamed` CTE only. No dbt packages.
- Airflow: DAG in `airflow/dags/airsight_pipeline.py`; cross-owner seam only through `tasks/transformation.py → build_transformation_group(dag)`. Defaults: retries 2, retry_delay 1 min, execution_timeout 20 min, failure callback logs to `OPS.PIPELINE_ERRORS`. DAG file must import quickly (no network calls at import time).
- Streamlit: LLM SQL must pass the guardrail (single `SELECT`/`WITH`, no DDL/DML keywords, forced `LIMIT`, only `MARTS_SCHEMA` tables) and run as read-only `BI_USER`. Fallback to `rules.py` on any LLM failure. Always show the generated SQL.

## 6. Role-specific guidance

### If you work for B (ingestion & orchestration)
- Airbyte Cloud is configured in its UI; document the click-path and non-secret IDs in `ingestion/README.md`. Airbyte stream `city_day`, **Full refresh | Overwrite**, manual schedule (Airflow triggers).
- Airbyte API (plain `requests`): token `POST https://api.airbyte.com/v1/applications/token`; trigger `POST https://api.airbyte.com/v1/jobs` body `{"connectionId": ..., "jobType": "sync"}`; poll `GET /v1/jobs/{jobId}`. Token expires in minutes — fetch it fresh inside the task.
- Airflow runs in ONE container (`airflow standalone`, SQLite, `mem_limit: 3g`) with dbt in a separate venv `/opt/dbt-venv`. Keep it light (disable example DAGs, no extra services).
- `validate_raw.py` checks row count, city count, date range, per-column null % and logs to `OPS.INGESTION_LOG`; non-zero exit on failure.
- Until R pushes the real `transformation.py`, use the stub group so the DAG stays green.

### If you work for R (transformation & analytics)
- Develop against `RAW_DEV` with `--target dev`, using `dbt/dev_tools/load_dev_raw.py` to load the CSV with original headers. Don't wait for Airbyte.
- When B posts the "RAW landed" handoff, run once with `--target prod` and adjust only the `renamed` CTE if column names differ.
- Handle types defensively: `try_to_date(to_varchar(...))`, `try_to_double(to_varchar(...))`.
- Tests: built-in + singular tests in `dbt/tests/`. Missing pollutant values are allowed (reported), negatives/impossible ranges fail.
- `app/` must run with only `.env` + `pip install -r app/requirements.txt`. Read the Gemini model name from `GEMINI_MODEL`; never hard-code a model or key.

## 7. Kick-off prompts (copy-paste to start each person's agent)

**Baibhav's agent**
> I am Baibhav (B). Read AGENTS.md and PLAN.md. Follow PLAN.md §6 (B1…B16) in order. Only edit B-owned paths. Start with B1–B3 (repo scaffold incl. stubs, `.env.example`, `.gitignore`, copy of AGENTS.md/PLAN.md, `data/city_day.csv`), push, then guide me through the Airbyte Cloud UI steps (B4, B5) and implement the code steps. Ask me for secrets; never write them into files that are committed. After each step tell me what to verify and append handoff notes when PLAN.md says so.

**Rahul's agent**
> I am Rahul (R). Read AGENTS.md and PLAN.md. Follow PLAN.md §7 (R1…R13) in order. Only edit R-owned paths. Start with R1–R2 (guide me through Snowflake signup and the setup SQL in PLAN.md §8, and the Gemini key), then after Baibhav's scaffold is pulled do R3–R13. Work on RAW_DEV with `--target dev` until Baibhav's "RAW landed" handoff. Ask me for secrets; never commit them. Append handoff notes when PLAN.md says so.

## 8. When in doubt

Ask the human, prefer the smaller change, and keep the other person unblocked: push early, write the handoff note, don't touch their files.
