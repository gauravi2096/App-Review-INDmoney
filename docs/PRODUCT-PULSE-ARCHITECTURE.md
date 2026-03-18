# Product Pulse: Phase-Wise System Architecture (Refined)

**Purpose:** Convert Google Play Store reviews for INDmoney into a weekly one-page product pulse, sent automatically every week to a configurable list of recipients, with optional manual trigger and full visibility of reports and delivery status.

**Audience:** Product/Growth (what to fix), Support (what users say), Leadership (weekly health pulse).

---

## 1. Phase Overview

| Phase | Name | Responsibility |
|-------|------|----------------|
| **P1** | Ingest | Fetch reviews via google-play-scraper (INDmoney app); filter to last 8–12 weeks; validate; persist to storage. |
| **P2** | Clean & Structure | Normalize and anonymize; enforce schema; persist cleaned dataset. |
| **P3** | LLM Analysis | Call LLM (Groq only); derive themes (each with **count of reviews mapped to it**), quotes (each **selected user quote includes its rating**), actions; persist results. |
| **P4** | Report Generation | Compose one-page note with Gemini (≤250 words); include review count per theme and rating per quote; persist report artifact and metadata. Retry/backoff for Gemini quota limits. |
| **P5** | Email Send | Send weekly note to recipient list via email service; record delivery status. |
| **P6** | UI & Scheduling | Recipient management; view reports; delivery status; manual trigger; weekly scheduler. |

---

## 2. Dependencies

The Product Pulse system depends on the following external services, libraries, and infrastructure. Failure or unavailability of any dependency affects the phase(s) that use it.

| Dependency | Type | Used in | Purpose |
|------------|------|---------|---------|
| **Google Play Store** | External service | P1 | Public source of INDmoney app reviews. Read via google-play-scraper; no auth. Subject to Play Store availability and rate limits. |
| **google-play-scraper** | Library / package | P1 | Fetches app reviews from the public Play Store (reviews API, pagination, throttling). Requires INDmoney app ID; optional lang/country. |
| **Database** | Infrastructure | P1–P6 | Persists raw reviews, cleaned reviews, analysis, report metadata (and report body when using a hosted DB), delivery status, recipient list. SQLite for local runs; **PostgreSQL** when `DATABASE_URL` is set (e.g. Supabase, Neon). For **Supabase** on Streamlit Cloud or GitHub Actions, use the **connection pooler** URI (port 6543), not the direct connection (5432). |
| **Object storage / file system** | Infrastructure | P4, P5, UI | When not using a hosted DB: report HTML is written to the file system (`data/reports/`). When `DATABASE_URL` is set, report body is stored in **report_metadata.body_html** so no separate blob storage is needed. |
| **Groq API** | External service | P3 | LLM for theme extraction (with count of reviews mapped per theme), quotes (each with its rating), and action ideas. Requires API key. |
| **Gemini API** | External service | P4 | LLM for composing the weekly one-pager from analysis. Retry with exponential backoff on 429 (quota limits). Requires API key. |
| **Email provider** (e.g. SendGrid, AWS SES, SMTP) | External service | P5 | Sends the weekly one-pager to the recipient list. Requires credentials and sender identity. |
| **Scheduler** (e.g. cron, cloud scheduler) | Infrastructure | P6 | Triggers the full pipeline weekly at a fixed time. Depends on host or cloud offering. |

**Optional / config:** INDmoney app ID, lang, country, date window (8–12 weeks), sender address, reply-to.

---

## 3. Cross-Cutting Components

### 3.1 Storage Layer

The system uses a single logical storage layer with two parts:

- **Database (relational):** Persistent store (SQLite for local runs, or **PostgreSQL** when `DATABASE_URL` is set for a shared hosted DB used by Streamlit and the scheduled pipeline):
  - **Raw reviews (post-ingest):** One row per review with rating, title, text, date, run_id, ingested_at. Filled by P1. Retained for audit and re-runs.
  - **Cleaned reviews:** Same schema but normalized and anonymized; linked to run_id. Used as input for LLM and for debugging.
  - **Recipient list:** Email, display_name, active, created_at, updated_at. Used by the email service and editable via UI.
  - **Report metadata:** One record per weekly report: report_id, week_start_date, report_status, word_count, generated_at, storage_artifact_path, and optionally **body_html** (when using a hosted DB, the report HTML is stored here so P5 can send without file storage).
  - **Delivery status:** Per (report_id, recipient_email): status, sent_at, error_message. Used by UI for delivery summary.

- **Object/Blob storage (or file system):** When not using a hosted DB, the report HTML is written to the file system (e.g. `data/reports/`). When `DATABASE_URL` is set, report HTML is stored in **report_metadata.body_html** so the Actions runner and Streamlit share the same data without shared file storage.

**Data flow and storage:** P1 fetches reviews via google-play-scraper and writes raw reviews to the database. P2 reads raw reviews, writes cleaned reviews to the database. P3 reads cleaned reviews, writes analysis to the database. P4 reads analysis, composes the report with Gemini, writes the HTML to the file system and (when `DATABASE_URL` is set) to **report_metadata.body_html**, and writes report metadata to the database. P5 reads report metadata and (when available) body from the database, else from the file system; reads recipients from the database; writes delivery status to the database. The **Streamlit** UI and the **GitHub Actions** scheduler both use the same database when `DATABASE_URL` is set, so recipients added in the UI are used by the scheduled run.

### 3.2 Email Service

- **Role:** Send transactional emails containing the weekly one-pager to a list of recipients. No login-based scraping; all outbound only.
- **Integration:** Use a dedicated email-sending provider (e.g. SMTP relay, SendGrid, AWS SES, or similar). The system holds configuration (API key or SMTP credentials, sender address, optional reply-to) in configuration or secrets; the email service component uses this to send.
- **Behaviour:** For each weekly run, the service receives: report subject, report body (HTML or plain text), and the list of recipient email addresses from the database. It sends one email per recipient, then returns or records per-recipient outcome (Sent / Not Sent / Error). The pipeline records these outcomes in the delivery status table so the UI can show "Sent," "Not Sent," or "Error" with optional error details.
- **Recipient list:** Maintained in the database and managed via UI (add / edit / delete). Only active recipients are included when P5 builds the send list. Edit includes changing email or display name; delete means soft-delete or marking inactive so they are no longer sent to.

### 3.3 Scheduling Mechanism (Weekly Automatic Send)

- **Role:** Run the full pipeline (P1 through P5) once per week without user action.
- **Component:** The repo includes a **GitHub Actions workflow** (`.github/workflows/weekly-product-pulse.yml`) that runs every **Monday at 10:00 AM IST** (10:00 AM IST = 04:30 UTC; cron `30 4 * * 1`). The workflow runs the **Python pipeline on the Actions runner** (no external URL or Phase 6 deployment required). It **requires `DATABASE_URL`** (a shared hosted Postgres connection string in repo Secrets) so the same DB is used by the Streamlit app and the scheduled run; recipients added in the Streamlit UI are then used automatically when the pipeline runs. Optional: Phase 6 (Node) can be deployed separately and use in-process cron; the repo workflow does not call it.
- **Execution:** On schedule, the scheduler calls the pipeline with parameters: e.g. "fetch reviews for INDmoney (last 8–12 weeks)," "generate report and send to all active recipients." The pipeline runs P1→P2→P3→P4→P5 in sequence. P1 fetches fresh reviews from the Play Store via google-play-scraper each run; if the fetch returns no reviews in the window, the design defines behaviour (e.g. skip run and record "No data," or reuse last run’s data per policy).
- **Idempotency:** Each run produces one report per week (keyed by week or run_id). Delivery status is per (report, recipient). Re-runs can overwrite that week’s report and re-send, or be treated as "manual resend"; the architecture should state which.

---

## 4. How Reviews Are Obtained (google-play-scraper)

- **Constraint:** Public data only. The system uses **google-play-scraper** to fetch reviews from the public Google Play Store listing for the INDmoney app. No login or Play Console credentials are required; the library reads the same public review pages that users see on the web.
- **Mechanism:**
  - **Review Fetcher:** A dedicated component (e.g. "Review Fetcher" or "Play Review Client") uses the **google-play-scraper** library. It is configured with the **INDmoney app ID** (the Play Store package name, e.g. `com.indwealth.in` or the actual package ID), and optionally **language** and **country** (e.g. `en`, `in`) so reviews match the target market.
  - **Pagination:** The library returns reviews in pages. The fetcher repeatedly calls the scraper’s review method (with pagination token or next-page handling as the library supports) until it has retrieved enough reviews, or until it has gone back beyond the desired window. The fetcher respects the library’s built-in **throttling** to avoid rate limits and reduce the risk of blocks.
  - **Date window:** Reviews include a date field. After each page (or after the full fetch), the fetcher **filters** results to keep only reviews from the **last 8–12 weeks** (configurable). Older reviews are discarded before persistence.
- **Execution in P1:** When the pipeline runs (scheduler or manual trigger), the ingest job invokes the Review Fetcher. The fetcher uses google-play-scraper to pull reviews for the INDmoney app, paginates as needed, applies the 8–12 week date filter, validates required fields (rating, title, text, date), and writes valid records to the **raw reviews** table with a run identifier and ingested_at. No export file upload or drop path is involved; the source of truth for ingestion is the live Play Store (public) data.
- **Components:** Review Fetcher (wraps google-play-scraper), date filter (8–12 weeks), validator (schema and required fields), database writer. Configuration: app ID (INDmoney), lang, country, date window length.

---

## 5. Phase-Wise Execution and Components

### Phase 1: Ingest

- **How it executes:** An ingest job (triggered by scheduler or UI) runs first. It invokes the **Review Fetcher**, which uses **google-play-scraper** to fetch reviews for the INDmoney app. The fetcher paginates through the scraper’s review API until it has enough data or reaches the end of available pages, applies the configurable **date filter** (last 8–12 weeks), and validates required fields (rating, title, text, date). Valid rows are written to the **raw reviews** table in the database with run_id and ingested_at.
- **Components:** Review Fetcher (google-play-scraper client with pagination and throttling), date filter, validator, database writer. Configuration: INDmoney app ID, lang, country, date window (e.g. 8 vs 12 weeks).
- **Output and handoff:** Raw reviews for the chosen window are in the database. Downstream (P2) reads from the same database (e.g. "latest ingestion" or "ingestion for run_id").

### Phase 2: Clean & Structure

- **How it executes:** A cleaning job reads the raw reviews produced by P1 (for the current run or latest ingestion). It normalizes text (encoding, trim, collapse whitespace), normalizes dates to a single format/timezone, enforces schema (drop or fix invalid fields), and anonymizes (strip usernames, emails, IDs). Resulting records are written to the **cleaned reviews** table (or overwrite a staging set for this run).
- **Components:** Reader from DB, text normalizer, date normalizer, anonymizer, schema enforcer, database writer.
- **Output and handoff:** Cleaned, anonymized review set in the database. P3 reads this set (e.g. by run_id or week) and passes it to the LLM layer.

### Phase 3: LLM Analysis

- **How it executes:** An LLM orchestration component loads the cleaned review set from the database, optionally truncates or batches by token limit, then calls **Groq** (no Gemini in this phase).
- **LLM output shape:** Each theme includes the **count of reviews mapped to it** (how many reviews in the batch belong to that theme). Each selected user quote **includes its rating** (the 1–5 star rating of the review the quote came from).
- **LLM call:** One or more requests (e.g. a single structured prompt) that return 3–5 themes (label, description, count of reviews mapped to that theme), 3 quotes (quote text plus rating from the source review), 3 action ideas. Responses are parsed and validated (max 5 themes, no PII in quotes). Results are written to the **analysis** table.
- **Components:** DB reader, token estimator, LLM client (Groq only), prompt builder, response parser, DB writer.
- **Output and handoff:** Themes (with count of reviews mapped to each), quotes (each with its rating), action ideas stored in the database. After the run completes, the latest analysis is **automatically exported** to **phase3-analysis.json** in the Phase 3 directory for easy viewing; no separate export command is required. P4 reads analysis from the database and composes the one-pager using Gemini.

### Phase 4: Report Generation

- **How it executes:** A report generator reads the analysis from the database for the current run. It uses **Gemini** to compose the weekly one-page note: top 3 themes (with **number of reviews per theme**), 3 user quotes (with **rating for each quote**), 3 action ideas, in a scannable format (headings, bullets). It enforces ≤250 words and ensures no PII. The Gemini client uses **retry with exponential backoff** on 429 (quota limits). The note is rendered to HTML. The HTML is written to the file system (e.g. `data/reports/<run_id>.html`). When **`DATABASE_URL`** is set (shared hosted DB), the HTML is also stored in **report_metadata.body_html** so the Actions runner and Streamlit can use it without shared file storage. A **report metadata** record is written: report_id, week_start_date, status, word_count, generated_at, storage_artifact_path, and optionally body_html.
- **Components:** DB reader (analysis), Gemini composer, word counter, renderer, file/DB writer (body + metadata).
- **Output and handoff:** Report body in file system and (when DATABASE_URL set) in report_metadata.body_html; metadata in database. P5 reads the body from the DB when body_html is present, else from the file system; UI reads metadata and body to list and view reports.

### Phase 5: Email Send

- **How it executes:** The email send component runs after P4. It loads the report metadata from the database. If **report_metadata.body_html** is present (hosted DB), it uses that as the report body; otherwise it reads the report HTML from the file system. It loads the active recipient list from the database. It builds the email (subject e.g. "INDmoney Product Pulse – [week date]," body = report content). For each recipient, it calls the **email service** to send. The email service uses the configured provider (SMTP/SendGrid/SES) and returns per-recipient status (Sent / Not Sent / Error). The pipeline writes one **delivery status** row per (report_id, recipient_email) with status, sent_at, and optional error_message.
- **Components:** DB reader (report metadata, recipients; report body when stored in body_html), file reader (body when not in DB), email builder, email service client, DB writer (delivery status).
- **Output and handoff:** Emails sent to all active recipients; delivery status persisted. UI reads delivery status to show "Sent," "Not Sent," "Error" and optional error details.

### Phase 6: UI and Trigger

- **How it executes:** The **primary UI** is the **Streamlit app** (`streamlit_app.py`): it runs the full pipeline (P1–P5) in-process, manages recipients, and shows reports and delivery status. When `DATABASE_URL` is set (e.g. Supabase pooler URI), the same database is used by Streamlit and the GitHub Actions workflow, so recipients added in the UI are used by the scheduled Monday run. Optionally, Streamlit can be configured to use an **external Phase 6 API** (Node backend) instead of the built-in pipeline; in that case the Node server holds the DB and pipeline.
- **UI capabilities (Streamlit):**
  - **Recipients:** List, add (email, optional display name), edit, delete (soft-delete). Data in shared DB when DATABASE_URL is set.
  - **Weekly email delivery:** Table of reports with per-report counts: sent, failed, pending (from report_metadata and delivery_status).
  - **Manual trigger:** "Run weekly pipeline (P1→P5)" in the sidebar runs ingest → clean → analyze → report → email in the app.
- **Scheduler:** The **GitHub Actions** workflow (`.github/workflows/weekly-product-pulse.yml`) runs the **Python pipeline on the runner** every Monday at 10:00 AM IST. It requires `DATABASE_URL` in repo Secrets; no Phase 6 deployment is required. The workflow does not call any external URL.
- **Components:** Streamlit frontend (recipients, reports/delivery table, pipeline trigger), Python pipeline (P1–P5), optional Phase 6 Node API for alternative deployment.

---

## 6. System Flow (Detailed)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        PRODUCT PULSE – EXECUTION FLOW                              │
└──────────────────────────────────────────────────────────────────────────────────┘

  [Trigger: Scheduler OR UI "Generate report"]
                    │
                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  P1: Ingest                                                                   │
  │  • Call google-play-scraper for INDmoney app (paginate, throttle)             │
  │  • Filter to last 8–12 weeks, validate (rating, title, text, date)            │
  │  • Write raw reviews ──────────────────────────────────────> Database        │
  └─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  P2: Clean & Structure                                                        │
  │  • Read raw reviews from DB                                                   │
  │  • Normalize, anonymize, enforce schema                                       │
  │  • Write cleaned reviews ──────────────────────────────────> Database      │
  └─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  P3: LLM Analysis (Groq only)                                                 │
  │  • Read cleaned reviews from DB                                               │
  │  • Batch by token limit; call Groq (themes + review count, quotes + rating)    │
  │  • Validate; no PII; write analysis ─────────────────────────> Database      │
  │  • Auto-export latest analysis ──────────────────────────────> phase3-analysis.json │
  └─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  P4: Report Generation (Gemini only; retry on 429)                            │
  │  • Read analysis from DB                                                      │
  │  • Compose one-pager with Gemini (reviews per theme, rating per quote; ≤250w)  │
  │  • Render HTML; write body ──────> File system + DB (body_html if DATABASE_URL)│
  │  • Write report metadata ───────────────────────────────────> Database      │
  └─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  P5: Email Send                                                               │
  │  • Read report metadata (+ body_html from DB if set; else file system)        │
  │  • Read active recipients from DB                                             │
  │  • For each recipient: call Email Service → send                              │
  │  • Write delivery status (Sent / Not Sent / Error) ───────────> Database      │
  └─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
  [Done. UI can show new report, view one-pager, and delivery status.]
```

---

## 7. Data Flow Between Phases and Storage

| Phase | Reads from | Writes to |
|-------|------------|-----------|
| P1 | Google Play (via google-play-scraper: INDmoney app, paginated) | Database: raw reviews (after date filter 8–12 weeks). |
| P2 | Database: raw reviews | Database: cleaned reviews |
| P3 | Database: cleaned reviews | Database: analysis (themes, quotes, actions). Auto-export to phase3-analysis.json. |
| P4 | Database: analysis | File system: report HTML. Database: report metadata (and body_html when DATABASE_URL set). |
| P5 | Database: report metadata, recipients; report body from body_html or file. | Database: delivery status. External: email via Email Service. |
| Streamlit UI | Database: recipients, report metadata, delivery status (and body when in body_html). | Database: recipients (add/edit/delete). In-app: trigger pipeline (P1–P5). |
| GitHub Actions scheduler | — | Runs Python pipeline on runner; requires DATABASE_URL; uses same DB as Streamlit. |

---

## 8. UI Interactions (Summary)

| Action | What happens |
|--------|----------------|
| Add recipient | Streamlit (or Phase 6 API) writes to recipient list in DB (active). With DATABASE_URL, same list is used by the scheduled pipeline. |
| Edit / Delete recipient | Streamlit or API updates or soft-deletes recipient in DB. |
| View weekly delivery | Streamlit reads report_metadata and delivery_status from DB; shows per-report sent/failed/pending counts. |
| Trigger report manually | In Streamlit: "Run weekly pipeline (P1→P5)" runs the Python pipeline in-process. With Phase 6 API: UI calls trigger endpoint; backend runs pipeline. |

---

## 9. Key Constraints (Reflected in Design)

- **Data source:** Public Play Store data only. Reviews are fetched via **google-play-scraper** for the INDmoney app (no login; pagination and throttling applied). Date window 8–12 weeks applied after fetch.
- **Storage:** Raw and cleaned reviews, analysis, report metadata, delivery status, and recipient list in database. Report body: file system when using SQLite; when `DATABASE_URL` is set, also (or only) in **report_metadata.body_html** so Streamlit and the Actions runner share the same data.
- **LLM:** Phase 3 uses Groq only (themes, quotes with rating, action ideas). Phase 4 uses Gemini only for report composition; quota limits handled with retry/backoff.
- **Report:** One-pager ≤250 words; stored in file system and, when using a hosted DB, in report_metadata.body_html.
- **Email:** Sent weekly via Email Service to active recipients from DB; delivery status stored per (report, recipient).
- **Scheduling:** Weekly automatic run every Monday 10:00 AM IST via GitHub Actions; workflow runs the Python pipeline on the runner and requires `DATABASE_URL` (shared Postgres). For Supabase, use the connection pooler URI (port 6543) for Streamlit Cloud and Actions.
- **Privacy:** No usernames, emails, or IDs in report or LLM outputs; anonymization in P2 and checks in P3/P4.

---

## 10. Out of Scope (Architecture Boundaries)

- No implementation code (languages, frameworks, or infra choices).
- Authentication/authorization for UI and API to be defined separately.
- Retention and archival policy for old reports and raw data to be defined separately.
- Retry and failure handling strategy (e.g. partial send failure) to be defined in operational runbook.

---

*Document: Refined phase-wise architecture with storage, email service, scheduling, UI behaviour, and execution flow. No implementation code.*
