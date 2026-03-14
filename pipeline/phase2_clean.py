"""Phase 2: Read raw_reviews, normalize and anonymize, write cleaned_reviews."""
import re
from datetime import datetime

from . import config
from . import db as pipeline_db

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
USER_ID_REGEX = re.compile(
    r"\b(?:user[_\s]?id|customer[_\s]?id|ref[_\s]?no\.?|id[:\s#]*)\s*[#:]?\s*[a-zA-Z0-9-]{4,}\b",
    re.I,
)

def _normalize_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    return " ".join(text.strip().split())

def _anonymize(text: str) -> str:
    if not text:
        return ""
    text = EMAIL_REGEX.sub("[email redacted]", text)
    text = USER_ID_REGEX.sub("[id redacted]", text)
    return text

def _normalize_date(date_str: str) -> str | None:
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()[:10]
    try:
        d = datetime.fromisoformat(date_str)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return None

def run(db_path: str | None = None, run_id_arg: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    conn = pipeline_db.get_connection(db_path)
    try:
        raw = pipeline_db.get_raw_reviews(conn, run_id_arg)
        if not raw:
            return {"run_id": None, "cleaned": 0}
        run_id = raw[0]["run_id"]
        cleaned = []
        for r in raw:
            text_norm = _normalize_text(r.get("text") or "")
            text_anon = _anonymize(text_norm)
            date_norm = _normalize_date(r.get("date") or "")
            rating = r.get("rating")
            if rating is None or not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
                continue
            rating = int(rating)
            if not date_norm or not text_anon:
                continue
            cleaned.append({
                "raw_review_id": r["id"],
                "rating": rating,
                "text": text_anon,
                "date": date_norm,
                "run_id": run_id,
            })
        pipeline_db.delete_cleaned_by_run_id(conn, run_id)
        pipeline_db.insert_cleaned_reviews(conn, cleaned)
        return {"run_id": run_id, "cleaned": len(cleaned)}
    finally:
        conn.close()
