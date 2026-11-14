"""AirSight pipeline DAG (owner: B).

trigger_sync >> wait_sync >> validate_raw >> transform (R's group) >> log_success
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

from tasks.ingestion import log_failure, trigger_sync, validate_raw, wait_sync
from tasks.transformation import build_transformation_group

default_args = {
    "owner": "airsight",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=20),
    "on_failure_callback": log_failure,
}

with DAG(
    dag_id="airsight_pipeline",
    description="Airbyte sync -> validate -> dbt run -> dbt test",
    start_date=datetime(2026, 11, 1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["airsight"],
) as dag:
    t_trigger = PythonOperator(task_id="trigger_sync", python_callable=trigger_sync)
    t_wait = PythonOperator(task_id="wait_sync", python_callable=wait_sync)
    t_validate = PythonOperator(task_id="validate_raw", python_callable=validate_raw)
    t_transform = build_transformation_group(dag)
    t_done = EmptyOperator(task_id="log_success")

    t_trigger >> t_wait >> t_validate >> t_transform >> t_done
