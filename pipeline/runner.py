"""Run the full pipeline P1 -> P2 -> P3 -> P4 -> P5."""
from . import config
from . import phase1_ingest
from . import phase2_clean
from . import phase3_analyze
from . import phase4_report
from . import phase5_email

def run_weekly_pipeline(db_path: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    results = {}
    # P1
    r1 = phase1_ingest.run(db_path)
    results["phase1"] = r1
    run_id = r1.get("run_id")
    if not run_id or r1.get("persisted", 0) == 0:
        return results
    # P2
    r2 = phase2_clean.run(db_path, run_id)
    results["phase2"] = r2
    # P3
    r3 = phase3_analyze.run(db_path, run_id)
    results["phase3"] = r3
    if not r3.get("analyzed"):
        return results
    # P4
    r4 = phase4_report.run(db_path, run_id)
    results["phase4"] = r4
    # P5
    r5 = phase5_email.run(db_path, r4.get("report_id"))
    results["phase5"] = r5
    return results
