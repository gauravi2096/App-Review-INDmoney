# Product Pulse (INDmoney App Review)

Weekly one-pager from Google Play reviews, sent by email to a configurable list. Pipeline: ingest → clean → analyze → report → email. UI for recipients and delivery status.

- **Streamlit (all-in-one)**: Run and deploy the full pipeline in one app. `pip install -r requirements.txt && streamlit run streamlit_app.py`. Manage recipients, click **Run weekly pipeline (P1→P5)** in the sidebar, view reports and delivery. See [STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md).
- **Node (phases 1–6)**: `phase-1-ingest` through `phase-6-orchestrator`. Run Phase 6: `cd phase-6-orchestrator && npm install && npm run dev`; open http://localhost:4006/.

## Quick start (Streamlit, recommended)

1. Create `.env` at repo root (or set env) with `GROQ_API_KEY`, `GEMINI_API_KEY`, and SMTP vars (`P5_FROM_ADDRESS`, `P5_SMTP_*`). Optional: `DATABASE_URL` for a shared Postgres DB (see above).
2. `pip install -r requirements.txt && streamlit run streamlit_app.py`.
3. Open http://localhost:8501/. Add recipients, then click **Run weekly pipeline (P1→P5)** in the sidebar.

## Quick start (Node)

1. Create `.env` at repo root with API keys and SMTP (see each `phase-*/README.md`).
2. `cd phase-6-orchestrator && npm install && npm run dev`.
3. Open http://localhost:4006/ to manage recipients and view delivery. Pipeline runs on cron or via GitHub Actions.

## Deploy on Streamlit

Deploy this repo on [Streamlit Community Cloud](https://share.streamlit.io); main file `streamlit_app.py`. Set secrets: `DATABASE_URL` (see below), `GROQ_API_KEY`, `GEMINI_API_KEY`, and SMTP (`P5_*`) so the built-in pipeline can run. See [STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md).

## Shared hosted database (recommended for pipeline + UI)

To have **recipients you add in the Streamlit UI** used by the **scheduled Monday pipeline**, use a single hosted Postgres database for both:

1. Create a Postgres database (e.g. [Supabase](https://supabase.com), [Neon](https://neon.tech), [Railway](https://railway.app)). **Supabase:** use the **connection pooler** URI (port **6543**), not the direct one (5432): Project Settings → Database → Connection string → **Connection pooling** (Transaction mode).
2. Set **`DATABASE_URL`** to that URI (e.g. `postgresql://user:pass@host:6543/postgres`) in:
   - **Streamlit Cloud**: App settings → Secrets.
   - **GitHub Actions**: Repo Settings → Secrets and variables → Actions → `DATABASE_URL`.

The pipeline and Streamlit app both connect to this DB when `DATABASE_URL` is set. No SQLite files or artifacts; report HTML is stored in the DB when using a hosted DB so the Monday run can send email without file storage.

## Automatic weekly email (Monday 10:00 AM IST)

The workflow **`.github/workflows/weekly-product-pulse.yml`** runs the **Python pipeline on the GitHub Actions runner** every Monday at 10:00 AM IST. It **requires** a shared DB so it uses the same recipients as the Streamlit UI.

**Secrets** (Settings → Secrets and variables → Actions):

- **Required:** `DATABASE_URL` (Postgres connection string), `GROQ_API_KEY`, `GEMINI_API_KEY`, and SMTP: `P5_FROM_ADDRESS`, `P5_SMTP_HOST`, `P5_SMTP_PORT`, `P5_SMTP_SECURE`, `P5_SMTP_USER`, `P5_SMTP_PASS`
- **Optional:** `RECIPIENT_EMAILS` = comma-separated emails to seed (in addition to recipients you add in the UI).
