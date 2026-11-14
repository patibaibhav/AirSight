"""Ingestion tasks (owner: B).

trigger_sync -> Airbyte Cloud API: fresh token, POST /v1/jobs, returns job id (XCom)
wait_sync    -> poll GET /v1/jobs/{id} until succeeded; raises on failed/cancelled/timeout
validate_raw -> ingestion/validate_raw.py checks + OPS.INGESTION_LOG
log_failure  -> on_failure_callback, writes OPS.PIPELINE_ERRORS (never raises)
No network calls at import time. Config only from env vars.
"""
import logging
import os
import time

import requests

log = logging.getLogger(__name__)

API = "https://api.airbyte.com/v1"
TIMEOUT = 30  # seconds per HTTP call


def _token() -> str:
    resp = requests.post(
        f"{API}/applications/token",
        json={
            "client_id": os.environ["AIRBYTE_CLIENT_ID"],
            "client_secret": os.environ["AIRBYTE_CLIENT_SECRET"],
            "grant_type": "client_credentials",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}", "Accept": "application/json"}


def trigger_sync(**_) -> str:
    connection_id = os.environ["AIRBYTE_CONNECTION_ID"]
    resp = requests.post(
        f"{API}/jobs",
        json={"connectionId": connection_id, "jobType": "sync"},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    job_id = str(resp.json()["jobId"])
    log.info("Triggered Airbyte sync, job id %s", job_id)
    return job_id  # pushed to XCom as return_value


def wait_sync(ti, **_) -> None:
    job_id = ti.xcom_pull(task_ids="trigger_sync")
    if not job_id:
        raise RuntimeError("no Airbyte job id from trigger_sync")
    poll = int(os.environ.get("AIRBYTE_POLL_SECONDS", "15"))
    deadline = time.time() + int(os.environ.get("AIRBYTE_SYNC_TIMEOUT_SECONDS", "900"))
    while time.time() < deadline:
        resp = requests.get(f"{API}/jobs/{job_id}", headers=_headers(), timeout=TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        status = body.get("status")
        log.info("Airbyte job %s status=%s rowsSynced=%s", job_id, status, body.get("rowsSynced"))
        if status == "succeeded":
            return
        if status in ("failed", "cancelled", "incomplete"):
            raise RuntimeError(f"Airbyte job {job_id} ended with status {status}")
        time.sleep(poll)
    raise TimeoutError(f"Airbyte job {job_id} did not finish in time")


def validate_raw(**_) -> None:
    from validate_raw import validate  # lazy: ingestion/ is on PYTHONPATH in the container

    validate()


def log_failure(context) -> None:
    """Failure callback: record in OPS.PIPELINE_ERRORS; must never raise."""
    try:
        ti = context.get("task_instance")
        message = str(context.get("exception"))[:2000]
        log.error("Task failed: dag=%s task=%s error=%s", ti.dag_id, ti.task_id, message)
        from validate_raw import connect

        conn = connect()
        try:
            conn.cursor().execute(
                "INSERT INTO AIRSIGHT.OPS.PIPELINE_ERRORS (dag_id, task_id, run_id, message) "
                "VALUES (%s, %s, %s, %s)",
                (ti.dag_id, ti.task_id, context.get("run_id"), message),
            )
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 - callback must not mask the original failure
        log.exception("Could not write failure to OPS.PIPELINE_ERRORS")
