"""Ingestion tasks (owner: B). STUBS so the DAG is green from minute 1.

Real implementations (PLAN.md B7/B8/B10):
  trigger_sync   -> Airbyte Cloud API: token, POST /v1/jobs, store job id (XCom)
  wait_sync      -> poll GET /v1/jobs/{id} until succeeded / failed
  validate_raw   -> ingestion/validate_raw.py checks + OPS.INGESTION_LOG
  log_failure    -> on_failure_callback, writes OPS.PIPELINE_ERRORS
No network calls at import time.
"""
import logging

log = logging.getLogger(__name__)


def trigger_sync(**_):
    log.info("STUB trigger_sync")
    return "stub-job-id"


def wait_sync(**_):
    log.info("STUB wait_sync")


def validate_raw(**_):
    log.info("STUB validate_raw")


def log_failure(context):
    log.error("STUB log_failure: task failed %s", context.get("task_instance"))
