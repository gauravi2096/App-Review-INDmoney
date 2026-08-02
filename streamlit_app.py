"""
INDmoney Review Pulse – Streamlit app.
Runs all phases (P1–P6) in one deployment: manage recipients, trigger pipeline, view reports and delivery.
Uses local SQLite and Python pipeline by default. Optional: connect to Phase 6 API instead (sidebar).
"""
import os
import streamlit as st

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="INDmoney Review Pulse",
    page_icon="📊",
    layout="wide",
)

import contextlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit.components.v1 as components

from pipeline import config as pipeline_config
from pipeline import db as pipeline_db
from pipeline.runner import run_weekly_pipeline

def inject_custom_css():
    st.markdown(
        """
        <style>
        .stApp {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
                Roboto, Helvetica, Arial, sans-serif;
        }
        /* Tertiary (borderless) buttons are muted by default; hover color is
           scoped per action below so Delete hints red and View report hints
           the app's purple accent, instead of both sharing one hover color. */
        button[kind="tertiary"] {
            color: #8b8f98 !important;
            font-size: 0.85rem;
        }
        [class*="st-key-delete_wrap_"] button[kind="tertiary"]:hover {
            color: #cf222e !important;
            text-decoration: underline;
        }
        [class*="st-key-view_report_wrap_"] button[kind="tertiary"]:hover {
            color: #4F46E5 !important;
            text-decoration: underline;
        }
        /* Right-align the "Add recipient" CTA within its full-width block.
           Streamlit's container is flex-direction: column, so the horizontal
           axis is the cross axis (align-items), not the main axis. */
        .st-key-add_recipient_cta {
            align-items: flex-end;
        }
        /* Tighten vertical rhythm: this is a dense admin dashboard, not a
           landing page, so cut down the default Streamlit block spacing. */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        h1 {
            margin-bottom: 0.2rem !important;
        }
        h2, h3 {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
        }
        hr {
            margin: 0.35rem 0 !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.4rem !important;
        }
        /* Streamlit's markdown renderer auto-links bare emails (GFM); reset
           that styling for plain data cells like the recipients table. */
        .rp-plain-cell a {
            color: inherit !important;
            text-decoration: none !important;
            pointer-events: none;
        }
        /* Row density for Recipients and Weekly email delivery only. Scoped to
           per-row/header keyed containers so the "Report content" preview box
           and edit-recipient form (separate containers, not matched by these
           prefixes) keep their existing padding untouched. */
        [class*="st-key-recipients_row_"] div[data-testid="stVerticalBlock"],
        [class*="st-key-delivery_row_"] div[data-testid="stVerticalBlock"],
        .st-key-recipients_header div[data-testid="stVerticalBlock"],
        .st-key-delivery_header div[data-testid="stVerticalBlock"] {
            gap: 0.1rem !important;
        }
        [class*="st-key-recipients_row_"] [data-testid="stMarkdownContainer"] p,
        [class*="st-key-delivery_row_"] [data-testid="stMarkdownContainer"] p,
        [class*="st-key-recipients_row_"] [data-testid="stMarkdownContainer"],
        [class*="st-key-delivery_row_"] [data-testid="stMarkdownContainer"] {
            margin: 0 !important;
        }
        [class*="st-key-recipients_row_"] .stButton button,
        [class*="st-key-delivery_row_"] .stButton button {
            padding-top: 0.15rem !important;
            padding-bottom: 0.15rem !important;
            min-height: unset !important;
        }
        [class*="st-key-recipients_row_"] div[data-testid="stColumn"],
        [class*="st-key-delivery_row_"] div[data-testid="stColumn"],
        .st-key-recipients_header div[data-testid="stColumn"],
        .st-key-delivery_header div[data-testid="stColumn"] {
            display: flex;
            align-items: center;
        }
        [class*="st-key-recipients_divider_"] hr,
        [class*="st-key-delivery_divider_"] hr {
            margin: 0.15rem 0 !important;
        }
        .st-key-recipients_header hr,
        .st-key-delivery_header hr {
            margin: 0.15rem 0 8px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_table_header(widths, labels, key=None):
    with st.container(key=key) if key else contextlib.nullcontext():
        cols = st.columns(widths)
        for col, label in zip(cols, labels):
            if label:
                col.markdown(f"<span style='color:#8b8f98; font-size:0.82em; font-weight:600;'>{label}</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:4px 0 8px;'>", unsafe_allow_html=True)

ROLE_OPTIONS = ["Product", "Marketing", "Sales", "Support", "Leadership", "Other"]
ROLE_PLACEHOLDER = "— Select —"

def render_role_picker(key_prefix, current_value=None):
    current_value = (current_value or "").strip()
    choices = [ROLE_PLACEHOLDER] + ROLE_OPTIONS
    if current_value in ROLE_OPTIONS:
        default_index = choices.index(current_value)
        default_other = ""
    elif current_value:
        default_index = choices.index("Other")
        default_other = current_value
    else:
        default_index = 0
        default_other = ""
    choice = st.selectbox("Role / Department", choices, index=default_index, key=f"{key_prefix}_role_select")
    if choice == "Other":
        other_val = st.text_input(
            "Specify role / department", value=default_other, key=f"{key_prefix}_role_other", placeholder="e.g. Data Science"
        )
        return (other_val or "").strip() or None
    if choice == ROLE_PLACEHOLDER:
        return None
    return choice

def render_plain_text(value):
    # st.write()/st.markdown() auto-link bare emails via GFM even inside a raw
    # span, which clashes with the plain, unstyled data cells used elsewhere.
    # Neutralize the link's styling via a scoped class instead of fighting the
    # autolinker itself.
    st.markdown(f'<div class="rp-plain-cell">{value}</div>', unsafe_allow_html=True)

def render_role_badge(role_department):
    if not role_department:
        st.caption("—")
        return
    st.markdown(
        f'<span style="background:#EEF0FF;color:#4F46E5;border-radius:999px;'
        f'padding:2px 10px;font-size:0.78rem;font-weight:600;white-space:nowrap;">{role_department}</span>',
        unsafe_allow_html=True,
    )

def week_label(week_start_date, generated_at):
    src = week_start_date or generated_at
    if not src:
        return "–"
    try:
        d = datetime.fromisoformat(str(src)[:10])
    except Exception:
        return str(src)[:10]
    try:
        day = d.strftime("%-d")
    except ValueError:
        day = str(d.day)
    return f"Week of {d.strftime('%b')} {day}, {d.strftime('%Y')}"

def fetch_report_local(conn, report_id, storage_artifact_path):
    meta = pipeline_db.get_report_metadata(conn, report_id)
    body_html = meta.get("body_html") if meta else None
    if body_html:
        return body_html, "database"
    # body_html is only populated when DATABASE_URL is set; otherwise fall back to
    # the file on disk. storage_artifact_path is stored relative to the repo root
    # without the configured reports dir, so also try resolving by filename alone.
    candidates = []
    if storage_artifact_path:
        candidates.append(Path(storage_artifact_path))
        candidates.append(Path(pipeline_config.REPORTS_DIR) / Path(storage_artifact_path).name)
    for path in candidates:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8"), "local file"
        except Exception:
            continue
    return None, None

def fetch_report_api(api_base, requests_module, report_id, storage_artifact_path):
    try:
        resp = requests_module.get(f"{api_base}/api/reports/{report_id}/html", timeout=15)
        if resp.status_code == 200 and resp.text:
            return resp.text, "Phase 6 API"
    except Exception:
        pass
    return None, None

def render_delivery_table(rows, fetch_report_fn=None):
    if not rows:
        st.info("No reports yet.")
        return

    def colored(value, color_on, color_off):
        try:
            n = int(value)
        except Exception:
            n = 0
        color = color_on if n > 0 else color_off
        return f"<span style='color:{color}; font-weight:600'>{value}</span>"

    widths = [1.7, 1.1, 0.7, 0.7, 0.8, 1.7, 1.2]
    render_table_header(widths, ["Week", "Generated", "Sent", "Failed", "Pending", "Run ID", ""], key="delivery_header")

    for row in rows:
        report_id = row.get("_report_id")
        row_key = f"delivery_row_{report_id or id(row)}"
        with st.container(key=row_key):
            cols = st.columns(widths)
            cols[0].write(row["Week"])
            cols[1].write(row["Generated"])
            cols[2].markdown(colored(row["Sent"], "#1a7f37", "#8b8f98"), unsafe_allow_html=True)
            cols[3].markdown(colored(row["Failed"], "#cf222e", "#8b8f98"), unsafe_allow_html=True)
            cols[4].markdown(f"<span style='color:#8b8f98'>{row['Pending']}</span>", unsafe_allow_html=True)
            cols[5].markdown(f"<span style='color:#8b8f98; font-size:0.82em'>{row['Run ID']}</span>", unsafe_allow_html=True)
            toggle_key = f"view_report_{report_id}"
            with cols[6]:
                with st.container(key=f"view_report_wrap_{report_id or id(row)}"):
                    # Static label by design: Streamlit renders a button's label from
                    # state as of the START of this run, so a label that flips based
                    # on st.session_state set moments earlier in the same run would
                    # display one interaction behind (looks "stuck" after opening).
                    # The explicit Close button below the content avoids that trap.
                    if st.button("View report", key=f"btn_{toggle_key}", type="tertiary", disabled=not report_id):
                        st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)
        if report_id and st.session_state.get(toggle_key):
            with st.container(border=True):
                content, source = fetch_report_fn(report_id, row.get("_storage_path")) if fetch_report_fn else (None, None)
                if content:
                    hcol, ccol = st.columns([5, 1])
                    hcol.caption(f"Report content for {report_id} (source: {source})")
                    with ccol:
                        with st.container(key=f"view_report_wrap_close_{report_id or id(row)}"):
                            if st.button("Close", key=f"close_{toggle_key}", type="tertiary"):
                                st.session_state[toggle_key] = False
                                st.rerun()
                    components.html(content, height=500, scrolling=True)
                else:
                    st.info(
                        "Report content isn't available for this run. It's only stored in the database "
                        "when DATABASE_URL (shared hosted DB) is set; otherwise it relies on the local report "
                        "file, which may no longer exist."
                    )
        with st.container(key=f"delivery_divider_{report_id or id(row)}"):
            st.divider()

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

    inject_custom_css()
    st.title("INDmoney Review Pulse")
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
        if "show_add_recipient" not in st.session_state:
            st.session_state.show_add_recipient = False
        with st.container(key="add_recipient_cta"):
            if st.button("Add recipient", icon=":material/add:", type="primary", key="toggle_add_recipient"):
                st.session_state.show_add_recipient = not st.session_state.show_add_recipient
        if st.session_state.show_add_recipient:
            with st.container(border=True):
                add_email = st.text_input("Email", key="add_email", placeholder="email@example.com")
                add_name = st.text_input("Display name (optional)", key="add_name")
                add_role = render_role_picker("add")
                fc1, fc2 = st.columns([1, 1])
                with fc1:
                    if st.button("Add recipient", key="submit_add_recipient", type="primary"):
                        if not (add_email and add_email.strip()):
                            st.error("Email is required.")
                        else:
                            try:
                                r = requests.post(f"{api_base}/api/recipients", json={"email": add_email.strip(), "display_name": (add_name.strip() or None) if add_name else None, "role_department": add_role}, timeout=30)
                                if r.status_code in (200, 201):
                                    st.session_state.show_add_recipient = False
                                    st.success("Recipient added.")
                                    st.rerun()
                                else:
                                    st.error(r.json().get("error", f"HTTP {r.status_code}"))
                            except Exception as e:
                                st.error(str(e))
                with fc2:
                    if st.button("Cancel", key="cancel_add_recipient"):
                        st.session_state.show_add_recipient = False
                        st.rerun()
        try:
            recipients = requests.get(f"{api_base}/api/recipients", timeout=30).json() or []
        except Exception:
            recipients = []
        active = [r for r in recipients if r.get("active") == 1]
        if not active:
            st.info("No active recipients. Add one above.")
            st.divider()
        else:
            recipient_widths = [2, 1.5, 1.3, 0.75, 0.75]
            render_table_header(recipient_widths, ["Email", "Display Name", "Role / Department", "", ""], key="recipients_header")
            for r in active:
                rid, email, display_name = r.get("id"), r.get("email", ""), r.get("display_name") or ""
                role_department = r.get("role_department") or ""
                edit_key = f"edit_open_{rid}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                with st.container(key=f"recipients_row_{rid}"):
                    c1, c2, c3, c4, c5 = st.columns(recipient_widths)
                    with c1: render_plain_text(email)
                    with c2: render_plain_text(display_name)
                    with c3: render_role_badge(role_department)
                    with c4:
                        if st.button("Edit", key=f"edit_{rid}", type="secondary"):
                            st.session_state[edit_key] = not st.session_state[edit_key]
                    with c5:
                        with st.container(key=f"delete_wrap_{rid}"):
                            if st.button("Delete", key=f"del_{rid}", type="tertiary"):
                                try:
                                    resp = requests.delete(f"{api_base}/api/recipients/{rid}", timeout=30)
                                    if resp.status_code in (200, 204):
                                        st.success("Removed.")
                                        st.rerun()
                                    else:
                                        st.error(resp.json().get("error", f"HTTP {resp.status_code}"))
                                except Exception as ex:
                                    st.error(str(ex))
                if st.session_state[edit_key]:
                    with st.container(border=True):
                        new_email = st.text_input("Email", value=email, key=f"edit_email_{rid}")
                        new_name = st.text_input("Display name", value=display_name, key=f"edit_name_{rid}")
                        new_role = render_role_picker(f"edit_{rid}", current_value=role_department)
                        ec1, ec2 = st.columns([1, 1])
                        with ec1:
                            if st.button("Save", key=f"save_{rid}", type="primary"):
                                try:
                                    resp = requests.patch(f"{api_base}/api/recipients/{rid}", json={"email": new_email.strip(), "display_name": new_name.strip() or None, "role_department": new_role}, timeout=30)
                                    if resp.status_code == 200:
                                        st.session_state[edit_key] = False
                                        st.success("Updated.")
                                        st.rerun()
                                    else:
                                        st.error(resp.json().get("error", f"HTTP {resp.status_code}"))
                                except Exception as ex:
                                    st.error(str(ex))
                        with ec2:
                            if st.button("Cancel", key=f"cancel_edit_{rid}"):
                                st.session_state[edit_key] = False
                                st.rerun()
                with st.container(key=f"recipients_divider_{rid}"):
                    st.divider()
        st.subheader("Weekly email delivery")
        try:
            reports = requests.get(f"{api_base}/api/reports", timeout=30).json() or []
        except Exception:
            reports = []
        rows = [
            {
                "Week": week_label(r.get("week_start_date"), r.get("generated_at")),
                "Generated": (r.get("generated_at") or "–")[:10],
                "Sent": (r.get("delivery_summary") or {}).get("sent", 0),
                "Failed": (r.get("delivery_summary") or {}).get("failed", 0),
                "Pending": (r.get("delivery_summary") or {}).get("not_sent", 0),
                "Run ID": r.get("report_id") or r.get("week_start_date", "–"),
                "_report_id": r.get("report_id"),
                "_storage_path": r.get("storage_artifact_path"),
            }
            for r in reports
        ]
        render_delivery_table(rows, fetch_report_fn=lambda rid, sp: fetch_report_api(api_base, requests, rid, sp))
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
    if "show_add_recipient" not in st.session_state:
        st.session_state.show_add_recipient = False
    with st.container(key="add_recipient_cta"):
        if st.button("Add recipient", icon=":material/add:", type="primary", key="toggle_add_recipient"):
            st.session_state.show_add_recipient = not st.session_state.show_add_recipient
    if st.session_state.show_add_recipient:
        with st.container(border=True):
            add_email = st.text_input("Email", key="add_email", placeholder="email@example.com")
            add_name = st.text_input("Display name (optional)", key="add_name")
            add_role = render_role_picker("add")
            fc1, fc2 = st.columns([1, 1])
            with fc1:
                if st.button("Add recipient", key="submit_add_recipient", type="primary"):
                    if not (add_email and add_email.strip()):
                        st.error("Email is required.")
                    else:
                        try:
                            pipeline_db.add_recipient(conn, add_email.strip(), (add_name.strip() or None) if add_name else None, add_role)
                            st.session_state.show_add_recipient = False
                            st.success("Recipient added.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            with fc2:
                if st.button("Cancel", key="cancel_add_recipient"):
                    st.session_state.show_add_recipient = False
                    st.rerun()

    recipients = pipeline_db.list_recipients(conn)
    active = [r for r in recipients if r.get("active") == 1]
    if not active:
        st.info("No active recipients. Add one above.")
        st.divider()
    else:
        recipient_widths = [2, 1.5, 1.3, 0.75, 0.75]
        render_table_header(recipient_widths, ["Email", "Display Name", "Role / Department", "", ""], key="recipients_header")
        for r in active:
            rid, email, display_name = r.get("id"), r.get("email", ""), r.get("display_name") or ""
            role_department = r.get("role_department") or ""
            edit_key = f"edit_open_{rid}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False
            with st.container(key=f"recipients_row_{rid}"):
                c1, c2, c3, c4, c5 = st.columns(recipient_widths)
                with c1: render_plain_text(email)
                with c2: render_plain_text(display_name)
                with c3: render_role_badge(role_department)
                with c4:
                    if st.button("Edit", key=f"edit_{rid}", type="secondary"):
                        st.session_state[edit_key] = not st.session_state[edit_key]
                with c5:
                    with st.container(key=f"delete_wrap_{rid}"):
                        if st.button("Delete", key=f"del_{rid}", type="tertiary"):
                            try:
                                pipeline_db.deactivate_recipient_by_id(conn, rid)
                                st.success("Removed.")
                                st.rerun()
                            except Exception as ex:
                                st.error(str(ex))
            if st.session_state[edit_key]:
                with st.container(border=True):
                    new_email = st.text_input("Email", value=email, key=f"edit_email_{rid}")
                    new_name = st.text_input("Display name", value=display_name, key=f"edit_name_{rid}")
                    new_role = render_role_picker(f"edit_{rid}", current_value=role_department)
                    ec1, ec2 = st.columns([1, 1])
                    with ec1:
                        if st.button("Save", key=f"save_{rid}", type="primary"):
                            try:
                                pipeline_db.update_recipient(conn, rid, email=new_email.strip(), display_name=new_name.strip() or None, role_department=new_role or "")
                                st.session_state[edit_key] = False
                                st.success("Updated.")
                                st.rerun()
                            except Exception as ex:
                                st.error(str(ex))
                    with ec2:
                        if st.button("Cancel", key=f"cancel_edit_{rid}"):
                            st.session_state[edit_key] = False
                            st.rerun()
            with st.container(key=f"recipients_divider_{rid}"):
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
                "Week": week_label(r.get("week_start_date"), r.get("generated_at")),
                "Generated": (r.get("generated_at") or "–")[:10],
                "Sent": summary["sent"],
                "Failed": summary["failed"],
                "Pending": summary["not_sent"],
                "Run ID": rid or r.get("week_start_date", "–"),
                "_report_id": rid,
                "_storage_path": r.get("storage_artifact_path"),
            })
        render_delivery_table(rows, fetch_report_fn=lambda rid, sp: fetch_report_local(conn, rid, sp))

    conn.close()
    st.sidebar.divider()
    if pipeline_config.DATABASE_URL:
        st.sidebar.caption("Using shared hosted DB (DATABASE_URL). Recipients and reports are shared with the scheduled pipeline.")
    else:
        st.sidebar.caption("INDmoney Review Pulse: all phases run in this app. Data in local SQLite. Set DATABASE_URL to use a shared hosted DB.")


if __name__ == "__main__":
    main()
