"""Phase 1: Fetch Play Store reviews, filter by date, validate, persist to raw_reviews."""
import time
from datetime import datetime, timedelta

from . import config
from . import db as pipeline_db

def _run_id() -> str:
    return f"run_{int(time.time() * 1000)}_{__import__('random').choice(__import__('string').ascii_lowercase)}{''.join(__import__('random').choices(__import__('string').ascii_lowercase + __import__('string').digits, k=8))}"

def _date_in_window(iso_date: str, weeks: int) -> bool:
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        cutoff = datetime.utcnow() - timedelta(weeks=weeks)
        return d.replace(tzinfo=None) >= cutoff if d.tzinfo else d >= cutoff
    except Exception:
        return False

def run(db_path: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    run_id = _run_id()
    try:
        from google_play_scraper import Sort, reviews
    except ImportError:
        raise RuntimeError("Install google-play-scraper: pip install google-play-scraper")

    all_reviews = []
    token = None
    page = 0
    while True:
        if token is None:
            result, token = reviews(
                config.APP_ID,
                lang=config.LANG,
                country=config.COUNTRY,
                sort=Sort.NEWEST,
                count=200,
            )
        else:
            result, token = reviews(
                config.APP_ID,
                lang=config.LANG,
                country=config.COUNTRY,
                continuation_token=token,
            )
        page += 1
        for r in result:
            at = r.get("at")
            date_str = at.isoformat() if hasattr(at, "isoformat") else str(at) if at else ""
            text = (r.get("content") or "").strip()
            rating = r.get("score")
            if isinstance(rating, (int, float)) and 1 <= rating <= 5:
                rating = int(rating)
            else:
                rating = None
            if not date_str or not text or rating is None:
                continue
            all_reviews.append({"rating": rating, "text": text, "date": date_str[:10] if len(date_str) >= 10 else date_str})
        if not token or len(result) < 200:
            break
        time.sleep(config.PAGINATION_DELAY)

    cutoff_date = (datetime.utcnow() - timedelta(weeks=config.DATE_WINDOW_WEEKS)).date()
    valid = []
    for r in all_reviews:
        try:
            d = datetime.fromisoformat(r["date"].replace("Z", "").split("T")[0]).date()
            if d < cutoff_date:
                continue
        except Exception:
            continue
        if not r["text"].strip() or not (1 <= r["rating"] <= 5):
            continue
        valid.append({"rating": r["rating"], "text": r["text"].strip(), "date": r["date"]})

    conn = pipeline_db.get_connection(db_path)
    try:
        pipeline_db.insert_raw_reviews(conn, run_id, valid)
    finally:
        conn.close()

    return {"run_id": run_id, "persisted": len(valid)}
