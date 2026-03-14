#!/usr/bin/env node
/**
 * Phase 1 Ingest job: fetch INDmoney reviews via google-play-scraper,
 * filter to last 8–12 weeks, validate, persist to raw_reviews table.
 *
 * Usage: node run.js
 * Env: P1_APP_ID, P1_LANG, P1_COUNTRY, P1_DATE_WINDOW_WEEKS, P1_DB_PATH, P1_PAGINATION_DELAY_MS, P1_MAX_RETRIES, P1_RETRY_DELAY_MS
 */

import path from 'path';
import { fileURLToPath } from 'url';
import open from 'open';
import config from './config.js';
import { fetchAllReviews } from './reviewFetcher.js';
import { filterByDateWindow } from './dateFilter.js';
import { filterEnglish } from './languageFilter.js';
import { validateReviews } from './validator.js';
import { openDb, insertRawReviews, getRawReviewCount } from './db.js';
import { exportReviewsToFile } from './export-reviews.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REVIEWS_JSON_PATH = path.join(__dirname, 'reviews.json');

function generateRunId() {
  return `run_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

async function run() {
  const runId = generateRunId();
  const dbPath = config.dbPath;

  console.log('Phase 1 Ingest starting');
  console.log('  appId:', config.appId);
  console.log('  lang:', config.lang, 'country:', config.country);
  console.log('  dateWindowWeeks:', config.dateWindowWeeks);
  console.log('  runId:', runId);
  console.log('  dbPath:', dbPath);
  console.log('  paginationDelayMs:', config.paginationDelayMs, 'maxRetries:', config.maxRetries);

  const fetched = await fetchAllReviews({
    appId: config.appId,
    lang: config.lang,
    country: config.country,
    paginationDelayMs: config.paginationDelayMs,
    maxRetries: config.maxRetries,
    retryDelayMs: config.retryDelayMs,
  });
  console.log('  Fetched', fetched.length, 'reviews from Play Store');

  const filtered = filterByDateWindow(fetched, config.dateWindowWeeks);
  console.log('  After date filter (last', config.dateWindowWeeks, 'weeks):', filtered.length);

  const { filtered: englishOnly, droppedCount: nonEnglishCount } = filterEnglish(filtered);
  if (nonEnglishCount > 0) {
    console.log('  Dropped', nonEnglishCount, 'non-English reviews');
  }
  console.log('  After English filter:', englishOnly.length);

  const { valid, invalidCount } = validateReviews(englishOnly);
  if (invalidCount > 0) {
    console.log('  Dropped', invalidCount, 'invalid rows');
  }
  console.log('  Valid rows to persist:', valid.length);

  if (valid.length === 0) {
    const exported = exportReviewsToFile(dbPath, REVIEWS_JSON_PATH);
    console.log('  Exported', exported, 'reviews to', REVIEWS_JSON_PATH);
    try {
      await open(REVIEWS_JSON_PATH);
    } catch (e) {
      console.log('  (Could not open reviews.json in editor:', e.message + ')');
    }
    console.log('Phase 1 Ingest finished: no rows to persist.');
    return { runId, persisted: 0 };
  }

  const db = openDb(dbPath);
  try {
    insertRawReviews(db, runId, valid);
    const count = getRawReviewCount(db, runId);
    console.log('  Persisted', count, 'rows to raw_reviews (run_id:', runId + ')');
  } finally {
    db.close();
  }

  const exported = exportReviewsToFile(dbPath, REVIEWS_JSON_PATH);
  console.log('  Exported', exported, 'reviews to', REVIEWS_JSON_PATH);
  try {
    await open(REVIEWS_JSON_PATH);
  } catch (e) {
    console.log('  (Could not open reviews.json in editor:', e.message + ')');
  }
  console.log('Phase 1 Ingest finished.');
  return { runId, persisted: valid.length };
}

const __filename = fileURLToPath(import.meta.url);
const isMain = process.argv[1] && path.resolve(process.argv[1]) === __filename;
if (isMain) {
  run().catch((err) => {
    console.error('Phase 1 Ingest failed:', err);
    process.exit(1);
  });
}

export { run };
