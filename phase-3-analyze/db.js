/**
 * Database layer for Phase 3: read cleaned_reviews, write analysis.
 * Same DB file as Phase 1 and 2 (product-pulse.db).
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const CLEANED_TABLE = 'cleaned_reviews';
const ANALYSIS_TABLE = 'analysis';

/**
 * Open DB and ensure analysis table exists.
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
    CREATE TABLE IF NOT EXISTS ${ANALYSIS_TABLE} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id TEXT NOT NULL UNIQUE,
      themes_json TEXT NOT NULL,
      quotes_json TEXT NOT NULL,
      action_ideas_json TEXT NOT NULL,
      analyzed_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_analysis_run_id ON ${ANALYSIS_TABLE}(run_id);
  `);
  return db;
}

/**
 * Get cleaned reviews for a run. If runId omitted, use latest run (by cleaned_at).
 * @param {import('better-sqlite3').Database} db
 * @param {{ runId?: string }} [opts]
 * @returns {Array<{ id: number, rating: number, text: string, date: string, run_id: string }>}
 */
function getCleanedReviews(db, opts = {}) {
  if (opts.runId) {
    return db.prepare(
      `SELECT id, rating, text, date, run_id FROM ${CLEANED_TABLE} WHERE run_id = ? ORDER BY date DESC, id DESC`
    ).all(opts.runId);
  }
  const latest = db.prepare(
    `SELECT run_id FROM ${CLEANED_TABLE} ORDER BY cleaned_at DESC LIMIT 1`
  ).get();
  if (!latest) return [];
  return db.prepare(
    `SELECT id, rating, text, date, run_id FROM ${CLEANED_TABLE} WHERE run_id = ? ORDER BY date DESC, id DESC`
  ).all(latest.run_id);
}

/**
 * Upsert analysis for a run (replace if exists).
 * @param {import('better-sqlite3').Database} db
 * @param {string} runId
 * @param {{ themes: Array<{ label: string, description: string }>, quotes: string[], actionIdeas: string[] }} data
 */
function upsertAnalysis(db, runId, data) {
  const analyzedAt = new Date().toISOString();
  const themesJson = JSON.stringify(data.themes || []);
  const quotesJson = JSON.stringify(data.quotes || []);
  const actionIdeasJson = JSON.stringify(data.actionIdeas || []);

  db.prepare(
    `INSERT INTO ${ANALYSIS_TABLE} (run_id, themes_json, quotes_json, action_ideas_json, analyzed_at)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(run_id) DO UPDATE SET
       themes_json = excluded.themes_json,
       quotes_json = excluded.quotes_json,
       action_ideas_json = excluded.action_ideas_json,
       analyzed_at = excluded.analyzed_at`
  ).run(runId, themesJson, quotesJson, actionIdeasJson, analyzedAt);
}

/**
 * Get analysis for a run_id.
 * @param {import('better-sqlite3').Database} db
 * @param {string} runId
 * @returns {{ themes: Array<{ label: string, description: string }>, quotes: string[], actionIdeas: string[] } | null}
 */
function getAnalysis(db, runId) {
  const row = db.prepare(
    `SELECT themes_json, quotes_json, action_ideas_json FROM ${ANALYSIS_TABLE} WHERE run_id = ?`
  ).get(runId);
  if (!row) return null;
  return {
    themes: JSON.parse(row.themes_json || '[]'),
    quotes: JSON.parse(row.quotes_json || '[]'),
    actionIdeas: JSON.parse(row.action_ideas_json || '[]'),
  };
}

/**
 * Get the latest analysis row (by analyzed_at DESC).
 * @param {import('better-sqlite3').Database} db
 * @returns {{ run_id: string, analyzed_at: string, themes: Array<{ label: string, description: string }>, quotes: string[], actionIdeas: string[] } | null}
 */
function getLatestAnalysis(db) {
  const row = db.prepare(
    `SELECT run_id, analyzed_at, themes_json, quotes_json, action_ideas_json FROM ${ANALYSIS_TABLE} ORDER BY analyzed_at DESC LIMIT 1`
  ).get();
  if (!row) return null;
  return {
    run_id: row.run_id,
    analyzed_at: row.analyzed_at,
    themes: JSON.parse(row.themes_json || '[]'),
    quotes: JSON.parse(row.quotes_json || '[]'),
    actionIdeas: JSON.parse(row.action_ideas_json || '[]'),
  };
}

export { openDb, getCleanedReviews, upsertAnalysis, getAnalysis, getLatestAnalysis, ANALYSIS_TABLE, CLEANED_TABLE };
