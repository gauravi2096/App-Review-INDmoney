# Phase 1: Ingest

Fetches Google Play Store reviews for INDmoney via **google-play-scraper**, filters to the last 8–12 weeks, validates required fields, and persists to the **raw_reviews** table.

## Architecture (from PRODUCT-PULSE-ARCHITECTURE.md)

- **P1 Ingest:** Review Fetcher (google-play-scraper) → date filter → English language filter → validator → database writer.
- **Output:** Raw reviews in DB (English only) with `rating`, `text`, `date`, `run_id`, `ingested_at`.

## Setup

```bash
cd phase-1-ingest
npm install
```

## Run

```bash
npm run ingest
# or
node run.js
```
At the end of each run, the filtered dataset (English-only, text ≥ 5 words, no title) is automatically exported to **reviews.json** and opened in your default application so you can inspect the processed reviews without running any manual commands.

## View stored reviews

```bash
npm run view-reviews
# show latest 100
node view-reviews.js 100
```
Uses `P1_DB_PATH`; defaults to 50 reviews, max 500 per run.

## Export reviews to JSON

Ingest automatically writes **reviews.json** after each run. To export manually (e.g. to a different path):

```bash
npm run export-reviews
# or custom output path
node export-reviews.js ./reviews.json
```
Uses `P1_DB_PATH`; writes the same JSON array as the automatic step.

## Configuration (env)

| Env | Default | Description |
|-----|---------|-------------|
| `P1_APP_ID` | `in.indwealth` | INDmoney Play Store app ID |
| `P1_LANG` | `en` | Language code for reviews |
| `P1_COUNTRY` | `in` | Country code for reviews |
| `P1_DATE_WINDOW_WEEKS` | `12` | Include reviews from last N weeks (8–12) |
| `P1_DB_PATH` | `./data/product-pulse.db` | SQLite database path |
| `P1_PAGINATION_DELAY_MS` | `1500` | Delay (ms) between pagination requests; increase (e.g. 3000) to reduce rate limiting |
| `P1_MAX_RETRIES` | `3` | Max retries per Play request on transient errors (e.g. ECONNRESET) |
| `P1_RETRY_DELAY_MS` | `3000` | Base delay (ms) before first retry; doubles each attempt (exponential backoff) |

## Programmatic use

```js
import { run } from './run.js';
const result = await run(); // { runId, persisted }
```

## Contents

- **config.js** – Configuration (appId, lang, country, date window, db path).
- **reviewFetcher.js** – Fetches reviews via google-play-scraper (pagination, NEWEST sort).
- **dateFilter.js** – Keeps only reviews from the last N weeks.
- **languageFilter.js** – Keeps only reviews detected as English (franc).
- **validator.js** – Ensures rating (1–5), text (≥ 5 words), date; drops invalid rows.
- **db.js** – SQLite: `raw_reviews` table, insert and count helpers.
- **run.js** – Ingest job: fetch → date filter → English filter → validate → persist.
- **view-reviews.js** – CLI to view raw_reviews from the DB (latest first).
- **export-reviews.js** – CLI to export raw_reviews to JSON for inspection.

## Data

- Database and tables are created automatically under `./data/` (or `P1_DB_PATH`).
- Table `raw_reviews`: `id`, `rating`, `text`, `date`, `run_id`, `ingested_at`.
