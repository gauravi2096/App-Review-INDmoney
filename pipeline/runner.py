"""Run the full pipeline P1 -> P2 -> P3 -> P4 -> P5."""
import random
import string
import time

from . import config
from . import phase1_ingest
from . import phase2_clean
from . import phase3_analyze
from . import phase4_report
from . import phase5_email
from . import db as pipeline_db

_PHASE_ORDER = ["phase1", "phase2", "phase3", "phase4", "phase5"]

def _new_run_id() -> str:
    return f"run_{int(time.time() * 1000)}_{random.choice(string.ascii_lowercase)}{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"

def _current_phase(results: dict) -> str:
    """Which phase was in flight when an exception hit, inferred from which phases already
    recorded a result. Covers both a phase's own exception and a DB-connectivity failure in
    the phase's surrounding get_connection() calls (neither of which record a result)."""
    done = [p for p in _PHASE_ORDER if p in results]
    idx = len(done)
    return _PHASE_ORDER[idx] if idx < len(_PHASE_ORDER) else "unknown"

def _finalize_run(db_path: str, run_id: str, status: str, failed_phase: str | None = None, error_message: str | None = None) -> None:
    """Best-effort: if the DB itself is unreachable there is nothing further to persist here."""
    try:
        conn = pipeline_db.get_connection(db_path)
        try:
            pipeline_db.update_pipeline_run(conn, run_id, status, failed_phase=failed_phase, error_message=error_message)
        finally:
            conn.close()
    except Exception:
        pass

def run_weekly_pipeline(db_path: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    run_id = _new_run_id()
    results = {}
    try:
        conn = pipeline_db.get_connection(db_path)
        try:
            pipeline_db.create_pipeline_run(conn, run_id)
        finally:
            conn.close()

        # P1
        r1 = phase1_ingest.run(db_path, run_id=run_id)
        results["phase1"] = r1
        if not r1.get("run_id") or r1.get("persisted", 0) == 0:
            _finalize_run(db_path, run_id, "failed", failed_phase="phase1", error_message="No reviews ingested (0 persisted in the date window)")
            return results
        # P2
        r2 = phase2_clean.run(db_path, run_id)
        results["phase2"] = r2
        # P3
        r3 = phase3_analyze.run(db_path, run_id)
        results["phase3"] = r3
        if not r3.get("analyzed"):
            _finalize_run(db_path, run_id, "failed", failed_phase="phase3", error_message="Phase 3 did not produce an analysis")
            return results
        # P4
        r4 = phase4_report.run(db_path, run_id)
        results["phase4"] = r4
        # P5
        r5 = phase5_email.run(db_path, r4.get("report_id"))
        results["phase5"] = r5

        fallback_used = bool(r3.get("fallback_used")) or bool(r4.get("fallback_used"))
        _finalize_run(db_path, run_id, "success_with_fallback" if fallback_used else "success")
        return results
    except Exception as e:
        _finalize_run(db_path, run_id, "failed", failed_phase=_current_phase(results), error_message=f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    import sys
    try:
        out = run_weekly_pipeline()
        print("Pipeline completed:", out)
        sys.exit(0)
    except Exception as e:
        print("Pipeline failed:", e, file=sys.stderr)
        sys.exit(1)
