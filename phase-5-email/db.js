/**
 * Database layer for Phase 5: read report_metadata and recipients, write delivery_status.
 * Same DB as P1–P4 (product-pulse.db).
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const REPORT_METADATA_TABLE = 'report_metadata';
const RECIPIENTS_TABLE = 'recipients';
const DELIVERY_STATUS_TABLE = 'delivery_status';

/**
 * Open DB and ensure recipients and delivery_status tables exist.
 * @param {string} dbPath
 * @returns {import('better-sqlite3').Database}
 */
function openDb(dbPath) {
  const dir = path.dirname(dbPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const db = new Database(dbPath);
  db.exec(`
    CREATE TABLE IF NOT EXISTS ${RECIPIENTS_TABLE} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL UNIQUE,
      display_name TEXT,
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_recipients_active ON ${RECIPIENTS_TABLE}(active);
    CREATE TABLE IF NOT EXISTS ${DELIVERY_STATUS_TABLE} (
      report_id TEXT NOT NULL,
      recipient_email TEXT NOT NULL,
      status TEXT NOT NULL,
      sent_at TEXT,
      error_message TEXT,
      PRIMARY KEY (report_id, recipient_email)
    );
    CREATE INDEX IF NOT EXISTS idx_delivery_status_report_id ON ${DELIVERY_STATUS_TABLE}(report_id);
  `);
  return db;
}

/**
 * Get report metadata by report_id or latest (by generated_at DESC).
 * @param {import('better-sqlite3').Database} db
 * @param {string | null} reportId - If null, returns latest.
 * @returns {{ report_id: string, week_start_date: string, storage_artifact_path: string } | null}
 */
function getReportMetadata(db, reportId = null) {
  const row = reportId
    ? db.prepare(
        `SELECT report_id, week_start_date, storage_artifact_path FROM ${REPORT_METADATA_TABLE} WHERE report_id = ?`
      ).get(reportId)
    : db.prepare(
        `SELECT report_id, week_start_date, storage_artifact_path FROM ${REPORT_METADATA_TABLE} ORDER BY generated_at DESC LIMIT 1`
      ).get();
  return row ? { report_id: row.report_id, week_start_date: row.week_start_date, storage_artifact_path: row.storage_artifact_path } : null;
}

/**
 * Get all active recipients.
 * @param {import('better-sqlite3').Database} db
 * @returns {Array<{ email: string, display_name: string | null }>}
 */
function getActiveRecipients(db) {
  const rows = db.prepare(
    `SELECT email, display_name FROM ${RECIPIENTS_TABLE} WHERE active = 1 ORDER BY email`
  ).all();
  return rows.map((r) => ({ email: r.email, display_name: r.display_name || null }));
}

/**
 * Record delivery status for one recipient.
 * @param {import('better-sqlite3').Database} db
 * @param {{ reportId: string, recipientEmail: string, status: 'Sent' | 'Not Sent' | 'Error', sentAt?: string, errorMessage?: string }} data
 */
function upsertDeliveryStatus(db, data) {
  const sentAt = data.sentAt || (data.status === 'Sent' ? new Date().toISOString() : null);
  db.prepare(
    `INSERT INTO ${DELIVERY_STATUS_TABLE} (report_id, recipient_email, status, sent_at, error_message)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(report_id, recipient_email) DO UPDATE SET
       status = excluded.status,
       sent_at = excluded.sent_at,
       error_message = excluded.error_message`
  ).run(
    data.reportId,
    data.recipientEmail,
    data.status,
    sentAt,
    data.errorMessage ?? null
  );
}

/**
 * Add a recipient (for CLI or UI).
 * @param {import('better-sqlite3').Database} db
 * @param {{ email: string, displayName?: string }} data
 */
function addRecipient(db, data) {
  const now = new Date().toISOString();
  db.prepare(
    `INSERT INTO ${RECIPIENTS_TABLE} (email, display_name, active, created_at, updated_at)
     VALUES (?, ?, 1, ?, ?)
     ON CONFLICT(email) DO UPDATE SET display_name = excluded.display_name, updated_at = excluded.updated_at`
  ).run(data.email, data.displayName || null, now, now);
}

/**
 * Deactivate a recipient by email (stop sending future emails to this address).
 * @param {import('better-sqlite3').Database} db
 * @param {string} email
 */
function deactivateRecipient(db, email) {
  const now = new Date().toISOString();
  db.prepare(
    `UPDATE ${RECIPIENTS_TABLE}
     SET active = 0, updated_at = ?
     WHERE email = ?`
  ).run(now, email);
}

export {
  openDb,
  getReportMetadata,
  getActiveRecipients,
  upsertDeliveryStatus,
  addRecipient,
  deactivateRecipient,
  REPORT_METADATA_TABLE,
  RECIPIENTS_TABLE,
  DELIVERY_STATUS_TABLE,
};
