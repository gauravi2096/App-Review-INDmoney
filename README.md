# INDmoney Review Pulse

A weekly automated pipeline that scrapes Google Play reviews for the INDmoney app, uses LLM-based analysis to cluster feedback into themes, and emails a one-pager report to a configurable recipient list every Monday at 10:00 AM IST (04:30 UTC) via GitHub Actions.

Pipeline: **ingest → clean → analyze → report → email**. A Streamlit app handles recipient management and delivery status.

## Why this exists

App Store rating is a direct install-conversion lever — a declining rating quietly costs new installs before anyone notices. This exists so someone doesn't have to manually read hundreds of reviews every week to catch that decline early. It's a small, real tool: currently 2 stakeholders are subscribed.

## What a report contains

Each report clusters the period's reviews into 3–5 themes, each with a description, a review count, representative user quotes, and recommended actions. From the actual **Jul 27, 2026** run — 943 reviews analyzed over the rolling window (see [Pipeline mechanics](#pipeline-mechanics) below):

| Theme | Reviews |
|---|---|
| App Performance / Stability | 43 |
| Feature Requests / Usability | 34 |
| Customer Support | 30 |
| Cashback / Rewards | 19 |
| Security / Trust | 10 |

Each theme ships with a short description, a couple of representative quotes pulled from actual reviews, and a recommended action — not just a count.

## Architecture

- **Streamlit (all-in-one, recommended)**: Run and deploy the full pipeline in one app. `pip install -r requirements.txt && streamlit run streamlit_app.py`. Manage recipients, click **Run weekly pipeline (P1→P5)** in the sidebar, view reports and delivery. See [STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md).
- **Node (phases 1–6)**: `phase-1-ingest` through `phase-6-orchestrator`. Run Phase 6: `cd phase-6-orchestrator && npm install && npm run dev`; open http://localhost:4006/.

### Pipeline mechanics

**Report period.** Fixed rolling lookback window measured from wall-clock execution time — not anchored to the previous run. Default 12 weeks, configurable via `P1_DATE_WINDOW_WEEKS`. A skipped or delayed run doesn't trigger catch-up logic; the next run just looks back the same window from its own execution time.

**Model mapping.**
- Phase 3 (theme analysis) uses **Groq** (`openai/gpt-oss-20b`) — many calls per run, one per review batch, paced to stay under the model's free-tier TPM ceiling (`P3_BATCH_DELAY_MS`, `P3_GROQ_MAX_TOKENS`; `reasoning_effort: "low"`, since gpt-oss-20b is a reasoning model that can otherwise spend its whole token budget on hidden reasoning tokens before emitting an answer).
- Phase 4 (report composition) uses **Gemini** (`gemini-2.0-flash`) — a single call per run.
- Phase 2 (cleaning) is regex-based normalization and PII redaction — no LLM call.
- Phase 5 (email) is pure SMTP — no LLM call.

**Resilience.** Both Phase 3 and Phase 4 fall back to deterministic output if their LLM call fails after retries — Phase 3 groups reviews by star rating instead of LLM-derived themes; Phase 4 composes the report from a fixed template instead of Gemini's prose. Either fallback logs the triggering exception and is recorded as a flag on that run's stored analysis/report, so a "successful" run that quietly used a fallback is distinguishable from one that used the real models.

**Run tracking.** Every pipeline run — scheduled, manual, or triggered from Streamlit — writes a row to a `pipeline_runs` table before Phase 1 starts, updated to `success`, `success_with_fallback`, or `failed` (with which phase and why) when it concludes, including on an uncaught exception. The dashboard's delivery table reads this directly, so a run that failed before ever reaching the email step is now visible instead of leaving zero trace. One real limit: a run that fails because the database itself is unreachable can't have a row written to it, by definition — that specific failure mode is only visible in GitHub Actions' own logs, not this table.

## PM thinking — key decisions

**Two LLM providers.** *Tension:* Phase 3 fires many calls (one per review batch); Phase 4 fires one. Running both through a single provider hit free-tier rate limits. *What I chose:* split providers — Groq for Phase 3, Gemini for Phase 4. *Why:* the split was originally forced by hitting limits on one provider, but it turned out to be volume-appropriate anyway — a fast, cheap model for the high-call-count analysis step, a stronger model for the single, higher-stakes composition call. *Principle:* a constraint can force an architecture that turns out to be correct on its own merits — worth keeping even after the constraint that caused it is no longer binding.

**Open-ended clustering over a fixed taxonomy.** *Tension:* a fixed taxonomy would make themes comparable week over week, which is what you want for trend tracking. But it also means only surfacing problems that fit predefined categories. *What I chose:* let the LLM decide theme labels fresh each run instead of clustering into a fixed list. *Why:* a fixed taxonomy risks a "streetlight effect" — you only see what you already thought to look for, and an emerging issue that doesn't fit any bucket goes silently missing. *Principle:* I traded trend-comparability for avoiding measurement bias. The planned fix for trend-tracking (rating-over-time, below) needs no taxonomy at all, so I don't have to choose between the two forever.

**Email as primary delivery, not the dashboard.** *Tension:* the Streamlit app could have been positioned as the place stakeholders check for the report. *What I chose:* email is the primary delivery surface; Streamlit is an admin and exploration tool, not the read surface. *Why:* the entire point of this project is to remove a manual chore — if consuming the output requires someone to remember to open a dashboard, I've just relocated the chore instead of removing it. *Principle:* match the delivery mechanism to the behavior you actually want (passive consumption), not the tooling that's easiest to build.

**Selective resilience, made honest instead of uniform.** *Tension:* I could build a fallback for every phase to maximize uptime, or accept that some phases are hard dependencies. I originally chose the latter for Phase 3: a "fallback" theme clustering would mean fabricating themes, which felt worse than not sending a report. *What changed:* a production incident — Groq deprecated the configured model mid-operation, and the replacement model's free-tier limits then caused a separate pacing failure — made "halt the entire pipeline" too costly to leave as the only option. *What I chose instead:* a Phase 3 fallback that's honest rather than fabricated — grouping reviews by star rating, real data, just not LLM-derived themes — paired with an explicit flag and log line so a fallback-recovered run is never silently indistinguishable from a real one. *Principle:* "don't fabricate output" and "don't have a fallback" aren't actually the same constraint — I'd conflated them the first time. The real rule is: degrade to something still true, and never hide that you degraded.

**Rolling window, not gap-aware.** *Tension:* a simple rolling window from execution time is predictable, but doesn't adjust if a run is skipped or delayed — the next run just looks back the same fixed window from wherever it actually executes. *What I chose:* kept it simple — no catch-up logic. *Why:* the date-range logic staying simple and predictable mattered more than handling the edge case of a missed run, especially at this scale. *Principle:* optimize for the common case explicitly, and document the edge-case tradeoff rather than adding complexity to silently paper over it.

## Honest limitations

- Theme clustering is LLM judgment, not validated against ground truth — no formal accuracy evaluation has been run yet.
- Both Phase 3 and Phase 4 now degrade to a deterministic fallback rather than halting, but a run that fails before that point — most concretely, the database itself being unreachable — still can't be recorded anywhere in-app. That gap showed up for real on three separate weeks (Aug 17, 24, 31) and had to be reconstructed manually from GitHub Actions logs afterward, not caught automatically.
- Phase 4's configured model (`gemini-2.0-flash`) was deprecated by Google after this was built; recent runs have been sending the deterministic fallback report rather than real Gemini output until the model name is updated — caught via the new fallback logging, not by design.
- Report period doesn't adjust for skipped runs — if a run is delayed, the next one's 12-week window doesn't "catch up," it just looks back 12 weeks from whenever it actually executes.
- The pipeline was deliberately paused for roughly 15 weeks (mid-April to late July 2026) during portfolio and interview prep. Not a reliability failure, but a visible gap in run history worth being upfront about.
- Small recipient list (2) — not yet tested at scale.
- No trend-over-time tracking on themes, by design (see above); only raw per-period snapshots currently.

## What I'd build next

1. **Rating-over-time trend.** Average star rating per report period, plotted as an interactive chart in the Streamlit dashboard, with a one-line summary added to the email itself since charts don't render reliably in most email clients. No taxonomy risk here — it's a raw number, not an LLM judgment, so it sidesteps the streetlight-effect tradeoff above entirely.
2. **A formal eval/validation harness for theme classification accuracy.** Planned as a separate, focused project rather than bolted onto this pipeline — measurement rigor is a distinct skill worth its own case study, not a footnote on this one.
3. **Competitive benchmarking** against other finance apps (e.g. Zerodha, Wealth Monitor) to distinguish INDmoney-specific issues from industry-wide patterns. Sequenced after the above, since it depends on having a validated theme model to compare against in the first place.
4. **Proactive failure alerting.** A failed or fallback-recovered run is currently only visible if someone opens the dashboard. A short Slack/email ping whenever a run's status isn't a clean `success` would close that loop — the run-tracking data this needs already exists, so it's mostly wiring, not new instrumentation.

## Setup

### Quick start (Streamlit, recommended)

1. Create `.env` at repo root (or set env) with `GROQ_API_KEY`, `GEMINI_API_KEY`, and SMTP vars (`P5_FROM_ADDRESS`, `P5_SMTP_*`). Optional: `DATABASE_URL` for a shared Postgres DB (see below).
2. `pip install -r requirements.txt && streamlit run streamlit_app.py`.
3. Open http://localhost:8501/. Add recipients, then click **Run weekly pipeline (P1→P5)** in the sidebar.

### Quick start (Node)

1. Create `.env` at repo root with API keys and SMTP (see each `phase-*/README.md`).
2. `cd phase-6-orchestrator && npm install && npm run dev`.
3. Open http://localhost:4006/ to manage recipients and view delivery. Pipeline runs on cron or via GitHub Actions.

### Deploy on Streamlit

Deploy this repo on [Streamlit Community Cloud](https://share.streamlit.io); main file `streamlit_app.py`. Set secrets: `DATABASE_URL` (see below), `GROQ_API_KEY`, `GEMINI_API_KEY`, and SMTP (`P5_*`) so the built-in pipeline can run. See [STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md).

### Shared hosted database (recommended for pipeline + UI)

To have **recipients you add in the Streamlit UI** used by the **scheduled Monday pipeline**, use a single hosted Postgres database for both:

1. Create a Postgres database (e.g. [Supabase](https://supabase.com), [Neon](https://neon.tech), [Railway](https://railway.app)). **Supabase:** use the **connection pooler** URI (port **6543**), not the direct one (5432): Project Settings → Database → Connection string → **Connection pooling** (Transaction mode).
2. Set **`DATABASE_URL`** to that URI (e.g. `postgresql://user:pass@host:6543/postgres`) in:
   - **Streamlit Cloud**: App settings → Secrets.
   - **GitHub Actions**: Repo Settings → Secrets and variables → Actions → `DATABASE_URL`.

The pipeline and Streamlit app both connect to this DB when `DATABASE_URL` is set. No SQLite files or artifacts; report HTML is stored in the DB when using a hosted DB so the Monday run can send email without file storage.

### Automatic weekly email (Monday 10:00 AM IST)

The workflow **`.github/workflows/weekly-product-pulse.yml`** runs the **Python pipeline on the GitHub Actions runner** every Monday at 10:00 AM IST. It **requires** a shared DB so it uses the same recipients as the Streamlit UI.

**Secrets** (Settings → Secrets and variables → Actions):

- **Required:** `DATABASE_URL` (Postgres connection string), `GROQ_API_KEY`, `GEMINI_API_KEY`, `TEST_RECIPIENT_EMAIL` (seeded once per run, used by the workflow's end-to-end delivery check), and SMTP: `P5_FROM_ADDRESS`, `P5_SMTP_HOST`, `P5_SMTP_PORT`, `P5_SMTP_SECURE`, `P5_SMTP_USER`, `P5_SMTP_PASS`
- **Optional:** `RECIPIENT_EMAILS` = comma-separated emails to seed (in addition to recipients you add in the UI).
