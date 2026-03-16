# Deploy Product Pulse on Streamlit Cloud

The Streamlit app runs **all phases (P1–P5)** in one deployment: built-in Python pipeline (ingest, clean, analyze, report, email), recipient management, and reports/delivery view. No separate Node server is required.

## Option A: Full pipeline + shared DB (recommended for Monday email)

Use a **shared hosted Postgres** so recipients you add in the Streamlit UI are used when the **Monday 10:00 AM IST** GitHub Actions pipeline runs.

1. Create a Postgres database (e.g. [Supabase](https://supabase.com), [Neon](https://neon.tech), [Railway](https://railway.app)) and copy its connection string. **Supabase:** use the **pooler** URI (port **6543**), not direct (5432): Project Settings → Database → Connection string → **Connection pooling** (Transaction mode). Streamlit Cloud cannot use the direct connection.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. **New app** → **Repository**: your repo (or fork), **Branch**: `main`, **Main file path**: `streamlit_app.py`.
4. **Advanced settings** → **Secrets**:

   ```toml
   DATABASE_URL = "postgresql://user:pass@host:6543/postgres"
   GROQ_API_KEY = "your-groq-api-key"
   GEMINI_API_KEY = "your-gemini-api-key"
   P5_FROM_ADDRESS = "your-email@gmail.com"
   P5_SMTP_HOST = "smtp.gmail.com"
   P5_SMTP_PORT = "465"
   P5_SMTP_SECURE = "true"
   P5_SMTP_USER = "your-email@gmail.com"
   P5_SMTP_PASS = "your-app-password"
   ```

5. In the **GitHub repo**: **Settings → Secrets and variables → Actions** → add the same **`DATABASE_URL`** (and `GROQ_API_KEY`, `GEMINI_API_KEY`, `P5_*` SMTP). The Monday workflow runs the pipeline on the runner and uses this DB; recipients added in Streamlit are used automatically.
6. Click **Deploy**. Add recipients in the app; run **Run weekly pipeline (P1→P5)** manually or wait for the Monday run.

## Option B: Streamlit only (local SQLite)

If you do not need the scheduled Monday run to share recipients with Streamlit:

1. Deploy the Streamlit app as above but **omit** `DATABASE_URL` from Secrets.
2. Recipients and reports use the app’s **ephemeral** SQLite (data is lost when the app restarts). Use **Run weekly pipeline** in the sidebar to run the pipeline on demand.

## Option C: Streamlit as UI + Phase 6 API

Use Streamlit as the UI and a **deployed Phase 6** (Node) as the backend: set **Secrets** → `P6_API_URL` to your Phase 6 URL, then check **Use external Phase 6 API** in the sidebar. Recipients and pipeline run on the Phase 6 server. The Monday workflow in this repo runs the **Python pipeline on the runner** with `DATABASE_URL`; it does not call Phase 6. To have Monday email via Phase 6, run the pipeline on your Phase 6 host (e.g. cron) instead of using the repo workflow.

## Run locally

```bash
pip install -r requirements.txt
# Set env (or .env): GROQ_API_KEY, GEMINI_API_KEY, P5_* for SMTP; optional DATABASE_URL for shared DB
streamlit run streamlit_app.py
```

- **Without `DATABASE_URL`**: built-in pipeline and local SQLite (`data/product_pulse.db`).
- **With `DATABASE_URL`**: same app and pipeline but data is in the shared Postgres (same as Streamlit Cloud and the Monday run if you set the secret there).

## Summary

| Mode        | What runs |
|-------------|-----------|
| **Built-in + DATABASE_URL** | Pipeline and UI use shared Postgres. Recipients added in Streamlit are used by the Monday GitHub Actions run. |
| **Built-in (no DATABASE_URL)** | Pipeline and UI use local SQLite. Monday run requires DATABASE_URL in Actions and uses its own DB/recipients. |
| **External Phase 6 API** | Streamlit is UI only; data and pipeline run on your Phase 6 server. |
