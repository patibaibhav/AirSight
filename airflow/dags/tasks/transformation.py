"""Transformation tasks (owner: R — the ONLY cross-owner seam).

CONTRACT (do not change signature without a handoff note):
    build_transformation_group(dag) -> TaskGroup   # group_id="transform", dbt_run >> dbt_test

Production commands:
  /opt/dbt-venv/bin/dbt run  --target prod --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
  /opt/dbt-venv/bin/dbt test --target prod --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
"""
from datetime import timedelta

from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup


def build_transformation_group(dag):
    with TaskGroup(group_id="transform", dag=dag) as group:
        command = '/opt/dbt-venv/bin/dbt {action} --target prod --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt'
        dbt_run = BashOperator(
            task_id="dbt_run", bash_command=command.format(action='run'),
            execution_timeout=timedelta(minutes=20),
        )
        dbt_test = BashOperator(
            task_id="dbt_test", bash_command=command.format(action='test'),
            execution_timeout=timedelta(minutes=20),
        )
        dbt_run >> dbt_test
    return group
