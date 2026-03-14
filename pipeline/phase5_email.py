"""Phase 5: Send latest report to active recipients via SMTP, record delivery_status."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse

from . import config
from . import db as pipeline_db

def _format_week(iso_date: str) -> str:
    if not iso_date:
        return ""
    try:
        from datetime import datetime
        d = datetime.fromisoformat(iso_date[:10])
        day = d.day
        if 10 <= day % 100 <= 20:
            suf = "th"
        else:
            suf = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return d.strftime(f"%d{suf} %B %Y")
    except Exception:
        return iso_date

def _subject(week_start_date: str) -> str:
    return f"INDmoney weekly product review – week of {_format_week(week_start_date)}"

def _send_email(to: str, subject: str, html: str, reply_to: str | None = None) -> tuple[bool, str | None]:
    from_addr = config.FROM_ADDRESS
    reply_to = reply_to or config.REPLY_TO or from_addr
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg["Reply-To"] = reply_to
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        if config.SMTP_URL:
            parsed = urlparse(config.SMTP_URL)
            host = parsed.hostname or config.SMTP_HOST
            port = parsed.port or (465 if parsed.scheme == "smtps" else config.SMTP_PORT)
            use_tls = parsed.scheme == "smtps"
            user = parsed.username
            password = parsed.password
        else:
            host, port = config.SMTP_HOST, config.SMTP_PORT
            use_tls = config.SMTP_SECURE
            user, password = config.SMTP_USER, config.SMTP_PASS
        if use_tls or port == 465:
            with smtplib.SMTP_SSL(host, port) as s:
                if user and password:
                    s.login(user, password)
                s.sendmail(from_addr, [to], msg.as_string())
        else:
            with smtplib.SMTP(host, port) as s:
                if use_tls:
                    s.starttls()
                if user and password:
                    s.login(user, password)
                s.sendmail(from_addr, [to], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)

def run(db_path: str | None = None, report_id_arg: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    reports_dir = Path(config.REPORTS_DIR)
    conn = pipeline_db.get_connection(db_path)
    try:
        meta = pipeline_db.get_report_metadata(conn, report_id_arg)
        if not meta:
            raise RuntimeError("No report metadata found. Run Phase 4 first.")
        report_path = reports_dir / f"{meta['report_id']}.html"
        if not report_path.exists():
            raise RuntimeError(f"Report body not found at {report_path}")
        html = report_path.read_text(encoding="utf-8")
        recipients = pipeline_db.get_active_recipients(conn)
        if not recipients:
            return {"sent": 0, "report_id": meta["report_id"]}
        subject = _subject(meta["week_start_date"])
        sent = 0
        for r in recipients:
            success, err = _send_email(r["email"], subject, html)
            status = "Sent" if success else "Error"
            from datetime import datetime
            sent_at = datetime.utcnow().isoformat() + "Z" if success else None
            pipeline_db.upsert_delivery_status(
                conn, meta["report_id"], r["email"], status,
                sent_at=sent_at, error_message=err,
            )
            if success:
                sent += 1
        return {"report_id": meta["report_id"], "sent": sent, "total": len(recipients)}
    finally:
        conn.close()
