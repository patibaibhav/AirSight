FROM apache/airflow:2.10.5-python3.11

USER root
RUN python -m venv /opt/dbt-venv && chown -R airflow:root /opt/dbt-venv

USER airflow
# dbt lives in its own venv so it cannot clash with Airflow's pinned dependencies.
# Versions are pins to verify on first build; adjust here (B-owned) and tell R if dbt version changes.
RUN /opt/dbt-venv/bin/pip install --no-cache-dir dbt-snowflake==1.9.0
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir -r /tmp/requirements-airflow.txt
