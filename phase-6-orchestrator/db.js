/**
 * Phase 6 DB helpers: read reports, recipients, and delivery status for UI.
 * Same SQLite DB as P1–P5.
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const REPORT_METADATA_TABLE = 'report_metadata';
const RECIPIENTS_TABLE = 'recipients';
const DELIVERY_STATUS_TABLE = 'delivery_status';

/**
 * Open the shared DB (no schema changes here; tables are managed by earlier phases).
 * @param {string} dbPath
 * @returns {import('better-sqlite3').Database}
 */
export function openDb(dbPath) {
  const dir = path.dirname(dbPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return new Database(dbPath);
}

/**
 * List reports (metadata only), newest first.
 * @param {import('better-sqlite3').Database} db
 */
export function listReports(db) {
  return db
    .prepare(
      `SELECT report_id, run_id, week_start_date, report_status, word_count, generated_at, storage_artifact_path
       FROM ${REPORT_METADATA_TABLE}
       ORDER BY generated_at DESC`
    )
    .all();
}

/**
 * Get one report metadata by id.
 * @param {import('better-sqlite3').Database} db
 * @param {string} reportId
 */
export function getReport(db, reportId) {
  return db
    .prepare(
      `SELECT report_id, run_id, week_start_date, report_status, word_count, generated_at, storage_artifact_path
       FROM ${REPORT_METADATA_TABLE}
       WHERE report_id = ?`
    )
    .get(reportId);
}

/**
 * Fetch delivery status rows for a given report id.
 * @param {import('better-sqlite3').Database} db
 * @param {string} reportId
 */
export function getDeliveryStatus(db, reportId) {
  return db
    .prepare(
      `SELECT recipient_email, status, sent_at, error_message
       FROM ${DELIVERY_STATUS_TABLE}
       WHERE report_id = ?
       ORDER BY recipient_email`
    )
    .all(reportId);
}

/**
 * List all recipients.
 * @param {import('better-sqlite3').Database} db
 */
export function listRecipients(db) {
  return db
    .prepare(
      `SELECT id, email, display_name, active, created_at, updated_at
       FROM ${RECIPIENTS_TABLE}
       ORDER BY email`
    )
    .all();
}

/**
 * Per-report delivery counts: sent, failed, not_sent.
 * @param {import('better-sqlite3').Database} db
 * @returns {Record<string, { sent: number, failed: number, not_sent: number }>}
 */
export function getDeliverySummaryPerReport(db) {
  const rows = db
    .prepare(
      `SELECT report_id, status, COUNT(*) as c
       FROM ${DELIVERY_STATUS_TABLE}
       GROUP BY report_id, status`
    )
    .all();
  const map = {};
  for (const r of rows) {
    if (!map[r.report_id]) map[r.report_id] = { sent: 0, failed: 0, not_sent: 0 };
    if (r.status === 'Sent') map[r.report_id].sent = r.c;
    else if (r.status === 'Error') map[r.report_id].failed = r.c;
    else map[r.report_id].not_sent = r.c;
  }
  return map;
}

/**
 * Add a recipient (same schema as Phase 5).
 * @param {import('better-sqlite3').Database} db
 * @param {{ email: string, display_name?: string | null }} data
 */
export function addRecipient(db, data) {
  const now = new Date().toISOString();
  db.prepare(
    `INSERT INTO ${RECIPIENTS_TABLE} (email, display_name, active, created_at, updated_at)
     VALUES (?, ?, 1, ?, ?)
     ON CONFLICT(email) DO UPDATE SET display_name = excluded.display_name, active = 1, updated_at = excluded.updated_at`
  ).run(data.email, data.display_name ?? null, now, now);
}

/**
 * Get recipient by id.
 * @param {import('better-sqlite3').Database} db
 * @param {number} id
 */
export function getRecipientById(db, id) {
  return db.prepare(`SELECT id, email, display_name, active, created_at, updated_at FROM ${RECIPIENTS_TABLE} WHERE id = ?`).get(id);
}

/**
 * Update recipient email and/or display_name.
 * @param {import('better-sqlite3').Database} db
 * @param {number} id
 * @param {{ email?: string, display_name?: string | null }} data
 */
export function updateRecipient(db, id, data) {
  const now = new Date().toISOString();
  const existing = getRecipientById(db, id);
  if (!existing) return false;
  const email = data.email !== undefined ? data.email : existing.email;
  const display_name = data.display_name !== undefined ? data.display_name : existing.display_name;
  db.prepare(
    `UPDATE ${RECIPIENTS_TABLE} SET email = ?, display_name = ?, updated_at = ? WHERE id = ?`
  ).run(email, display_name, now, id);
  return true;
}

/**
 * Deactivate recipient (soft delete) so they no longer receive emails.
 * @param {import('better-sqlite3').Database} db
 * @param {number} id
 */
export function deactivateRecipientById(db, id) {
  const now = new Date().toISOString();
  const r = db.prepare(`UPDATE ${RECIPIENTS_TABLE} SET active = 0, updated_at = ? WHERE id = ?`).run(now, id);
  return r.changes > 0;
}

