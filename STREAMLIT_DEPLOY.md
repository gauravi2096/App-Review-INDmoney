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

## Option B: Streamlit as UI only (connect to Phase 6 API)

If you prefer to run the pipeline on a Node server (e.g. Phase 6 on Railway) and only use Streamlit as the dashboard:

1. Deploy Phase 6 somewhere and get its public URL.
2. Deploy the Streamlit app as above; in **Secrets** set only:
   ```toml
   P6_API_URL = "https://your-phase6-url.up.railway.app"
   ```
3. In the Streamlit sidebar, check **Use external Phase 6 API**. The app will then use the API for recipients, reports, and delivery (no built-in pipeline run).

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
