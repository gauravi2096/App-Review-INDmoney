# Phase 6: Orchestrator, UI Backend, and Scheduler

Provides a lightweight HTTP API and a weekly scheduler for the Product Pulse pipeline:

- Surfaces reports, recipients, and delivery status to a UI.
- Exposes a manual trigger endpoint to run P1→P5.
- Runs the full pipeline automatically on a cron schedule.

## Setup

```bash
cd phase-6-orchestrator
npm install
npm run dev   # or: npm start
```

By default the API listens on `http://localhost:4006`. Configure via `P6_PORT` in `.env`.

**Dashboard:** Open `http://localhost:4006/` to manage recipients and view weekly email delivery status. The pipeline remains fully automated; the dashboard does not expose a manual run button.

## API Endpoints

- `GET /api/health`  
  Returns `{ ok: true, phase: 6 }`.

- `GET /api/reports`  
  Lists report metadata (newest first). Each report includes `delivery_summary`: `{ sent, failed, not_sent }` counts.

- `GET /api/reports/:id`  
  Single report metadata row.

- `GET /api/reports/:id/html`  
  Returns the HTML body of the report (for embedding in UI). Reads from the Phase 4 `reports` directory.

- `GET /api/reports/:id/delivery`  
  Returns per-recipient delivery status for the report: `recipient_email`, `status`, `sent_at`, `error_message`.

- `GET /api/recipients`  
  Lists all recipients with `id`, `email`, `display_name`, `active`, `created_at`, `updated_at`.

- `POST /api/recipients`  
  Add (or reactivate) a recipient. Body: `{ "email": "...", "display_name": "..." }`.

- `PATCH /api/recipients/:id`  
  Update email and/or display_name. Body: `{ "email": "...", "display_name": "..." }` (both optional).

- `DELETE /api/recipients/:id`  
  Soft-delete: sets `active = 0` so the recipient no longer receives emails.

- `POST /api/pipeline/run`  
  Runs the full pipeline **once** (Phase 1 → … → Phase 5). Used by cron; not exposed in the dashboard.

## Scheduler

You can run the pipeline on a schedule in two ways.

### Option A: GitHub Actions (recommended for Monday 10:00 AM IST)

A workflow runs **every Monday at 10:00 AM IST** and triggers the pipeline by calling your Phase 6 server:

1. Deploy Phase 6 (and its DB) so it is reachable at a URL (e.g. `https://your-host/api/pipeline/run`).
2. In the repo: **Settings → Secrets and variables → Actions**, add:
   - **PIPELINE_TRIGGER_URL** (required): full URL to trigger, e.g. `https://your-phase6-host/api/pipeline/run`
   - **PIPELINE_TRIGGER_SECRET** (optional): bearer token if you add auth to the endpoint
3. Disable the in-process cron on the Phase 6 server so it doesn’t run twice:
   ```env
   P6_DISABLE_CRON=true
   ```

Workflow file: `.github/workflows/weekly-pipeline.yml`. You can also run it manually from the Actions tab.

### Option B: In-process cron (node-cron)

Phase 6 can run the pipeline on a weekly schedule inside the process:

- Default: `0 9 * * 1` (every Monday at 09:00 server time).
- Configure via `.env`:

```env
P6_WEEKLY_CRON=0 9 * * 1   # or your preferred cron schedule
P6_DB_PATH=../phase-1-ingest/data/product-pulse.db
P6_PORT=4006
```

When the cron fires, it calls the same `runWeeklyPipeline()` used by `POST /api/pipeline/run`.

## Files

- **package.json** – Express + node-cron + better-sqlite3 + dotenv.
- **config.js** – Loads `.env` from repo root; DB path, cron expression, API port.
- **db.js** – Helpers for reports, delivery, and recipients:
  - `listReports`, `getReport`, `getDeliverySummaryPerReport`, `getDeliveryStatus`
  - `listRecipients`, `addRecipient`, `getRecipientById`, `updateRecipient`, `deactivateRecipientById`
- **pipeline.js** – `runWeeklyPipeline()` spawns the existing phase scripts:
  - Phase 1: `node phase-1-ingest/run.js`
  - Phase 2: `node phase-2-clean/run.js`
  - Phase 3: `node phase-3-analyze/run.js`
  - Phase 4: `node phase-4-report/run.js`
  - Phase 5: `node phase-5-email/run.js`
- **server.js** – Express 5 API server; registers endpoints, wires cron to `runWeeklyPipeline`.

- **public/index.html** – Minimal dashboard: recipient add/edit/delete and weekly delivery table (sent/failed/pending per report). No pipeline trigger; pipeline runs on cron only.

