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
| **Database** | Infrastructure | P1–P6 | Persists raw reviews, cleaned reviews, analysis, report metadata, delivery status, recipient list. Required for pipeline and UI. |
| **Object (blob) storage** | Infrastructure | P4, P5, UI | Stores generated report artifact per week. P5 and UI read report body from here. |
| **Groq API** | External service | P3 | LLM for theme extraction (with count of reviews mapped per theme), quotes (each with its rating), and action ideas. Requires API key. |
| **Gemini API** | External service | P4 | LLM for composing the weekly one-pager from analysis. Retry with exponential backoff on 429 (quota limits). Requires API key. |
| **Email provider** (e.g. SendGrid, AWS SES, SMTP) | External service | P5 | Sends the weekly one-pager to the recipient list. Requires credentials and sender identity. |
| **Scheduler** (e.g. cron, cloud scheduler) | Infrastructure | P6 | Triggers the full pipeline weekly at a fixed time. Depends on host or cloud offering. |

**Optional / config:** INDmoney app ID, lang, country, date window (8–12 weeks), sender address, reply-to.

---

## 3. Cross-Cutting Components

### 3.1 Storage Layer

The system uses a single logical storage layer with two parts:

- **Database (relational or document):** Persistent store for:
  - **Raw reviews (post-ingest):** One row/document per review with rating, title, text, date, run_id (or fetch_run_id), ingested_at. Filled by P1 from google-play-scraper output. Retained for audit and re-runs. Optional retention policy (e.g. keep last N runs).
  - **Cleaned reviews:** Same schema but normalized and anonymized; linked to an ingestion run or week. Used as input for LLM and for debugging.
  - **Recipient list:** Email address, display name, active flag, created_at, updated_at. Used by the email service and editable via UI.
  - **Report metadata:** One record per weekly report: report_id, week_start_date, report_status (draft / generated / failed), word_count, generated_at, storage_artifact_path (or URL). Used by UI to list and open reports and by P5 to send.
  - **Delivery status:** One record per (report_id, recipient_email): status (Sent / Not Sent / Error), sent_at, error_message (if Error). Used by UI to show per-recipient delivery status.

- **Object/Blob storage (or file system):** For large or binary artifacts:
  - **Generated report artifact:** The final one-pager (e.g. HTML or markdown) for each week. Stored by report_id or week identifier. Report metadata in the database holds the path or URL so P5 and UI can read the body for email and for "view one-pager."

**Data flow and storage:** P1 fetches reviews via google-play-scraper and writes raw reviews to the database. P2 reads raw reviews, writes cleaned reviews to the database. P3 reads cleaned reviews from the database, writes theme/quote/action results to the database (or a dedicated analysis table). P4 reads analysis from the database, writes the note to object storage and report metadata to the database. P5 reads report body from object storage and recipient list from the database, writes delivery status to the database. UI and scheduler read/write recipients, report metadata, and delivery status.

### 3.2 Email Service

- **Role:** Send transactional emails containing the weekly one-pager to a list of recipients. No login-based scraping; all outbound only.
- **Integration:** Use a dedicated email-sending provider (e.g. SMTP relay, SendGrid, AWS SES, or similar). The system holds configuration (API key or SMTP credentials, sender address, optional reply-to) in configuration or secrets; the email service component uses this to send.
- **Behaviour:** For each weekly run, the service receives: report subject, report body (HTML or plain text), and the list of recipient email addresses from the database. It sends one email per recipient, then returns or records per-recipient outcome (Sent / Not Sent / Error). The pipeline records these outcomes in the delivery status table so the UI can show "Sent," "Not Sent," or "Error" with optional error details.
- **Recipient list:** Maintained in the database and managed via UI (add / edit / delete). Only active recipients are included when P5 builds the send list. Edit includes changing email or display name; delete means soft-delete or marking inactive so they are no longer sent to.

### 3.3 Scheduling Mechanism (Weekly Automatic Send)

- **Role:** Run the full pipeline (P1 through P5) once per week without user action.
- **Component:** A scheduler (e.g. cron job, cloud scheduler, or in-process scheduler) that runs at a fixed weekday and time (e.g. every Monday 09:00). The repo includes a **GitHub Actions workflow** (`.github/workflows/weekly-product-pulse.yml`) that runs every **Monday at 10:00 AM IST** and triggers the pipeline by calling the Phase 6 `POST /api/pipeline/run` endpoint on a deployed server; recipients managed in the dashboard receive the one-pager. Alternatively, Phase 6 can use in-process node-cron. In all cases the trigger invokes the same pipeline entry point; only the trigger differs (time-based vs user click).
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

- **How it executes:** A report generator reads the analysis from the database for the current run. It uses **Gemini** to compose the weekly one-page note: top 3 themes (with **number of reviews per theme**), 3 user quotes (with **rating for each quote**), 3 action ideas, in a scannable format (headings, bullets). It enforces ≤250 words and ensures no PII. The Gemini client uses **retry with exponential backoff** on 429 (quota limits). The note is rendered to a final format (e.g. HTML for email and viewing). The artifact is written to **object storage** (path/key by report_id or week). A **report metadata** record is written to the database: report_id, week_start_date, status (generated), word_count, generated_at, storage_artifact_path (or URL).
- **Components:** DB reader (analysis), Gemini composer, word counter, renderer, object storage writer, DB writer (metadata).
- **Output and handoff:** Report body in object storage; metadata in database. P5 reads the body from storage and the recipient list from the database; UI reads metadata and body to "view one-pager" and show in lists.

### Phase 5: Email Send

- **How it executes:** The email send component runs after P4. It loads the report metadata and fetches the report body from object storage. It loads the active recipient list from the database. It builds the email (subject e.g. "INDmoney Product Pulse – [week date]," body = report content). For each recipient, it calls the **email service** to send. The email service uses the configured provider (SMTP/SendGrid/SES) and returns per-recipient status (Sent / Not Sent / Error). The pipeline writes one **delivery status** row per (report_id, recipient_email) with status, sent_at, and optional error_message.
- **Components:** DB reader (report metadata, recipients), object storage reader (body), email builder, email service client, DB writer (delivery status).
- **Output and handoff:** Emails sent to all active recipients; delivery status persisted. UI reads delivery status to show "Sent," "Not Sent," "Error" and optional error details.

### Phase 6: UI and Trigger

- **How it executes:** The UI is a separate surface (web app or internal tool) that talks to a backend API. The backend reads/writes the database and, for "view one-pager," reads from object storage (or a signed URL). The same backend exposes the pipeline entry point used by the scheduler and by the manual "Generate weekly report" button.
- **UI capabilities:**
  - **Recipients:** List recipients; add (email, optional name); edit (email, name); delete (soft-delete or remove). Actions call API that updates the **recipient list** table.
  - **View weekly one-pager:** List of past reports (from report metadata: week, date, status). User selects a report; UI fetches and displays the report body (from storage or API that reads storage).
  - **Email delivery status:** For a selected report, show per-recipient status: Sent (with sent_at), Not Sent, or Error (with error_message). Data comes from **delivery status** table.
  - **Manual trigger:** "Generate weekly report" button calls the API that runs the full pipeline (P1→P5). UI shows running state, then success or failure; on success, the new report appears in the list and delivery status is available.
- **Scheduler:** Runs the same pipeline entry point on a fixed weekly schedule; no UI action required. Optionally the UI can show "last run" time and next scheduled run if the backend exposes this.
- **Components:** Frontend (pages for recipients, reports list, report detail, delivery status, trigger button), backend API (CRUD recipients, list reports, get report body, get delivery status, trigger pipeline), pipeline orchestrator (invoked by API and by scheduler).

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
  │  • Render HTML; write body ─────────────────────────────────> Object storage │
  │  • Write report metadata ───────────────────────────────────> Database      │
  └─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  P5: Email Send                                                               │
  │  • Read report metadata + body (from DB + object storage)                     │
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
| P4 | Database: analysis | Object storage: report body. Database: report metadata. |
| P5 | Database: report metadata, recipients. Object storage: report body. | Database: delivery status. External: email via Email Service. |
| UI | Database: recipients, report metadata, delivery status. Object storage (or API): report body. | Database: recipients (add/edit/delete). API: trigger pipeline. |
| Scheduler | — | Invokes same pipeline entry point as UI trigger. |

---

## 8. UI Interactions (Summary)

| Action | What happens |
|--------|----------------|
| Add recipient | UI sends new email (and optional name) to API; API inserts into recipient list (active). |
| Edit recipient | UI sends updated email/name and id; API updates recipient row. |
| Delete recipient | UI sends id; API soft-deletes or marks inactive so P5 no longer sends to them. |
| View weekly one-pager | UI requests report by id/week; API loads report metadata, fetches body from storage, returns for display. |
| See delivery status | UI requests delivery status for a report; API returns list of (recipient, status: Sent / Not Sent / Error, sent_at, error_message). |
| Trigger report manually | UI calls "generate report" API; backend runs P1→P5; UI polls or gets callback for status; on success, new report and delivery rows exist. |

---

## 9. Key Constraints (Reflected in Design)

- **Data source:** Public Play Store data only. Reviews are fetched via **google-play-scraper** for the INDmoney app (no login; pagination and throttling applied). Date window 8–12 weeks applied after fetch.
- **Storage:** Raw and cleaned reviews, analysis, report metadata, delivery status, and recipient list in database; report artifact in object storage.
- **LLM:** Phase 3 uses Groq only (themes, quotes with rating, action ideas). Phase 4 uses Gemini only for report composition; quota limits handled with retry/backoff.
- **Report:** One-pager ≤250 words, stored in object storage and referenced by report metadata in DB.
- **Email:** Sent weekly via Email Service to active recipients from DB; delivery status stored per (report, recipient).
- **Scheduling:** Weekly automatic run via scheduler invoking the same pipeline as manual trigger.
- **Privacy:** No usernames, emails, or IDs in report or LLM outputs; anonymization in P2 and checks in P3/P4.

---

## 10. Out of Scope (Architecture Boundaries)

- No implementation code (languages, frameworks, or infra choices).
- Authentication/authorization for UI and API to be defined separately.
- Retention and archival policy for old reports and raw data to be defined separately.
- Retry and failure handling strategy (e.g. partial send failure) to be defined in operational runbook.

---

*Document: Refined phase-wise architecture with storage, email service, scheduling, UI behaviour, and execution flow. No implementation code.*
