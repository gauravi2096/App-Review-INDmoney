"""
INDmoney Review Pulse – Streamlit app.
Tabs: Latest report (chart + latest report, read-only), Recipients (add/edit/delete gated behind
a one-time-per-action admin password dialog), Delivery logs. The pipeline itself runs only via
the scheduled/manual GitHub Actions workflow — this app has no way to trigger it.
Uses local SQLite and Python pipeline by default. Optional: connect to Phase 6 API instead (sidebar).
"""
import hmac
import html
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

import altair as alt
import pandas as pd
import streamlit.components.v1 as components

from pipeline import config as pipeline_config
from pipeline import db as pipeline_db

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
        [class*="st-key-view_report_wrap_"] button[kind="tertiary"]:hover {
            color: #4F46E5 !important;
            text-decoration: underline;
        }
        /* Edit/Delete icon buttons: the underlying st.button(...) keeps its
           original label, key, and click handler (a pure visual swap); both
           use type="tertiary" (borderless) so Edit matches Delete's weight
           exactly. The text is hidden and a masked SVG glyph is painted in
           its place via ::before, which lets us recolor the same icon per
           state (neutral for Edit, muted-then-red-on-hover for Delete) with
           plain CSS instead of shipping two separate icon assets per color. */
        [class*="st-key-edit_wrap_"] button,
        [class*="st-key-delete_wrap_"] button {
            color: transparent !important;
            font-size: 0 !important;
            width: 34px !important;
            min-width: 34px !important;
            height: 34px !important;
            min-height: 34px !important;
            max-height: 34px !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center;
            justify-content: center;
        }
        /* Streamlit lays out a button's own content (icon slot + label) as a
           flex row; without an explicit flex-basis our pseudo-element gets
           squeezed to 0 width by that internal layout. */
        [class*="st-key-edit_wrap_"] button::before,
        [class*="st-key-delete_wrap_"] button::before {
            content: "";
            flex: 0 0 17px;
            display: inline-block;
            width: 17px;
            height: 17px;
            -webkit-mask-size: contain;
            mask-size: contain;
            -webkit-mask-repeat: no-repeat;
            mask-repeat: no-repeat;
            -webkit-mask-position: center;
            mask-position: center;
        }
        [class*="st-key-edit_wrap_"] button::before {
            background-color: #57606a;
            -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGhlaWdodD0iMjRweCIgdmlld0JveD0iMCAtOTYwIDk2MCA5NjAiIHdpZHRoPSIyNHB4IiBmaWxsPSIjZTNlM2UzIj48cGF0aCBkPSJNMjAwLTIwMGg1N2wzOTEtMzkxLTU3LTU3LTM5MSAzOTF2NTdabS04MCA4MHYtMTcwbDUyOC01MjdxMTItMTEgMjYuNS0xN3QzMC41LTZxMTYgMCAzMSA2dDI2IDE4bDU1IDU2cTEyIDExIDE3LjUgMjZ0NS41IDMwcTAgMTYtNS41IDMwLjVUODE3LTY0N0wyOTAtMTIwSDEyMFptNjQwLTU4NC01Ni01NiA1NiA1NlptLTE0MSA4NS0yOC0yOSA1NyA1Ny0yOS0yOFoiLz48L3N2Zz4=");
            mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGhlaWdodD0iMjRweCIgdmlld0JveD0iMCAtOTYwIDk2MCA5NjAiIHdpZHRoPSIyNHB4IiBmaWxsPSIjZTNlM2UzIj48cGF0aCBkPSJNMjAwLTIwMGg1N2wzOTEtMzkxLTU3LTU3LTM5MSAzOTF2NTdabS04MCA4MHYtMTcwbDUyOC01MjdxMTItMTEgMjYuNS0xN3QzMC41LTZxMTYgMCAzMSA2dDI2IDE4bDU1IDU2cTEyIDExIDE3LjUgMjZ0NS41IDMwcTAgMTYtNS41IDMwLjVUODE3LTY0N0wyOTAtMTIwSDEyMFptNjQwLTU4NC01Ni01NiA1NiA1NlptLTE0MSA4NS0yOC0yOSA1NyA1Ny0yOS0yOFoiLz48L3N2Zz4=");
        }
        [class*="st-key-delete_wrap_"] button::before {
            background-color: #8b8f98;
            -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGhlaWdodD0iMjRweCIgdmlld0JveD0iMCAtOTYwIDk2MCA5NjAiIHdpZHRoPSIyNHB4IiBmaWxsPSIjZTNlM2UzIj48cGF0aCBkPSJNMjgwLTEyMHEtMzMgMC01Ni41LTIzLjVUMjAwLTIwMHYtNTIwaC00MHYtODBoMjAwdi00MGgyNDB2NDBoMjAwdjgwaC00MHY1MjBxMCAzMy0yMy41IDU2LjVUNjgwLTEyMEgyODBabTQwMC02MDBIMjgwdjUyMGg0MDB2LTUyMFpNMzYwLTI4MGg4MHYtMzYwaC04MHYzNjBabTE2MCAwaDgwdi0zNjBoLTgwdjM2MFpNMjgwLTcyMHY1MjAtNTIwWiIvPjwvc3ZnPg==");
            mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGhlaWdodD0iMjRweCIgdmlld0JveD0iMCAtOTYwIDk2MCA5NjAiIHdpZHRoPSIyNHB4IiBmaWxsPSIjZTNlM2UzIj48cGF0aCBkPSJNMjgwLTEyMHEtMzMgMC01Ni41LTIzLjVUMjAwLTIwMHYtNTIwaC00MHYtODBoMjAwdi00MGgyNDB2NDBoMjAwdjgwaC00MHY1MjBxMCAzMy0yMy41IDU2LjVUNjgwLTEyMEgyODBabTQwMC02MDBIMjgwdjUyMGg0MDB2LTUyMFpNMzYwLTI4MGg4MHYtMzYwaC04MHYzNjBabTE2MCAwaDgwdi0zNjBoLTgwdjM2MFpNMjgwLTcyMHY1MjAtNTIwWiIvPjwvc3ZnPg==");
        }
        [class*="st-key-delete_wrap_"] button:hover::before {
            background-color: #cf222e !important;
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
        /* align-items:center on stColumn only centers its direct child block;
           that block (stVerticalBlock) still stacks its own content flush to
           the top, so the actual cell content needs its own centering too.
           stVerticalBlock is flex-direction: column, so the vertical axis is
           the main axis here — justify-content, not align-items. */
        [class*="st-key-recipients_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"],
        [class*="st-key-delivery_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"],
        .st-key-recipients_header div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"],
        .st-key-delivery_header div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
            display: flex;
            justify-content: center;
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
        f'<span style="display:inline-flex;align-items:center;background:#EEF0FF;color:#4F46E5;'
        f'border-radius:999px;padding:2px 10px;font-size:0.78rem;font-weight:600;white-space:nowrap;">{role_department}</span>',
        unsafe_allow_html=True,
    )

def render_run_status_badge(status, failed_phase=None, error_message=None):
    pill = "display:inline-flex;align-items:center;border-radius:999px;padding:2px 10px;font-size:0.78rem;font-weight:600;white-space:nowrap;"
    if status == "success":
        return f'<span style="{pill}background:#DAFBE1;color:#1a7f37;">Success</span>'
    if status == "success_with_fallback":
        detail = "Analysis or report used the deterministic fallback instead of full LLM output."
        return f'<span title="{html.escape(detail)}" style="{pill}background:#FFF3CD;color:#9A6700;cursor:help;">Fallback used</span>'
    if status == "failed":
        detail = f"{failed_phase or 'Unknown phase'}: {error_message or 'No details available'}"
        return f'<span title="{html.escape(detail)}" style="{pill}background:#FFEBE9;color:#cf222e;cursor:help;">Failed</span>'
    if status == "running":
        return f'<span style="{pill}background:#EEF0FF;color:#4F46E5;">Running…</span>'
    return "<span style='color:#8b8f98'>—</span>"

def _st_secret(name: str):
    """st.secrets.get(name) raises StreamlitSecretNotFoundError (not caught by .get()'s own
    KeyError handling) when no secrets.toml exists anywhere — a real case for local/.env-only
    setups, not a hypothetical. Swallow that so callers can fall back to env vars."""
    if not hasattr(st, "secrets"):
        return None
    try:
        return st.secrets.get(name)
    except Exception:
        return None

def get_secret(name: str):
    """Same lookup order the app already uses for P6_API_URL: st.secrets first, env fallback."""
    val = _st_secret(name)
    if val:
        return val
    return os.environ.get(name) or None

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
        if value is None:
            return "<span style='color:#8b8f98'>—</span>"
        try:
            n = int(value)
        except Exception:
            n = 0
        color = color_on if n > 0 else color_off
        return f"<span style='color:{color}; font-weight:600'>{value}</span>"

    widths = [1.6, 1.0, 1.3, 0.7, 0.7, 1.2]
    render_table_header(widths, ["Week", "Generated", "Status", "Sent", "Failed", ""], key="delivery_header")

    for row in rows:
        report_id = row.get("_report_id")
        run_key = row.get("_run_id") or report_id or id(row)
        row_key = f"delivery_row_{run_key}"
        toggle_key = f"view_report_{run_key}"
        with st.container(key=row_key):
            cols = st.columns(widths)
            cols[0].write(row["Week"])
            cols[1].write(row["Generated"])
            cols[2].markdown(
                render_run_status_badge(row.get("Status", "success"), row.get("FailedPhase"), row.get("ErrorMessage")),
                unsafe_allow_html=True,
            )
            cols[3].markdown(colored(row["Sent"], "#1a7f37", "#8b8f98"), unsafe_allow_html=True)
            cols[4].markdown(colored(row["Failed"], "#cf222e", "#8b8f98"), unsafe_allow_html=True)
            with cols[5]:
                with st.container(key=f"view_report_wrap_{run_key}"):
                    if report_id:
                        # Static label by design: Streamlit renders a button's label from
                        # state as of the START of this run, so a label that flips based
                        # on st.session_state set moments earlier in the same run would
                        # display one interaction behind (looks "stuck" after opening).
                        # The explicit Close button below the content avoids that trap.
                        if st.button("View report", key=f"btn_{toggle_key}", type="tertiary"):
                            st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)
                    else:
                        st.caption("No report generated")
        if report_id and st.session_state.get(toggle_key):
            with st.container(border=True):
                content, source = fetch_report_fn(report_id, row.get("_storage_path")) if fetch_report_fn else (None, None)
                if content:
                    hcol, ccol = st.columns([5, 1])
                    hcol.caption(f"Report content for {report_id} (source: {source})")
                    with ccol:
                        with st.container(key=f"view_report_wrap_close_{run_key}"):
                            if st.button("Close", key=f"close_{toggle_key}", type="tertiary"):
                                st.session_state[toggle_key] = False
                    components.html(content, height=500, scrolling=True)
                else:
                    st.info(
                        "Report content isn't available for this run. It's only stored in the database "
                        "when DATABASE_URL (shared hosted DB) is set; otherwise it relies on the local report "
                        "file, which may no longer exist."
                    )
        with st.container(key=f"delivery_divider_{run_key}"):
            st.divider()

def get_db_path():
    return pipeline_config.DB_PATH

def use_external_api():
    if _st_secret("P6_API_URL"):
        return True
    if os.environ.get("P6_API_URL"):
        return True
    return st.sidebar.checkbox("Use external Phase 6 API", value=False, help="If checked, connect to Phase 6 API for data and actions instead of local pipeline.")

def get_api_base():
    base = _st_secret("P6_API_URL")
    if not base:
        base = os.environ.get("P6_API_URL", "").rstrip("/")
    if not base:
        base = st.sidebar.text_input("Phase 6 API URL", value="http://localhost:4006", key="api_url").rstrip("/")
    return base

# --- Rating-over-time chart ---
@st.cache_data(ttl=600)
def load_rating_over_time(_conn):
    """_conn is prefixed with an underscore so st.cache_data doesn't try to hash a DB connection.
    De-dup happens in SQL (SELECT DISTINCT); week grouping happens here in pandas so the same
    code works against both SQLite and Postgres. Weeks with no data are reindexed in as NaN
    rows (not 0), so the chart renders them as a gap rather than a dip to zero."""
    rows = pipeline_db.get_distinct_raw_reviews(_conn)
    df = pd.DataFrame(rows, columns=["date", "rating", "text"])
    if df.empty:
        return df.assign(week_start=[], avg_rating=[], review_count=[])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return pd.DataFrame(columns=["week_start", "avg_rating", "review_count"])
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.day_of_week, unit="D")
    weekly = df.groupby("week_start").agg(avg_rating=("rating", "mean"), review_count=("rating", "size")).reset_index()
    full_weeks = pd.date_range(weekly["week_start"].min(), weekly["week_start"].max(), freq="7D")
    weekly = weekly.set_index("week_start").reindex(full_weeks).rename_axis("week_start").reset_index()
    return weekly

def render_rating_chart(weekly_df):
    if weekly_df.empty or weekly_df["avg_rating"].dropna().empty:
        st.info("Not enough review data yet to chart ratings over time.")
        return
    y_enc = alt.Y("avg_rating:Q", title="Avg rating", scale=alt.Scale(domain=[1, 5]))
    line = alt.Chart(weekly_df).mark_line(color="#4F46E5").encode(
        x=alt.X("week_start:T", title="Week"), y=y_enc,
    )
    points_df = weekly_df.dropna(subset=["avg_rating"])
    points = alt.Chart(points_df).mark_point(filled=True, size=60, color="#4F46E5").encode(
        x=alt.X("week_start:T", title="Week"), y=y_enc,
        tooltip=[
            alt.Tooltip("week_start:T", title="Week"),
            alt.Tooltip("avg_rating:Q", title="Avg rating", format=".1f"),
            alt.Tooltip("review_count:Q", title="Reviews"),
        ],
    )
    st.altair_chart((line + points).properties(height=320), width="stretch")
    st.caption("Weekly average of Google Play reviews, de-duplicated across runs.")

# --- Tab 1: Latest report ---
def render_latest_report_tab(conn):
    """Only the chart and the latest report, stacked, full width — no header, no run status,
    no buttons. The report is the single most recent report_metadata row, independent of
    whether a later pipeline run since then has failed."""
    render_rating_chart(load_rating_over_time(conn))
    meta = pipeline_db.get_report_metadata(conn)
    if meta and meta.get("report_id"):
        content, source = fetch_report_local(conn, meta["report_id"], meta.get("storage_artifact_path"))
        if content:
            # Phase 4 caps reports at ~400 words (config.MAX_WORDS); 800px comfortably fits that
            # without leaving a wall of blank space below short reports — scrolling=True covers outliers.
            components.html(content, height=800, scrolling=True)
        else:
            st.info(
                "Report content isn't available for this run. It's only stored in the database "
                "when DATABASE_URL (shared hosted DB) is set; otherwise it relies on the local report "
                "file, which may no longer exist."
            )
    else:
        st.info("No report has been generated yet.")

# --- Tab 2: Recipients ---
# A single module-level dialog (not nested in the fragment) so Streamlit's dialog identity
# stays stable across fragment reruns; it reads which action/row is pending from session_state
# rather than from closed-over arguments, and opens its own connection rather than sharing one
# with the fragment that triggered it.
@st.dialog("Admin password required")
def _recipients_password_dialog():
    target = st.session_state.get("recipients_dialog_target")
    if not target:
        return
    action, rid = target
    app_password = get_secret("APP_PASSWORD")
    if not app_password:
        st.error("Admin password is not configured")
        if st.button("Close", key="recipients_dialog_close_noconfig"):
            st.session_state.recipients_dialog_target = None
            # Plain st.rerun(): dialogs are an app-level overlay even when triggered from a
            # fragment, so scope="fragment" leaves the dialog shell stuck open (confirmed live).
            st.rerun()
        return
    pwd = st.text_input("Password", type="password", key="recipients_dialog_pwd")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Confirm", key="recipients_dialog_confirm", type="primary"):
            if hmac.compare_digest(pwd or "", app_password):
                ok = True
                if action == "add":
                    st.session_state.show_add_recipient = True
                elif action == "edit":
                    st.session_state[f"edit_open_{rid}"] = True
                elif action == "delete":
                    conn = pipeline_db.get_connection(pipeline_config.DB_PATH)
                    try:
                        pipeline_db.deactivate_recipient_by_id(conn, rid)
                        st.success("Removed.")
                    except Exception as ex:
                        st.error(str(ex))
                        ok = False
                    finally:
                        conn.close()
                if ok:
                    st.session_state.recipients_dialog_target = None
                    st.rerun()
            else:
                st.error("Incorrect password.")
    with c2:
        if st.button("Cancel", key="recipients_dialog_cancel"):
            st.session_state.recipients_dialog_target = None
            st.rerun()

@st.fragment
def render_recipients_tab(db_path):
    """Opens its own DB connection rather than reusing main()'s: a fragment reruns on its own
    when a widget inside it fires, without re-running the rest of main() — so a connection
    opened (and later closed) by the outer call would be stale/closed on that next interaction.
    The recipient list itself is always visible; only Add/Edit/Delete are password-gated, via a
    dialog asked fresh every time (no session-wide unlock)."""
    conn = pipeline_db.get_connection(db_path)

    if st.session_state.get("recipients_dialog_target"):
        _recipients_password_dialog()

    if "show_add_recipient" not in st.session_state:
        st.session_state.show_add_recipient = False
    with st.container(key="add_recipient_cta"):
        if st.button("Add recipient", icon=":material/add:", type="primary", key="toggle_add_recipient"):
            st.session_state.recipients_dialog_target = ("add", None)
            st.rerun(scope="fragment")
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
                            conn.close()  # st.rerun() aborts this call, skipping the conn.close() at the function's end
                            st.rerun(scope="fragment")
                        except Exception as e:
                            st.error(str(e))
            with fc2:
                if st.button("Cancel", key="cancel_add_recipient"):
                    st.session_state.show_add_recipient = False
                    conn.close()
                    st.rerun(scope="fragment")

    recipients = pipeline_db.list_recipients(conn)
    active = [r for r in recipients if r.get("active") == 1]
    if not active:
        st.info("No active recipients. Add one above.")
        st.divider()
    else:
        recipient_widths = [1.5, 1.3, 2, 0.75, 0.75]
        render_table_header(recipient_widths, ["Display Name", "Role / Department", "Email", "", ""], key="recipients_header")
        for r in active:
            rid, email, display_name = r.get("id"), r.get("email", ""), r.get("display_name") or ""
            role_department = r.get("role_department") or ""
            edit_key = f"edit_open_{rid}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False
            with st.container(key=f"recipients_row_{rid}"):
                c1, c2, c3, c4, c5 = st.columns(recipient_widths)
                with c1: render_plain_text(display_name)
                with c2: render_role_badge(role_department)
                with c3: render_plain_text(email)
                with c4:
                    with st.container(key=f"edit_wrap_{rid}"):
                        if st.button("Edit", key=f"edit_{rid}", type="tertiary", help="Edit"):
                            st.session_state.recipients_dialog_target = ("edit", rid)
                            st.rerun(scope="fragment")
                with c5:
                    with st.container(key=f"delete_wrap_{rid}"):
                        if st.button("Delete", key=f"del_{rid}", type="tertiary", help="Delete"):
                            st.session_state.recipients_dialog_target = ("delete", rid)
                            st.rerun(scope="fragment")
            if st.session_state[edit_key]:
                with st.container(border=True):
                    new_email = st.text_input("Email", value=email, key=f"edit_email_{rid}")
                    new_name = st.text_input("Display name", value=display_name, key=f"edit_name_{rid}")
                    new_role = render_role_picker(f"edit_{rid}", current_value=role_department)
                    ec1, ec2 = st.columns([1, 1])
                    with ec1:
                        if st.button("Save", key=f"save_{rid}", type="primary"):
                            try:
                                ok = pipeline_db.update_recipient(conn, rid, email=new_email.strip(), display_name=new_name.strip() or None, role_department=new_role or "")
                                if ok:
                                    st.session_state[edit_key] = False
                                    st.success("Updated.")
                                    conn.close()
                                    st.rerun(scope="fragment")
                                else:
                                    st.error(f"Update failed: no recipient found with id {rid}. Refresh and try again.")
                            except Exception as ex:
                                st.error(str(ex))
                    with ec2:
                        if st.button("Cancel", key=f"cancel_edit_{rid}"):
                            st.session_state[edit_key] = False
                            conn.close()
                            st.rerun(scope="fragment")
            with st.container(key=f"recipients_divider_{rid}"):
                st.divider()
    conn.close()

# --- Tab 3: Delivery logs ---
def render_delivery_logs_tab(conn):
    st.caption("Every pipeline run, including ones that failed before any email was sent.")
    runs = pipeline_db.list_pipeline_runs(conn)
    reports_by_run = {r["run_id"]: r for r in pipeline_db.list_reports(conn)}
    summary_map = pipeline_db.get_delivery_summary_per_report(conn)
    if not runs:
        st.info("No pipeline runs yet.")
        return
    rows = []
    for run in runs:
        run_id = run["run_id"]
        report = reports_by_run.get(run_id)
        if report:
            rid = report.get("report_id")
            summary = summary_map.get(rid, {"sent": 0, "failed": 0, "not_sent": 0})
            week = week_label(report.get("week_start_date"), report.get("generated_at"))
            generated = (report.get("generated_at") or "–")[:10]
            sent, failed = summary["sent"], summary["failed"]
            storage_path = report.get("storage_artifact_path")
        else:
            rid = None
            week = week_label(None, run.get("started_at"))
            generated = (run.get("started_at") or "–")[:10]
            sent, failed = None, None
            storage_path = None
        rows.append({
            "Week": week,
            "Generated": generated,
            "Status": run["status"],
            "FailedPhase": run.get("failed_phase"),
            "ErrorMessage": run.get("error_message"),
            "Sent": sent,
            "Failed": failed,
            "_report_id": rid,
            "_run_id": run_id,
            "_storage_path": storage_path,
        })
    render_delivery_table(rows, fetch_report_fn=lambda rid, sp: fetch_report_local(conn, rid, sp))

def main():
    use_api = use_external_api()
    api_base = get_api_base() if use_api else None

    inject_custom_css()
    st.title("INDmoney Review Pulse")
    st.caption("View the latest report, manage recipients, and track delivery status.")

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
            recipient_widths = [1.5, 1.3, 2, 0.75, 0.75]
            render_table_header(recipient_widths, ["Display Name", "Role / Department", "Email", "", ""], key="recipients_header")
            for r in active:
                rid, email, display_name = r.get("id"), r.get("email", ""), r.get("display_name") or ""
                role_department = r.get("role_department") or ""
                edit_key = f"edit_open_{rid}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                with st.container(key=f"recipients_row_{rid}"):
                    c1, c2, c3, c4, c5 = st.columns(recipient_widths)
                    with c1: render_plain_text(display_name)
                    with c2: render_role_badge(role_department)
                    with c3: render_plain_text(email)
                    with c4:
                        with st.container(key=f"edit_wrap_{rid}"):
                            if st.button("Edit", key=f"edit_{rid}", type="tertiary", help="Edit"):
                                st.session_state[edit_key] = not st.session_state[edit_key]
                    with c5:
                        with st.container(key=f"delete_wrap_{rid}"):
                            if st.button("Delete", key=f"del_{rid}", type="tertiary", help="Delete"):
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
        # Phase 6 (Node) has no pipeline_runs equivalent, so failed-before-report runs aren't
        # visible here and Status always renders as "success" via render_delivery_table's default.
        rows = [
            {
                "Week": week_label(r.get("week_start_date"), r.get("generated_at")),
                "Generated": (r.get("generated_at") or "–")[:10],
                "Sent": (r.get("delivery_summary") or {}).get("sent", 0),
                "Failed": (r.get("delivery_summary") or {}).get("failed", 0),
                "_report_id": r.get("report_id"),
                "_run_id": r.get("report_id"),
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

    tab_report, tab_recipients, tab_delivery = st.tabs(["Latest report", "Recipients", "Delivery logs"])
    with tab_report:
        render_latest_report_tab(conn)
    with tab_recipients:
        render_recipients_tab(db_path)
    with tab_delivery:
        render_delivery_logs_tab(conn)

    conn.close()
    st.sidebar.divider()
    if pipeline_config.DATABASE_URL:
        st.sidebar.caption("Using shared hosted DB (DATABASE_URL). Recipients and reports are shared with the scheduled pipeline.")
    else:
        st.sidebar.caption("INDmoney Review Pulse: all phases run in this app. Data in local SQLite. Set DATABASE_URL to use a shared hosted DB.")


if __name__ == "__main__":
    main()
