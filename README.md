# Product Pulse (INDmoney App Review)

Weekly one-pager from Google Play reviews, sent by email to a configurable list. Pipeline: ingest → clean → analyze → report → email. UI for recipients and delivery status.

- **Streamlit (all-in-one)**: Run and deploy the full pipeline in one app. `pip install -r requirements.txt && streamlit run streamlit_app.py`. Manage recipients, click **Run weekly pipeline (P1→P5)** in the sidebar, view reports and delivery. See [STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md).
- **Node (phases 1–6)**: `phase-1-ingest` through `phase-6-orchestrator`. Run Phase 6: `cd phase-6-orchestrator && npm install && npm run dev`; open http://localhost:4006/.

## Quick start (Streamlit, recommended)

1. Create `.env` at repo root (or set env) with `GROQ_API_KEY`, `GEMINI_API_KEY`, and SMTP vars (`P5_FROM_ADDRESS`, `P5_SMTP_*`).
2. `pip install -r requirements.txt && streamlit run streamlit_app.py`.
3. Open http://localhost:8501/. Add recipients, then click **Run weekly pipeline (P1→P5)** in the sidebar.

## Quick start (Node)

1. Create `.env` at repo root with API keys and SMTP (see each `phase-*/README.md`).
2. `cd phase-6-orchestrator && npm install && npm run dev`.
3. Open http://localhost:4006/ to manage recipients and view delivery. Pipeline runs on cron or via GitHub Actions.

## Deploy on Streamlit

Deploy this repo on [Streamlit Community Cloud](https://share.streamlit.io); main file `streamlit_app.py`. Set secrets: `GROQ_API_KEY`, `GEMINI_API_KEY`, and SMTP (`P5_*`) so the built-in pipeline can run. See [STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md).

## Automatic weekly email (Monday 10:00 AM IST)

The one-pager is sent automatically every **Monday at 10:00 AM IST** to recipients you manage in the Streamlit UI. To enable this:

1. **Deploy Phase 6** (Node) so it has a public URL (e.g. Railway, Render).
2. **Use Streamlit as the UI** and connect it to Phase 6: deploy the Streamlit app, set secret `P6_API_URL` to your Phase 6 URL, and in the app sidebar check **Use external Phase 6 API**. Add and edit recipients in Streamlit; they are stored in Phase 6’s DB.
3. **Set the GitHub Actions secret**: in the repo go to **Settings → Secrets and variables → Actions** and add `PIPELINE_TRIGGER_URL` = `https://your-phase6-host/api/pipeline/run` (your real Phase 6 base URL + `/api/pipeline/run`).

The workflow (`.github/workflows/weekly-pipeline.yml`) runs on schedule and calls that URL; Phase 6 runs the full pipeline and sends the one-pager to all active recipients.
