# Phase 4: Report Generation

Generates a **weekly one-pager** from Phase 3 analysis: top 3 themes (with **review count** when available), 3 user quotes (with **rating** when available), 3 action ideas. Uses **Gemini** to compose the narrative; the Gemini client **retries with exponential backoff** on 429 (quota limits). Renders HTML and writes report metadata to the same Product Pulse DB.

## Prerequisites

- Phase 3 must have been run at least once (analysis table populated).
- `GEMINI_API_KEY` in the repo root `.env` file.

## Setup

```bash
cd phase-4-report
npm install
```

## Usage

- **Latest analysis:**  
  `npm run report` or `node run.js`

- **Specific run:**  
  `node run.js <run_id>`

Outputs:

- **Storage:** `phase-4-report/reports/<run_id>.html` (HTML one-pager).
- **DB:** `report_metadata` table updated with `report_id`, `week_start_date`, `report_status`, `word_count`, `generated_at`, `storage_artifact_path`.

## Config (env)

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Required. Gemini API key (from repo root `.env`). |
| `P4_DB_PATH` | Optional. DB path (default: `../phase-1-ingest/data/product-pulse.db`). |
| `P4_REPORTS_DIR` | Optional. Directory for HTML reports (default: `./reports`). |
| `P4_GEMINI_MODEL` | Optional. Model name (default: `gemini-2.0-flash`). |
| `P4_MAX_WORDS` | Optional. Max words for one-pager (default: `250`). |

## Files

- **config.js** – Loads `.env` from repo root; DB path, Gemini key, reports dir.
- **db.js** – Opens shared DB; creates `report_metadata`; reads `analysis` (latest or by `run_id`).
- **llmClient.js** – Gemini-only client for plain-text generation.
- **composer.js** – Builds prompt from analysis, calls Gemini for one-pager text.
- **wordCounter.js** – Word count and truncation to `P4_MAX_WORDS`.
- **renderer.js** – Converts plain-text one-pager to HTML.
- **run.js** – Orchestrates: get analysis → compose → enforce word count → render HTML → write file → insert metadata.
