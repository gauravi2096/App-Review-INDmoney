"""Load config from environment (and optional .env)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
except ImportError:
    pass

def _path(name: str, default_subpath: str) -> str:
    p = os.environ.get(name)
    if p:
        return p
    root = Path(__file__).resolve().parent.parent
    return str(root / default_subpath)

# P1
APP_ID = os.environ.get("P1_APP_ID", "in.indwealth")
LANG = os.environ.get("P1_LANG", "en")
COUNTRY = os.environ.get("P1_COUNTRY", "in")
DATE_WINDOW_WEEKS = int(os.environ.get("P1_DATE_WINDOW_WEEKS", "12"))
# Shared hosted DB: set DATABASE_URL (e.g. Postgres from Supabase/Neon/Railway) so pipeline and Streamlit use the same DB.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or None
DB_PATH = os.environ.get("P1_DB_PATH") or os.environ.get("P6_DB_PATH") or _path("P1_DB_PATH", "data/product_pulse.db")
PAGINATION_DELAY = float(os.environ.get("P1_PAGINATION_DELAY_MS", "1500")) / 1000
MAX_RETRIES = int(os.environ.get("P1_MAX_RETRIES", "3"))

# P3
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("P3_GROQ_MODEL", "llama-3.1-8b-instant")
BATCH_TOKEN_LIMIT = int(os.environ.get("P3_BATCH_TOKEN_LIMIT", "4000"))
BATCH_DELAY_MS = int(os.environ.get("P3_BATCH_DELAY_MS", "15000"))

# P4
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.environ.get("P4_GEMINI_MODEL", "gemini-2.0-flash")
MAX_WORDS = int(os.environ.get("P4_MAX_WORDS", "400"))
REPORTS_DIR = os.environ.get("P4_REPORTS_DIR") or _path("P4_REPORTS_DIR", "data/reports")

# P5
FROM_ADDRESS = os.environ.get("P5_FROM_ADDRESS") or os.environ.get("EMAIL_FROM", "product-pulse@localhost")
REPLY_TO = os.environ.get("P5_REPLY_TO") or os.environ.get("EMAIL_REPLY_TO", "")
SMTP_HOST = os.environ.get("P5_SMTP_HOST") or os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("P5_SMTP_PORT") or os.environ.get("SMTP_PORT", "1025"))
SMTP_SECURE = (os.environ.get("P5_SMTP_SECURE") or os.environ.get("SMTP_SECURE", "")).lower() == "true"
SMTP_USER = os.environ.get("P5_SMTP_USER") or os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("P5_SMTP_PASS") or os.environ.get("SMTP_PASS", "")
SMTP_URL = os.environ.get("P5_SMTP_URL") or os.environ.get("SMTP_URL", "")
