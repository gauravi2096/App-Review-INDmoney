"""Single SQLite DB for all phases. Same schema as Node P1–P5."""
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn

def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS raw_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rating INTEGER NOT NULL,
        text TEXT NOT NULL,
        date TEXT NOT NULL,
        run_id TEXT NOT NULL,
        ingested_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_raw_reviews_run_id ON raw_reviews(run_id);
    CREATE INDEX IF NOT EXISTS idx_raw_reviews_date ON raw_reviews(date);

    CREATE TABLE IF NOT EXISTS cleaned_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_review_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        text TEXT NOT NULL,
        date TEXT NOT NULL,
        run_id TEXT NOT NULL,
        cleaned_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_cleaned_reviews_run_id ON cleaned_reviews(run_id);

    CREATE TABLE IF NOT EXISTS analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL UNIQUE,
        themes_json TEXT NOT NULL,
        quotes_json TEXT NOT NULL,
        action_ideas_json TEXT NOT NULL,
        analyzed_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS report_metadata (
        report_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        week_start_date TEXT NOT NULL,
        report_status TEXT NOT NULL,
        word_count INTEGER NOT NULL,
        generated_at TEXT NOT NULL,
        storage_artifact_path TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        display_name TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_recipients_active ON recipients(active);

    CREATE TABLE IF NOT EXISTS delivery_status (
        report_id TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        status TEXT NOT NULL,
        sent_at TEXT,
        error_message TEXT,
        PRIMARY KEY (report_id, recipient_email)
    );
    """)
    conn.commit()

# --- Raw reviews (P1) ---
def insert_raw_reviews(conn: sqlite3.Connection, run_id: str, rows: list[dict]) -> None:
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    cur = conn.cursor()
    for r in rows:
        cur.execute(
            "INSERT INTO raw_reviews (rating, text, date, run_id, ingested_at) VALUES (?,?,?,?,?)",
            (r["rating"], r["text"], r["date"], run_id, now),
        )
    conn.commit()

def get_latest_run_id_raw(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute("SELECT run_id FROM raw_reviews ORDER BY ingested_at DESC LIMIT 1").fetchone()
    return row[0] if row else None

# --- Cleaned (P2) ---
def get_raw_reviews(conn: sqlite3.Connection, run_id: Optional[str] = None) -> list[dict]:
    if run_id:
        rows = conn.execute(
            "SELECT id, rating, text, date, run_id FROM raw_reviews WHERE run_id = ? ORDER BY date DESC",
            (run_id,),
        ).fetchall()
    else:
        rid = get_latest_run_id_raw(conn)
        if not rid:
            return []
        rows = conn.execute(
            "SELECT id, rating, text, date, run_id FROM raw_reviews WHERE run_id = ? ORDER BY date DESC",
            (rid,),
        ).fetchall()
    return [dict(r) for r in rows]

def delete_cleaned_by_run_id(conn: sqlite3.Connection, run_id: str) -> None:
    conn.execute("DELETE FROM cleaned_reviews WHERE run_id = ?", (run_id,))
    conn.commit()

def insert_cleaned_reviews(conn: sqlite3.Connection, rows: list[dict]) -> None:
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    cur = conn.cursor()
    for r in rows:
        cur.execute(
            "INSERT INTO cleaned_reviews (raw_review_id, rating, text, date, run_id, cleaned_at) VALUES (?,?,?,?,?,?)",
            (r["raw_review_id"], r["rating"], r["text"], r["date"], r["run_id"], now),
        )
    conn.commit()

# --- Analysis (P3) ---
def get_cleaned_reviews(conn: sqlite3.Connection, run_id: Optional[str] = None) -> list[dict]:
    if run_id:
        rows = conn.execute(
            "SELECT id, rating, text, date, run_id FROM cleaned_reviews WHERE run_id = ? ORDER BY date DESC",
            (run_id,),
        ).fetchall()
    else:
        row = conn.execute("SELECT run_id FROM cleaned_reviews ORDER BY cleaned_at DESC LIMIT 1").fetchone()
        if not row:
            return []
        rows = conn.execute(
            "SELECT id, rating, text, date, run_id FROM cleaned_reviews WHERE run_id = ? ORDER BY date DESC",
            (row[0],),
        ).fetchall()
    return [dict(r) for r in rows]

def upsert_analysis(conn: sqlite3.Connection, run_id: str, data: dict) -> None:
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    themes = json.dumps(data.get("themes") or [])
    quotes = json.dumps(data.get("quotes") or [])
    actions = json.dumps(data.get("actionIdeas") or [])
    conn.execute(
        """INSERT INTO analysis (run_id, themes_json, quotes_json, action_ideas_json, analyzed_at)
           VALUES (?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET
           themes_json=excluded.themes_json, quotes_json=excluded.quotes_json,
           action_ideas_json=excluded.action_ideas_json, analyzed_at=excluded.analyzed_at""",
        (run_id, themes, quotes, actions, now),
    )
    conn.commit()

def get_latest_analysis(conn: sqlite3.Connection) -> Optional[dict]:
    row = conn.execute(
        "SELECT run_id, analyzed_at, themes_json, quotes_json, action_ideas_json FROM analysis ORDER BY analyzed_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {
        "run_id": row[0],
        "analyzed_at": row[1],
        "themes": json.loads(row[2] or "[]"),
        "quotes": json.loads(row[3] or "[]"),
        "actionIdeas": json.loads(row[4] or "[]"),
    }

def get_analysis(conn: sqlite3.Connection, run_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT themes_json, quotes_json, action_ideas_json FROM analysis WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not row:
        return None
    return {
        "themes": json.loads(row[0] or "[]"),
        "quotes": json.loads(row[1] or "[]"),
        "actionIdeas": json.loads(row[2] or "[]"),
    }

# --- Report (P4) ---
def get_review_stats_for_run(conn: sqlite3.Connection, run_id: str) -> dict:
    row = conn.execute(
        "SELECT COUNT(*), MIN(date), MAX(date) FROM cleaned_reviews WHERE run_id = ?", (run_id,)
    ).fetchone()
    return {
        "totalReviews": row[0] or 0,
        "dateMin": row[1],
        "dateMax": row[2],
    }

def insert_report_metadata(
    conn: sqlite3.Connection,
    report_id: str,
    run_id: str,
    week_start_date: str,
    word_count: int,
    storage_path: str,
) -> None:
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        """INSERT INTO report_metadata (report_id, run_id, week_start_date, report_status, word_count, generated_at, storage_artifact_path)
           VALUES (?,?,?,'generated',?,?,?) ON CONFLICT(report_id) DO UPDATE SET
           week_start_date=excluded.week_start_date, report_status=excluded.report_status,
           word_count=excluded.word_count, generated_at=excluded.generated_at, storage_artifact_path=excluded.storage_artifact_path""",
        (report_id, run_id, week_start_date, word_count, now, storage_path),
    )
    conn.commit()

# --- Recipients & delivery (P5 / UI) ---
def get_report_metadata(conn: sqlite3.Connection, report_id: Optional[str] = None) -> Optional[dict]:
    if report_id:
        row = conn.execute(
            "SELECT report_id, week_start_date, storage_artifact_path FROM report_metadata WHERE report_id = ?",
            (report_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT report_id, week_start_date, storage_artifact_path FROM report_metadata ORDER BY generated_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return {"report_id": row[0], "week_start_date": row[1], "storage_artifact_path": row[2]}

def get_active_recipients(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT email, display_name FROM recipients WHERE active = 1 ORDER BY email"
    ).fetchall()
    return [{"email": r[0], "display_name": r[1] or None} for r in rows]

def upsert_delivery_status(
    conn: sqlite3.Connection,
    report_id: str,
    recipient_email: str,
    status: str,
    sent_at: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    conn.execute(
        """INSERT INTO delivery_status (report_id, recipient_email, status, sent_at, error_message)
           VALUES (?,?,?,?,?) ON CONFLICT(report_id, recipient_email) DO UPDATE SET
           status=excluded.status, sent_at=excluded.sent_at, error_message=excluded.error_message""",
        (report_id, recipient_email, status, sent_at, error_message),
    )
    conn.commit()

# --- UI: recipients CRUD and reports list ---
def list_recipients(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, email, display_name, active, created_at, updated_at FROM recipients ORDER BY email"
    ).fetchall()
    return [dict(r) for r in rows]

def add_recipient(conn: sqlite3.Connection, email: str, display_name: Optional[str] = None) -> None:
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        """INSERT INTO recipients (email, display_name, active, created_at, updated_at) VALUES (?,?,1,?,?)
           ON CONFLICT(email) DO UPDATE SET display_name=excluded.display_name, active=1, updated_at=excluded.updated_at""",
        (email, display_name or None, now, now),
    )
    conn.commit()

def get_recipient_by_id(conn: sqlite3.Connection, id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT id, email, display_name, active, created_at, updated_at FROM recipients WHERE id = ?", (id,)
    ).fetchone()
    return dict(row) if row else None

def update_recipient(
    conn: sqlite3.Connection, id: int, email: Optional[str] = None, display_name: Optional[str] = None
) -> bool:
    cur = conn.execute("SELECT email, display_name FROM recipients WHERE id = ?", (id,))
    row = cur.fetchone()
    if not row:
        return False
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    e = email if email is not None else row[0]
    d = display_name if display_name is not None else row[1]
    conn.execute("UPDATE recipients SET email=?, display_name=?, updated_at=? WHERE id=?", (e, d, now, id))
    conn.commit()
    return True

def deactivate_recipient_by_id(conn: sqlite3.Connection, id: int) -> bool:
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    cur = conn.execute("UPDATE recipients SET active=0, updated_at=? WHERE id=?", (now, id))
    conn.commit()
    return cur.rowcount > 0

def list_reports(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT report_id, run_id, week_start_date, report_status, word_count, generated_at, storage_artifact_path
           FROM report_metadata ORDER BY generated_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]

def get_delivery_summary_per_report(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT report_id, status, COUNT(*) as c FROM delivery_status GROUP BY report_id, status"
    ).fetchall()
    out = {}
    for r in rows:
        rid, status, c = r[0], r[1], r[2]
        if rid not in out:
            out[rid] = {"sent": 0, "failed": 0, "not_sent": 0}
        if status == "Sent":
            out[rid]["sent"] = c
        elif status == "Error":
            out[rid]["failed"] = c
        else:
            out[rid]["not_sent"] = c
    return out
