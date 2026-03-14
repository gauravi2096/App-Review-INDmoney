# Phase 3: LLM Analysis

Reads **cleaned_reviews** from the database, estimates token usage, calls **Groq** or **Gemini** (based on limit), and persists **themes**, **quotes**, and **action ideas** to the **analysis** table for Phase 4 (Report Generation).

## Architecture (from PRODUCT-PULSE-ARCHITECTURE.md)

- **P3:** DB reader → token estimator → LLM client (Groq or Gemini) → prompt builder → response parser → DB writer.
- **Output:** One row per run in **analysis**: themes (3–5, each with label and 1–2 line description), quotes (3), action ideas (3). P4 reads this to compose the one-pager.

## Setup

```bash
cd phase-3-analyze
npm install
```

Set at least one API key:

- **Groq:** `GROQ_API_KEY` (get from [console.groq.com](https://console.groq.com))
- **Gemini:** `GEMINI_API_KEY` or `GOOGLE_API_KEY` (get from [aistudio.google.com](https://aistudio.google.com))

Ensure Phase 2 has been run so **cleaned_reviews** exists for a run.

## Run

```bash
npm run analyze
# or analyze a specific run
node run.js run_1773225025485_yer128yqu
```

By default, analyzes the **latest** cleaned run. Reviews are split into **batches** that stay under `P3_BATCH_TOKEN_LIMIT`; each batch is sent to the LLM (Groq or Gemini). If there are multiple batches, a **synthesis** pass consolidates batch outputs into the final 3–5 themes, 3 quotes, and 3 action ideas.

## Export analysis to JSON

To view the latest analysis in the editor (similar to Phase 1’s reviews.json):

```bash
npm run export-analysis
# or custom path
node export-analysis.js ./phase3-analysis.json
```

Writes **phase3-analysis.json** in this folder (or the path you give) with `run_id`, `analyzed_at`, `themes` (array of `{ label, description }`), `quotes`, and `actionIdeas`.

## Configuration (env)

| Env | Default | Description |
|-----|---------|-------------|
| `P3_DB_PATH` | `../phase-1-ingest/data/product-pulse.db` | Same DB as P1/P2. |
| `P3_GROQ_TOKEN_LIMIT` | `6000` | Use Groq if estimated tokens ≤ this; else Gemini. |
| `P3_BATCH_TOKEN_LIMIT` | `4000` | Max tokens per batch prompt; reviews are split to stay under this. |
| `P3_BATCH_DELAY_MS` | `15000` | Delay (ms) between batch LLM calls to avoid rate limits (e.g. Groq TPM). |
| `GROQ_API_KEY` | — | Required for Groq (e.g. from repo root `.env`). |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | — | Required for Gemini (if over limit or no Groq key). |
| `P3_GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model name. |
| `P3_GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name. |

## Contents

- **config.js** – DB path, token limit, API keys, model names.
- **db.js** – Open DB, **analysis** table, getCleanedReviews, upsertAnalysis, getAnalysis, getLatestAnalysis.
- **export-analysis.js** – CLI to export latest analysis to phase3-analysis.json.
- **tokenEstimator.js** – Rough token count (~4 chars per token).
- **batcher.js** – Split reviews into batches under `P3_BATCH_TOKEN_LIMIT`.
- **promptBuilder.js** – Per-batch prompt: reviews + JSON schema (themes, quotes, actionIdeas).
- **synthesisPromptBuilder.js** – Consolidate multiple batch results into one final JSON.
- **responseParser.js** – Extract JSON, validate (max 5 themes, 3 quotes, no PII in quotes).
- **llmClient.js** – Groq (fetch) and Gemini (@google/genai); `complete(provider, prompt, config)`.
- **run.js** – Load cleaned → batch → LLM per batch → synthesize if needed → upsert analysis.

## Data

- **analysis** table: `id`, `run_id` (unique), `themes_json` (array of `{ label, description }`), `quotes_json`, `action_ideas_json`, `analyzed_at`.
- P4 reads **analysis** by run_id to build the one-pager.
