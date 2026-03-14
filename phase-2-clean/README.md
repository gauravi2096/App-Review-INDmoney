# Phase 2: Clean & Structure

Reads **raw_reviews** from the same database as Phase 1, normalizes text and dates, anonymizes PII (emails, user IDs), enforces schema, and writes to the **cleaned_reviews** table for use by Phase 3 (LLM Analysis).

## Architecture (from PRODUCT-PULSE-ARCHITECTURE.md)

- **P2:** Reader from DB → text normalizer → date normalizer → anonymizer → schema enforcer → database writer.
- **Output:** Cleaned, anonymized review set in **cleaned_reviews** (linked to run_id). P3 reads this set.

## Setup

```bash
cd phase-2-clean
npm install
```

Ensure Phase 1 has been run so `raw_reviews` exists (e.g. in `../phase-1-ingest/data/product-pulse.db`).

## Run

```bash
npm run clean
# or clean a specific run
node run.js run_1773216637651_rnqms5l0k
```

By default, cleans the **latest** ingestion run (by `ingested_at`). Optionally pass a `run_id` to clean that run. Existing cleaned rows for that run are replaced.

## Configuration (env)

| Env | Default | Description |
|-----|---------|-------------|
| `P2_DB_PATH` | `../phase-1-ingest/data/product-pulse.db` | Same DB as Phase 1 (raw_reviews + cleaned_reviews). |

## Contents

- **config.js** – Database path (P2_DB_PATH).
- **db.js** – Open DB, create **cleaned_reviews** table, read raw_reviews, insert cleaned, delete by run_id.
- **textNormalizer.js** – Trim and collapse whitespace.
- **dateNormalizer.js** – Normalize to ISO 8601; invalid → null.
- **anonymizer.js** – Redact emails and user/customer ID patterns.
- **run.js** – Pipeline: read raw → normalize → anonymize → schema check → write cleaned.

## Data

- **cleaned_reviews** table: `id`, `raw_review_id`, `rating`, `text`, `date`, `run_id`, `cleaned_at`.
- Same DB as Phase 1; P3 reads **cleaned_reviews** by run_id.
