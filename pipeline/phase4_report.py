"""Phase 4: Read latest analysis, call Gemini for one-pager, write HTML and report_metadata."""
import re
import time
from pathlib import Path

import requests

from . import config
from . import db as pipeline_db

def _count_words(text: str) -> int:
    if not text or not text.strip():
        return 0
    return len(text.strip().split())

def _truncate_words(text: str, max_words: int) -> tuple[str, bool]:
    words = text.strip().split()
    if len(words) <= max_words:
        return text.strip(), False
    return " ".join(words[:max_words]), True

def _theme_line(t: dict) -> str:
    count = f" ({t['reviewCount']} reviews)" if t.get("reviewCount") is not None else ""
    return f"- **{t.get('label', '')}**: {t.get('description', '')}{count}"

def _quote_line(q: dict | str) -> str:
    if isinstance(q, dict):
        text = q.get("text", "")
        rating = f" ({q.get('rating')}/5 stars)" if q.get("rating") is not None else ""
        return f'- {rating}: "{text}"' if rating else f'- "{text}"'
    return f'- "{q}"'

def _build_report_prompt(analysis: dict, max_words: int, report_context: dict | None) -> str:
    period = ""
    if report_context:
        total = report_context.get("totalReviews")
        dmin, dmax = report_context.get("dateMin"), report_context.get("dateMax")
        if dmin and dmax:
            period = f"Report period: {dmin} to {dmax}. Total reviews analyzed: {total}."
        elif total is not None:
            period = f"Total reviews analyzed: {total}."
    themes_block = "\n".join(_theme_line(t) for t in (analysis.get("themes") or []))
    quotes_block = "\n".join(_quote_line(q) for q in (analysis.get("quotes") or []))
    actions_block = "\n".join(f"- {a}" for a in (analysis.get("actionIdeas") or []))
    return f"""You are writing a weekly Product Pulse one-pager for internal stakeholders. You must FAITHFULLY reflect the Phase 3 analysis below. Do not summarize or reinterpret.

{period + chr(10) + chr(10) if period else ""}**THEMES (include every theme below with its full description and review count):**
{themes_block or "(none)"}

**USER QUOTES (include each quote below with its star rating):**
{quotes_block or "(none)"}

**ACTION IDEAS (include each action below verbatim):**
{actions_block or "(none)"}

TASK: Produce a plain-text report that faithfully reflects the data above. Structure:
1. A one-line title that includes the week or date range when provided.
2. A line stating the report period and total reviews analyzed (when provided).
3. "KEY THEMES" section: list each theme with its exact label, description, and review count.
4. "VOICE OF THE USER" section: list each quote with its exact text and star rating.
5. "RECOMMENDED ACTIONS" section: list each action idea exactly as given.

Rules:
- No markdown (no ** or ##). Use ALL CAPS for section headings and plain text for body.
- Maximum {max_words} words total. Be concise but do not omit theme descriptions, quotes, or action ideas.
- No names, emails, or other PII.
- Output only the report text, nothing else."""

def _gemini_complete_text(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    try:
        # google-generativeai is deprecated; use google-genai instead.
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini API: no text in response")
        return text.strip()
    except ImportError:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048}},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        text = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
        if not text:
            raise RuntimeError("Gemini API: no text in response")
        return text.strip()


def _gemini_complete_with_retries(prompt: str) -> str:
    last_err = None
    for attempt in range(6):
        try:
            return _gemini_complete_text(prompt)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            # Retry transient or quota/rate cases, then fallback in caller.
            if any(x in msg for x in ["429", "quota", "rate", "retry", "timeout", "temporar"]):
                if attempt < 5:
                    time.sleep(10 + attempt * 10)
                    continue
            break
    raise last_err


def _fallback_report_text(analysis: dict, report_context: dict | None) -> str:
    total = (report_context or {}).get("totalReviews")
    dmin = (report_context or {}).get("dateMin")
    dmax = (report_context or {}).get("dateMax")
    lines = ["PRODUCT PULSE WEEKLY"]
    if dmin and dmax and total is not None:
        lines.append(f"REPORT PERIOD: {dmin} to {dmax}. TOTAL REVIEWS ANALYZED: {total}.")
    elif total is not None:
        lines.append(f"TOTAL REVIEWS ANALYZED: {total}.")
    lines.append("")
    lines.append("KEY THEMES")
    for t in (analysis.get("themes") or [])[:5]:
        label = (t.get("label") or "Unnamed theme").strip()
        desc = (t.get("description") or "").strip()
        cnt = t.get("reviewCount")
        cnt_txt = f" ({cnt} reviews)" if cnt is not None else ""
        lines.append(f"- {label}: {desc}{cnt_txt}".strip())
    lines.append("")
    lines.append("VOICE OF THE USER")
    for q in (analysis.get("quotes") or [])[:3]:
        if isinstance(q, dict):
            qt = (q.get("text") or "").strip()
            rating = q.get("rating")
            if qt:
                lines.append(f'- "{qt}" ({rating}/5)' if rating is not None else f'- "{qt}"')
    lines.append("")
    lines.append("RECOMMENDED ACTIONS")
    for a in (analysis.get("actionIdeas") or [])[:3]:
        if a:
            lines.append(f"- {str(a).strip()}")
    return "\n".join(lines).strip()

def _text_to_html(body_text: str, title: str = "Product Pulse Weekly") -> str:
    def escape(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    lines = [l.strip() for l in body_text.split("\n") if l.strip()]
    blocks = []
    list_items = []
    for line in lines:
        if line == line.upper() and len(line) > 1 and re.search(r"[A-Z]", line):
            if list_items:
                blocks.append("<ul>\n" + "\n".join(f"  <li>{escape(t)}</li>" for t in list_items) + "\n</ul>")
                list_items = []
            blocks.append(f"<h2>{escape(line)}</h2>")
        elif line.startswith("- ") or line.startswith("* "):
            list_items.append(line[2:])
        else:
            if list_items:
                blocks.append("<ul>\n" + "\n".join(f"  <li>{escape(t)}</li>" for t in list_items) + "\n</ul>")
                list_items = []
            blocks.append(f"<p>{escape(line)}</p>")
    if list_items:
        blocks.append("<ul>\n" + "\n".join(f"  <li>{escape(t)}</li>" for t in list_items) + "\n</ul>")
    body = "\n".join(blocks)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/><title>{escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;background:#f5f7fb;margin:0;padding:24px;}}.email-shell{{max-width:720px;margin:0 auto;background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);padding:24px;line-height:1.6;}}h2{{font-size:1.05rem;margin:20px 0 8px;}}ul{{margin:4px 0;padding-left:20px;}}p{{margin:4px 0 8px;}}</style>
</head>
<body><div class="email-shell"><h1>{escape(title)}</h1><div class="content">{body}</div></div></body>
</html>"""

def run(db_path: str | None = None, run_id_arg: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    reports_dir = Path(config.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    conn = pipeline_db.get_connection(db_path)
    try:
        if run_id_arg:
            row = conn.execute("SELECT run_id, analyzed_at FROM analysis WHERE run_id = ?", (run_id_arg,)).fetchone()
            if not row:
                raise RuntimeError(f"No analysis found for run_id: {run_id_arg}")
            run_id = run_id_arg
            analyzed_at = row[1]
            analysis = pipeline_db.get_analysis(conn, run_id)
        else:
            latest = pipeline_db.get_latest_analysis(conn)
            if not latest:
                raise RuntimeError("No analysis found. Run Phase 3 first.")
            run_id = latest["run_id"]
            analyzed_at = latest["analyzed_at"]
            analysis = latest
        if not (analysis.get("themes") or analysis.get("quotes") or analysis.get("actionIdeas")):
            raise RuntimeError("Analysis has no themes, quotes, or action ideas.")
        report_context = pipeline_db.get_review_stats_for_run(conn, run_id)
    finally:
        conn.close()

    prompt = _build_report_prompt(analysis, config.MAX_WORDS, report_context)
    try:
        body_text = _gemini_complete_with_retries(prompt)
    except Exception:
        # Keep the pipeline operational when Gemini quota is exhausted.
        body_text = _fallback_report_text(analysis, report_context)
    word_count = _count_words(body_text)
    if word_count > config.MAX_WORDS:
        body_text, _ = _truncate_words(body_text, config.MAX_WORDS)
        word_count = _count_words(body_text)
    html = _text_to_html(body_text)
    report_filename = f"{run_id}.html"
    storage_path = reports_dir / report_filename
    storage_path.write_text(html, encoding="utf-8")
    week_start = (analyzed_at or "")[:10] if analyzed_at else __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d")
    artifact_path = f"reports/{report_filename}"
    body_html = html if config.DATABASE_URL else None

    conn = pipeline_db.get_connection(db_path)
    try:
        pipeline_db.insert_report_metadata(conn, run_id, run_id, week_start, word_count, artifact_path, body_html=body_html)
    finally:
        conn.close()
    return {"report_id": run_id, "path": str(storage_path)}
