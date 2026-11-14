"""Transformation tasks (owner: R — the ONLY cross-owner seam).

CONTRACT (do not change signature without a handoff note):
    build_transformation_group(dag) -> TaskGroup   # group_id="transform", dbt_run >> dbt_test

STUB created by B in the scaffold commit. R replaces the body with BashOperators:
  /opt/dbt-venv/bin/dbt run  --target prod --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
  /opt/dbt-venv/bin/dbt test --target prod --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
"""
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup


def build_transformation_group(dag):
    with TaskGroup(group_id="transform", dag=dag) as group:
        dbt_run = EmptyOperator(task_id="dbt_run")
        dbt_test = EmptyOperator(task_id="dbt_test")
        dbt_run >> dbt_test
    return group
