/**
 * Database layer for Phase 1: raw_reviews table.
 * Schema: rating, text, date, run_id, ingested_at.
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const TABLE = 'raw_reviews';

/**
 * Ensure directory for dbPath exists, then open DB and create table if needed.
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
    CREATE TABLE IF NOT EXISTS ${TABLE} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      rating INTEGER NOT NULL,
      text TEXT NOT NULL,
      date TEXT NOT NULL,
      run_id TEXT NOT NULL,
      ingested_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_raw_reviews_run_id ON ${TABLE}(run_id);
    CREATE INDEX IF NOT EXISTS idx_raw_reviews_date ON ${TABLE}(date);
  `);
  return db;
}

/**
 * Insert a batch of validated raw reviews for a run.
 * @param {import('better-sqlite3').Database} db
 * @param {string} runId
 * @param {Array<{ rating: number, text: string, date: string }>} reviews
 */
function insertRawReviews(db, runId, reviews) {
  const ingestedAt = new Date().toISOString();
  const stmt = db.prepare(
    `INSERT INTO ${TABLE} (rating, text, date, run_id, ingested_at) VALUES (?, ?, ?, ?, ?)`
  );
  const insertMany = db.transaction((rows) => {
    for (const r of rows) {
      stmt.run(r.rating, r.text, r.date, runId, ingestedAt);
    }
  });
  insertMany(reviews);
}

/**
 * Get count of rows for a run_id (optional).
 * @param {import('better-sqlite3').Database} db
 * @param {string} [runId]
 * @returns {number}
 */
function getRawReviewCount(db, runId) {
  if (runId) {
    const row = db.prepare(`SELECT COUNT(*) as c FROM ${TABLE} WHERE run_id = ?`).get(runId);
    return row.c;
  }
  const row = db.prepare(`SELECT COUNT(*) as c FROM ${TABLE}`).get();
  return row.c;
}

/**
 * List raw reviews for viewing (e.g. CLI). Latest first.
 * @param {import('better-sqlite3').Database} db
 * @param {{ limit?: number }} [opts]
 * @returns {Array<{ id: number, rating: number, text: string, date: string, run_id: string, ingested_at: string }>}
 */
function getRawReviews(db, opts = {}) {
  const limit = Math.min(Math.max(0, opts.limit ?? 100), 1000);
  return db.prepare(
    `SELECT id, rating, text, date, run_id, ingested_at FROM ${TABLE} ORDER BY date DESC, id DESC LIMIT ?`
  ).all(limit);
}

export { openDb, insertRawReviews, getRawReviewCount, getRawReviews, TABLE };
