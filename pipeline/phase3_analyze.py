"""Phase 3: Read cleaned_reviews, batch, call Groq, parse JSON, synthesize, persist analysis."""
import json
import re
import time
from typing import Any

import requests
from requests.exceptions import HTTPError

from . import config
from . import db as pipeline_db

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text) + 3) // 4

def _build_prompt(reviews: list[dict]) -> str:
    lines = [f"[{r['id']}] (rating {r['rating']}) {r['text']}" for r in reviews]
    return f"""You are analyzing app store reviews for a product team. Below are cleaned review texts with id and rating.

REVIEWS:
{chr(10).join(lines)}

TASK: Respond with exactly one JSON object (no markdown, no code fence) with these keys:
- "themes": array of 3 to 5 theme objects, each with "label" (short theme name), "description" (1–2 line description), and "reviewCount" (number of reviews in this batch that fit this theme; integer).
- "quotes": array of exactly 3 objects, each with "text" (one short representative quote from the reviews; exact wording where possible) and "rating" (the star rating 1–5 of the review this quote came from). Do not include emails, names, or IDs in text.
- "actionIdeas": array of exactly 3 concrete product action ideas (one line each) that the team could take based on these reviews.

Keep labels and action ideas concise. Ensure no PII in quotes.
JSON:"""

def _build_synthesis_prompt(batch_results: list[dict]) -> str:
    parts = []
    for i, b in enumerate(batch_results):
        themes = (b.get("themes") or [])
        t_str = "; ".join(
            f"{t.get('label', '')}: {t.get('description', '')} ({t.get('reviewCount', 0)} reviews)"
            for t in themes
        )
        quotes = (b.get("quotes") or [])
        q_str = " | ".join(
            f'"{q.get("text", "")}" [{q.get("rating", "")}/5]' if isinstance(q, dict) else str(q)
            for q in quotes
        )
        actions = "; ".join(b.get("actionIdeas") or [])
        parts.append(f"Batch {i+1}:\nThemes: {t_str}\nQuotes: {q_str}\nAction ideas: {actions}")
    return f"""You are consolidating analysis from multiple batches of the same app's store reviews. Each batch was analyzed separately. Below are the results.

{chr(10).join(parts)}

TASK: Produce ONE combined analysis. Merge overlapping themes into 3–5 distinct themes, each with "label", "description", and "reviewCount" (sum or estimate). Pick the 3 most representative user quotes; for each include "text" and "rating" (1–5). Output exactly one JSON object (no markdown) with keys:
- "themes": array of 3 to 5 objects with "label", "description", "reviewCount" (integer)
- "quotes": array of exactly 3 objects with "text" and "rating" (1–5)
- "actionIdeas": array of exactly 3 concrete product action ideas

JSON:"""

def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = m.group(1).strip() if m else text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None

def _normalize_analysis(parsed: dict) -> dict:
    themes = (parsed.get("themes") or [])[:5]
    themes = [
        {
            "label": str(t.get("label") or "").strip() or "Unnamed theme",
            "description": str(t.get("description") or "").strip(),
            "reviewCount": int(t["reviewCount"]) if t.get("reviewCount") is not None else None,
        }
        for t in themes if isinstance(t, dict)
    ]
    quotes = (parsed.get("quotes") or [])[:3]
    quotes = [
        {"text": str(q.get("text") or "").strip(), "rating": q.get("rating") if isinstance(q.get("rating"), (int, float)) else None}
        for q in quotes if isinstance(q, dict) and q.get("text")
    ]
    ideas = []
    for a in (parsed.get("actionIdeas") or [])[:3]:
        if isinstance(a, str):
            ideas.append(a.strip())
        elif isinstance(a, dict):
            ideas.append(str(a.get("text") or a.get("idea") or a.get("action") or "").strip())
        else:
            ideas.append(str(a).strip())
    ideas = [x for x in ideas if x]
    return {"themes": themes, "quotes": quotes, "actionIdeas": ideas}

def _groq_complete_once(prompt: str) -> str:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")
    r = requests.post(
        GROQ_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
        },
        json={
            "model": config.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You respond only with valid JSON. No markdown code blocks."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("Groq API: no content in response")
    return content


def _groq_complete(prompt: str) -> str:
    """Call Groq with retries on 429. Dashboard totals do not show per-minute RPM/TPM; one pipeline run can fire many calls in a short window."""
    max_attempts = 8
    for attempt in range(max_attempts):
        try:
            return _groq_complete_once(prompt)
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                wait = 60
                try:
                    ra = e.response.headers.get("Retry-After")
                    if ra and ra.isdigit():
                        wait = min(300, int(ra))
                except Exception:
                    pass
                if attempt < max_attempts - 1:
                    time.sleep(wait + attempt * 15)
                    continue
            raise
        except requests.RequestException as e:
            if attempt < max_attempts - 1 and "429" in str(e):
                time.sleep(60 + attempt * 15)
                continue
            raise

def _split_batches(reviews: list[dict], max_tokens: int) -> list[list[dict]]:
    base_prompt = _build_prompt([])
    base_tokens = _estimate_tokens(base_prompt)
    budget = max(0, max_tokens - base_tokens)
    if budget <= 0:
        return [reviews]
    batches = []
    current = []
    current_tokens = 0
    for r in reviews:
        line = f"[{r['id']}] (rating {r['rating']}) {r['text']}"
        line_tokens = _estimate_tokens(line) + 2
        if current and current_tokens + line_tokens > budget:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(r)
        current_tokens += line_tokens
    if current:
        batches.append(current)
    return batches

def run(db_path: str | None = None, run_id_arg: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    # Close DB before Groq calls: Supabase pooler drops idle connections (SSL EOF) if the
    # connection sits open during long API work.
    conn = pipeline_db.get_connection(db_path)
    try:
        reviews = pipeline_db.get_cleaned_reviews(conn, run_id_arg)
        if not reviews:
            return {"run_id": None, "analyzed": False}
        run_id = reviews[0]["run_id"]
    finally:
        conn.close()

    batches = _split_batches(reviews, config.BATCH_TOKEN_LIMIT)
    batch_results = []
    for i, batch in enumerate(batches):
        if i > 0:
            time.sleep(max(config.BATCH_DELAY_MS / 1000.0, 2.0))
        prompt = _build_prompt(batch)
        raw = _groq_complete(prompt)
        parsed = _extract_json(raw)
        if parsed:
            batch_results.append(_normalize_analysis(parsed))
    if not batch_results:
        raise RuntimeError("No valid batch results")
    if len(batch_results) == 1:
        analysis = batch_results[0]
    else:
        syn_prompt = _build_synthesis_prompt(batch_results)
        raw_syn = _groq_complete(syn_prompt)
        parsed_syn = _extract_json(raw_syn)
        if not parsed_syn:
            raise RuntimeError("Synthesis parse failed")
        analysis = _normalize_analysis(parsed_syn)

    conn = pipeline_db.get_connection(db_path)
    try:
        pipeline_db.upsert_analysis(conn, run_id, analysis)
    finally:
        conn.close()
    return {"run_id": run_id, "analyzed": True, "analysis": analysis}
