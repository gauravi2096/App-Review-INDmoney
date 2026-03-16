"""
Product Pulse – Streamlit app.
Runs all phases (P1–P6) in one deployment: manage recipients, trigger pipeline, view reports and delivery.
Uses local SQLite and Python pipeline by default. Optional: connect to Phase 6 API instead (sidebar).
"""
import os
import streamlit as st

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="Product Pulse",
    page_icon="📊",
    layout="wide",
)

from pipeline import config as pipeline_config
from pipeline import db as pipeline_db
from pipeline.runner import run_weekly_pipeline

def get_db_path():
    return pipeline_config.DB_PATH

def use_external_api():
    if hasattr(st, "secrets") and st.secrets.get("P6_API_URL"):
        return True
    if os.environ.get("P6_API_URL"):
        return True
    return st.sidebar.checkbox("Use external Phase 6 API", value=False, help="If checked, connect to Phase 6 API for data and actions instead of local pipeline.")

def get_api_base():
    base = st.secrets.get("P6_API_URL") if hasattr(st, "secrets") else None
    if not base:
        base = os.environ.get("P6_API_URL", "").rstrip("/")
    if not base:
        base = st.sidebar.text_input("Phase 6 API URL", value="http://localhost:4006", key="api_url").rstrip("/")
    return base

def main():
    use_api = use_external_api()
    api_base = get_api_base() if use_api else None

    st.title("Product Pulse")
    st.caption("Manage recipients, run the weekly pipeline (ingest → clean → analyze → report → email), and view delivery status.")

    if use_api:
        import requests
        if not api_base:
            st.warning("Enter **Phase 6 API URL** in the sidebar.")
            return
        try:
            r = requests.get(f"{api_base}/api/health", timeout=10)
            r.raise_for_status()
        except Exception as e:
            st.error(f"Cannot reach Phase 6 API at `{api_base}`. Error: {e}")
            return
        # --- API mode: recipients ---
        st.subheader("Recipients")
        with st.expander("Add recipient", expanded=False):
            add_email = st.text_input("Email", key="add_email", placeholder="email@example.com")
            add_name = st.text_input("Display name (optional)", key="add_name")
            if st.button("Add recipient"):
                if not (add_email and add_email.strip()):
                    st.error("Email is required.")
                else:
                    try:
                        r = requests.post(f"{api_base}/api/recipients", json={"email": add_email.strip(), "display_name": (add_name.strip() or None) if add_name else None}, timeout=30)
                        if r.status_code in (200, 201):
                            st.success("Recipient added.")
                            st.rerun()
                        else:
                            st.error(r.json().get("error", f"HTTP {r.status_code}"))
                    except Exception as e:
                        st.error(str(e))
        try:
            recipients = requests.get(f"{api_base}/api/recipients", timeout=30).json() or []
        except Exception:
            recipients = []
        active = [r for r in recipients if r.get("active") == 1]
        for r in active:
            rid, email, display_name = r.get("id"), r.get("email", ""), r.get("display_name") or ""
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            with c1: st.text(email)
            with c2: st.text(display_name)
            with c3:
                if st.button("Delete", key=f"del_{rid}", type="secondary"):
                    try:
                        resp = requests.delete(f"{api_base}/api/recipients/{rid}", timeout=30)
                        if resp.status_code in (200, 204):
                            st.success("Removed.")
                            st.rerun()
                        else:
                            st.error(resp.json().get("error", f"HTTP {resp.status_code}"))
                    except Exception as ex:
                        st.error(str(ex))
            with c4:
                with st.expander("Edit"):
                    new_email = st.text_input("Email", value=email, key=f"edit_email_{rid}")
                    new_name = st.text_input("Display name", value=display_name, key=f"edit_name_{rid}")
                    if st.button("Save", key=f"save_{rid}"):
                        try:
                            resp = requests.patch(f"{api_base}/api/recipients/{rid}", json={"email": new_email.strip(), "display_name": new_name.strip() or None}, timeout=30)
                            if resp.status_code == 200:
                                st.success("Updated.")
                                st.rerun()
                            else:
                                st.error(resp.json().get("error", f"HTTP {resp.status_code}"))
                        except Exception as ex:
                            st.error(str(ex))
        if not active:
            st.info("No active recipients. Add one above.")
        st.divider()
        st.subheader("Weekly email delivery")
        try:
            reports = requests.get(f"{api_base}/api/reports", timeout=30).json() or []
        except Exception:
            reports = []
        if not reports:
            st.info("No reports yet.")
        else:
            rows = [{"Report": r.get("report_id") or r.get("week_start_date", "–"), "Generated": (r.get("generated_at") or "–")[:10], "Sent": (r.get("delivery_summary") or {}).get("sent", 0), "Failed": (r.get("delivery_summary") or {}).get("failed", 0), "Pending": (r.get("delivery_summary") or {}).get("not_sent", 0)} for r in reports]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.sidebar.caption("Connected to Phase 6 API. Uncheck 'Use external Phase 6 API' to use the built-in pipeline.")
        return

    # --- Local pipeline mode ---
    db_path = get_db_path()
    conn = pipeline_db.get_connection(db_path)

    # Run pipeline button
    st.sidebar.subheader("Pipeline")
    if st.sidebar.button("Run weekly pipeline (P1→P5)"):
        with st.spinner("Running pipeline (ingest, clean, analyze, report, email). This may take a few minutes."):
            try:
                results = run_weekly_pipeline(db_path)
                st.sidebar.success("Pipeline finished.")
                st.success("Pipeline completed: P1 ingested, P2 cleaned, P3 analyzed, P4 generated report, P5 sent emails (if recipients configured).")
                if results.get("phase5"):
                    st.info(f"Emails sent: {results['phase5'].get('sent', 0)} of {results['phase5'].get('total', 0)} recipients.")
            except Exception as e:
                st.error(f"Pipeline failed: {e}")
                st.sidebar.error("Pipeline failed.")
        st.rerun()

    st.sidebar.caption("Built-in pipeline uses GROQ_API_KEY, GEMINI_API_KEY, and SMTP env vars. Set in Secrets or .env.")

    # --- Recipients (local DB) ---
    st.subheader("Recipients")
    with st.expander("Add recipient", expanded=False):
        add_email = st.text_input("Email", key="add_email", placeholder="email@example.com")
        add_name = st.text_input("Display name (optional)", key="add_name")
        if st.button("Add recipient"):
            if not (add_email and add_email.strip()):
                st.error("Email is required.")
            else:
                try:
                    pipeline_db.add_recipient(conn, add_email.strip(), (add_name.strip() or None) if add_name else None)
                    st.success("Recipient added.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    recipients = pipeline_db.list_recipients(conn)
    active = [r for r in recipients if r.get("active") == 1]
    if not active:
        st.info("No active recipients. Add one above.")
    else:
        for r in active:
            rid, email, display_name = r.get("id"), r.get("email", ""), r.get("display_name") or ""
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            with c1: st.text(email)
            with c2: st.text(display_name)
            with c3:
                if st.button("Delete", key=f"del_{rid}", type="secondary"):
                    try:
                        pipeline_db.deactivate_recipient_by_id(conn, rid)
                        st.success("Removed.")
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))
            with c4:
                with st.expander("Edit"):
                    new_email = st.text_input("Email", value=email, key=f"edit_email_{rid}")
                    new_name = st.text_input("Display name", value=display_name, key=f"edit_name_{rid}")
                    if st.button("Save", key=f"save_{rid}"):
                        try:
                            pipeline_db.update_recipient(conn, rid, email=new_email.strip(), display_name=new_name.strip() or None)
                            st.success("Updated.")
                            st.rerun()
                        except Exception as ex:
                            st.error(str(ex))
    st.divider()

    # --- Reports and delivery (local DB) ---
    st.subheader("Weekly email delivery")
    st.caption("Per report: sent, failed, and pending (not yet sent) counts.")
    reports = pipeline_db.list_reports(conn)
    summary_map = pipeline_db.get_delivery_summary_per_report(conn)
    if not reports:
        st.info("No reports yet. Run the pipeline from the sidebar.")
    else:
        rows = []
        for r in reports:
            rid = r.get("report_id")
            summary = summary_map.get(rid, {"sent": 0, "failed": 0, "not_sent": 0})
            rows.append({
                "Report / week": rid or r.get("week_start_date", "–"),
                "Generated": (r.get("generated_at") or "–")[:10],
                "Sent": summary["sent"],
                "Failed": summary["failed"],
                "Pending": summary["not_sent"],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    conn.close()
    st.sidebar.divider()
    if pipeline_config.DATABASE_URL:
        st.sidebar.caption("Using shared hosted DB (DATABASE_URL). Recipients and reports are shared with the scheduled pipeline.")
    else:
        st.sidebar.caption("Product Pulse: all phases run in this app. Data in local SQLite. Set DATABASE_URL to use a shared hosted DB.")


if __name__ == "__main__":
    main()
