/**
 * Database layer for Phase 4: read analysis, write report_metadata.
 * Same DB file as Phase 1–3 (product-pulse.db).
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const ANALYSIS_TABLE = 'analysis';
const REPORT_METADATA_TABLE = 'report_metadata';
const CLEANED_TABLE = 'cleaned_reviews';

/**
 * Open DB and ensure report_metadata table exists.
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
    CREATE TABLE IF NOT EXISTS ${REPORT_METADATA_TABLE} (
      report_id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      week_start_date TEXT NOT NULL,
      report_status TEXT NOT NULL,
      word_count INTEGER NOT NULL,
      generated_at TEXT NOT NULL,
      storage_artifact_path TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_report_metadata_run_id ON ${REPORT_METADATA_TABLE}(run_id);
  `);
  return db;
}

/**
 * Get latest analysis (by analyzed_at DESC) from analysis table.
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

/**
 * Get analysis for a given run_id.
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
 * Get total review count and date range for a run (from cleaned_reviews).
 * @param {import('better-sqlite3').Database} db
 * @param {string} runId
 * @returns {{ totalReviews: number, dateMin: string | null, dateMax: string | null }}
 */
function getReviewStatsForRun(db, runId) {
  const countRow = db.prepare(`SELECT COUNT(*) as c FROM ${CLEANED_TABLE} WHERE run_id = ?`).get(runId);
  const rangeRow = db.prepare(`SELECT MIN(date) as date_min, MAX(date) as date_max FROM ${CLEANED_TABLE} WHERE run_id = ?`).get(runId);
  return {
    totalReviews: countRow?.c ?? 0,
    dateMin: rangeRow?.date_min ?? null,
    dateMax: rangeRow?.date_max ?? null,
  };
}

/**
 * Insert report metadata after generating a report.
 * @param {import('better-sqlite3').Database} db
 * @param {{ reportId: string, runId: string, weekStartDate: string, wordCount: number, storagePath: string }} data
 */
function insertReportMetadata(db, data) {
  const generatedAt = new Date().toISOString();
  db.prepare(
    `INSERT INTO ${REPORT_METADATA_TABLE} (report_id, run_id, week_start_date, report_status, word_count, generated_at, storage_artifact_path)
     VALUES (?, ?, ?, 'generated', ?, ?, ?)
     ON CONFLICT(report_id) DO UPDATE SET
       week_start_date = excluded.week_start_date,
       report_status = excluded.report_status,
       word_count = excluded.word_count,
       generated_at = excluded.generated_at,
       storage_artifact_path = excluded.storage_artifact_path`
  ).run(data.reportId, data.runId, data.weekStartDate, data.wordCount, generatedAt, data.storagePath);
}

export { openDb, getLatestAnalysis, getAnalysis, getReviewStatsForRun, insertReportMetadata, REPORT_METADATA_TABLE };
