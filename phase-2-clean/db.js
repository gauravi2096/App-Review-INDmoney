/**
 * Database layer for Phase 2: read raw_reviews, write cleaned_reviews.
 * Uses the same DB file as Phase 1 (product-pulse.db).
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const RAW_TABLE = 'raw_reviews';
const CLEANED_TABLE = 'cleaned_reviews';

/**
 * Open DB and ensure cleaned_reviews table exists.
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
    CREATE TABLE IF NOT EXISTS ${CLEANED_TABLE} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      raw_review_id INTEGER NOT NULL,
      rating INTEGER NOT NULL,
      text TEXT NOT NULL,
      date TEXT NOT NULL,
      run_id TEXT NOT NULL,
      cleaned_at TEXT NOT NULL,
      FOREIGN KEY (raw_review_id) REFERENCES ${RAW_TABLE}(id)
    );
    CREATE INDEX IF NOT EXISTS idx_cleaned_reviews_run_id ON ${CLEANED_TABLE}(run_id);
    CREATE INDEX IF NOT EXISTS idx_cleaned_reviews_date ON ${CLEANED_TABLE}(date);
  `);
  return db;
}

/**
 * Get raw reviews from the database, optionally for the latest run only.
 * @param {import('better-sqlite3').Database} db
 * @param {{ runId?: string }} [opts] - If runId omitted, uses latest run by ingested_at.
 * @returns {Array<{ id: number, rating: number, text: string, date: string, run_id: string, ingested_at: string }>}
 */
function getRawReviews(db, opts = {}) {
  if (opts.runId) {
    return db.prepare(
      `SELECT id, rating, text, date, run_id, ingested_at FROM ${RAW_TABLE} WHERE run_id = ? ORDER BY date DESC, id DESC`
    ).all(opts.runId);
  }
  const latest = db.prepare(
    `SELECT run_id FROM ${RAW_TABLE} ORDER BY ingested_at DESC LIMIT 1`
  ).get();
  if (!latest) return [];
  return db.prepare(
    `SELECT id, rating, text, date, run_id, ingested_at FROM ${RAW_TABLE} WHERE run_id = ? ORDER BY date DESC, id DESC`
  ).all(latest.run_id);
}

/**
 * Delete existing cleaned reviews for a run (so we can overwrite).
 * @param {import('better-sqlite3').Database} db
 * @param {string} runId
 */
function deleteCleanedByRunId(db, runId) {
  db.prepare(`DELETE FROM ${CLEANED_TABLE} WHERE run_id = ?`).run(runId);
}

/**
 * Insert cleaned reviews for a run.
 * @param {import('better-sqlite3').Database} db
 * @param {Array<{ raw_review_id: number, rating: number, text: string, date: string, run_id: string }>} rows
 */
function insertCleanedReviews(db, rows) {
  const cleanedAt = new Date().toISOString();
  const stmt = db.prepare(
    `INSERT INTO ${CLEANED_TABLE} (raw_review_id, rating, text, date, run_id, cleaned_at) VALUES (?, ?, ?, ?, ?, ?)`
  );
  const insertMany = db.transaction((list) => {
    for (const r of list) {
      stmt.run(r.raw_review_id, r.rating, r.text, r.date, r.run_id, cleanedAt);
    }
  });
  insertMany(rows);
}

/**
 * Get count of cleaned reviews, optionally for a run_id.
 * @param {import('better-sqlite3').Database} db
 * @param {string} [runId]
 * @returns {number}
 */
function getCleanedCount(db, runId) {
  if (runId) {
    const row = db.prepare(`SELECT COUNT(*) as c FROM ${CLEANED_TABLE} WHERE run_id = ?`).get(runId);
    return row.c;
  }
  const row = db.prepare(`SELECT COUNT(*) as c FROM ${CLEANED_TABLE}`).get();
  return row.c;
}

export { openDb, getRawReviews, deleteCleanedByRunId, insertCleanedReviews, getCleanedCount, CLEANED_TABLE, RAW_TABLE };
