"""Validate AIRSIGHT.RAW.CITY_DAY after an Airbyte sync (owner: B).

STUB — implemented in PLAN.md step B7. Planned checks:
  - row count == EXPECTED_ROW_COUNT
  - distinct cities == EXPECTED_CITY_COUNT
  - per-column null % (report; fail only if CITY or DATE has nulls)
  - min/max date
Logs one row to AIRSIGHT.OPS.INGESTION_LOG; exits non-zero on failure.
"""
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("validate_raw")


def validate() -> dict:
    log.info("validate_raw stub: nothing checked yet")
    return {"status": "STUB"}


if __name__ == "__main__":
    validate()
