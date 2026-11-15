# AirSight conversational BI

From the repository root:

```sh
dbt/.venv/bin/python -m pip install -r app/requirements.txt
dbt/.venv/bin/python -m streamlit run app/streamlit_app.py
```

Alternatively install `app/requirements.txt` into a separate Python 3.11 venv.
Configuration loads from root `.env`: SNOWFLAKE_ACCOUNT, SNOWFLAKE_WAREHOUSE,
SNOWFLAKE_DATABASE, BI_USER, BI_PASSWORD, MARTS_SCHEMA. Default schema is DEV_MARTS;
switch to MARTS after production validation. No administrator credentials are used.
Production is now validated and Rahul's local `.env` selects MARTS.

No Gemini key is needed for the six sample questions. Rules cover city rankings,
two-city yearly comparisons, monthly city trends, seasonal month patterns,
March–May 2019/2020 comparison and a city/month heatmap. Broader questions use
Gemini when GEMINI_API_KEY and GEMINI_MODEL are both configured. The model name
is always read from configuration. Gemini receives the question and schema, not
Snowflake credentials or result rows. There is one SQL-error correction attempt,
then automatic rule fallback on model/API/guardrail failure. Unsupported fallback
questions receive a message directing the user to a supported sample.

The SQL parser checks one SELECT/WITH statement, permitted fully qualified marts,
no DDL/DML or external functions, and a maximum LIMIT 200. Rules bind values with
qmark parameters. Queries run under BI_ROLE with a 30-second statement timeout.
sqlglot is pinned explicitly for this guardrail (already installed through dbt).

Validation commands:

```sh
dbt/.venv/bin/python -m unittest discover -s app -p 'test_*.py' -v
dbt/.venv/bin/python app/validate_analytics.py --schema DEV_MARTS
dbt/.venv/bin/python app/validate_analytics.py --schema MARTS
dbt/.venv/bin/python app/smoke_ui.py
dbt/.venv/bin/python app/validate_explorer.py
```

The SQL validation appends reproducible query/result evidence to
`docs/report/R_sections.md`. The live UI smoke check disables Gemini in its own
process, submits a chat comparison, and exercises the heatmap sample button.
Gemini has been tested with mocked responses/errors; live API behavior awaits
local GEMINI_API_KEY and GEMINI_MODEL configuration. Do not claim live Gemini
validation until those are set and a real question has been checked.

All charts show historical observations. Missing/flagged AQI is excluded, not
filled; monthly averages, coverage and rolling-window definitions are documented
in dbt/README.md. Lockdown comparisons are descriptive, not causal.

## Dashboard and explorer controls

The redesigned interface has two workspaces:

- **Ask AirSight**: sample prompts, chat input and the last ten questions. Select a
  recent question to revisit its snapshot without another warehouse query.
- **Explore data**: choose a monthly city trend, annual city comparison, city
  rankings, seasonal pattern or heatmap. Select cities and a year range, then
  submit. Trend/seasonal views require one city; comparisons allow two or three.
  Ranking and heatmap views default to all cities when selected. Ranking size
  and cleanest/most-polluted ordering are configurable.

Explorer filters apply only to explorer results, not to chat questions. The result
title records the submitted selection; changing controls alone does not fetch data.
Filtered rankings and seasonal/heatmap AQI use daily-weighted means derived from
monthly average × usable-day count, not an unweighted average of monthly means.
Rolling trends can include the preceding two calendar months before the selected
display interval. Comparisons across 2020 use that partial year's available data.

Each result includes observed min/max summaries, a chart, expandable table/SQL,
bound values, fetch time and CSV/SQL downloads. CSV formula-like string labels
are escaped for spreadsheet applications; measurement values are unchanged.
Queries still use the existing SQL guardrail, BI_ROLE and 200-row cap.

Results are cached within each browser session for up to five minutes, with a
maximum of twenty entries. Repeating a request reuses its result; expiry is checked
on the next request, not by background polling. **Refresh from warehouse** bypasses
the explorer cache. **Clear saved results** clears that session's history/cache.
Opening the app, switching workspaces, changing filters or downloading a result
does not itself request warehouse data. Old snapshots remain labeled by fetch time.

For report screenshots, expand **Result table** and **View generated SQL** as needed.
Report screenshot capture remains manual. No new dependencies were added.
