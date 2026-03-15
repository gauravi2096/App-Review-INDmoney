# Deploy Product Pulse on Streamlit Cloud

The Streamlit app runs **all phases (P1–P6)** in one deployment: it uses a built-in Python pipeline (ingest, clean, analyze, report, email), manages recipients, and shows reports and delivery status. No separate Node server is required.

## Option A: Full pipeline in Streamlit (recommended)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **New app**.
3. **Repository**: `gauravi2096/App-Review-INDmoney` (or your fork).
4. **Branch**: `main`.
5. **Main file path**: `streamlit_app.py`.
6. **Advanced settings** → **Secrets**: add your API keys and SMTP (so the pipeline can run in the cloud):

   ```toml
   GROQ_API_KEY = "your-groq-api-key"
   GEMINI_API_KEY = "your-gemini-api-key"
   P5_FROM_ADDRESS = "your-email@gmail.com"
   P5_SMTP_HOST = "smtp.gmail.com"
   P5_SMTP_PORT = "465"
   P5_SMTP_SECURE = "true"
   P5_SMTP_USER = "your-email@gmail.com"
   P5_SMTP_PASS = "your-app-password"
   ```

7. Click **Deploy**. Use the sidebar **Run weekly pipeline (P1→P5)** to trigger the full pipeline. Recipients and reports use the app’s local SQLite (ephemeral on Streamlit Cloud unless you add persistent storage).

## Option B: Streamlit as UI + automatic Monday 10 AM IST email (Phase 6 API)

Use Streamlit to manage recipients and have the one-pager **sent automatically every Monday at 10:00 AM IST** to those recipients via GitHub Actions:

1. **Deploy Phase 6** (Node) so it has a public URL (e.g. Railway, Render). Ensure it has the same DB and env (API keys, SMTP) so it can run the pipeline.
2. **Deploy the Streamlit app**; in **Secrets** set:
   ```toml
   P6_API_URL = "https://your-phase6-url.up.railway.app"
   ```
3. In the Streamlit sidebar, check **Use external Phase 6 API**. Add and edit recipients in Streamlit; they are stored in Phase 6’s DB.
4. **Enable the weekly run**: in the **GitHub repo** go to **Settings → Secrets and variables → Actions** and add:
   - `PIPELINE_TRIGGER_URL` = `https://your-phase6-url.up.railway.app/api/pipeline/run`

The workflow runs every Monday 10:00 AM IST and triggers Phase 6; Phase 6 runs the pipeline and sends the one-pager to all active recipients (the same list you manage in Streamlit).

## Run locally

```bash
# From repo root
pip install -r requirements.txt
# Set env vars (or use .env): GROQ_API_KEY, GEMINI_API_KEY, P5_* for SMTP
streamlit run streamlit_app.py
```

- By default the app uses the **built-in pipeline** and local SQLite (`data/product_pulse.db`). Click **Run weekly pipeline (P1→P5)** in the sidebar to run ingest → clean → analyze → report → email.
- To use the Node Phase 6 API instead, check **Use external Phase 6 API** in the sidebar and set the API URL.

## Summary

| Mode        | What runs |
|-------------|-----------|
| **Built-in (default)** | All phases (P1–P5) run inside the Streamlit app. Recipients and reports are stored in local SQLite. Trigger with **Run weekly pipeline** in the sidebar. |
| **External API** | Streamlit is UI only; it talks to your deployed Phase 6 API. Pipeline runs on the Node server (e.g. via GitHub Actions or cron). |
