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

## Weekly run (Node + GitHub Actions)

A GitHub Actions workflow runs every **Monday 10:00 AM IST** and triggers the pipeline. Set the secret `PIPELINE_TRIGGER_URL` to your deployed Phase 6 `/api/pipeline/run` URL (when using the Node stack).
