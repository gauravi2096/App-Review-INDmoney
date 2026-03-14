#!/usr/bin/env node
/**
 * Phase 2 Clean job: read raw_reviews from DB, normalize text/dates, anonymize,
 * enforce schema, write to cleaned_reviews table.
 *
 * Usage: node run.js [run_id]
 * If run_id omitted, cleans the latest ingestion run.
 * Env: P2_DB_PATH (default: ../phase-1-ingest/data/product-pulse.db)
 */

import path from 'path';
import { fileURLToPath } from 'url';
import config from './config.js';
import { openDb, getRawReviews, deleteCleanedByRunId, insertCleanedReviews, getCleanedCount } from './db.js';
import { normalizeText } from './textNormalizer.js';
import { normalizeDate } from './dateNormalizer.js';
import { anonymize } from './anonymizer.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function run() {
  const runIdArg = process.argv[2];
  const dbPath = config.dbPath;

  console.log('Phase 2 Clean starting');
  console.log('  dbPath:', dbPath);
  if (runIdArg) console.log('  runId:', runIdArg);

  const db = openDb(dbPath);
  const raw = getRawReviews(db, runIdArg ? { runId: runIdArg } : {});
  if (raw.length === 0) {
    console.log('  No raw reviews to clean. Run Phase 1 ingest first.');
    db.close();
    return { runId: null, cleaned: 0 };
  }

  const runId = raw[0].run_id;
  console.log('  Raw reviews to clean:', raw.length, '(run_id:', runId + ')');

  const cleaned = [];
  let dropped = 0;

  for (const r of raw) {
    const textNorm = normalizeText(r.text);
    const textAnon = anonymize(textNorm);
    const dateNorm = normalizeDate(r.date);

    const rating = r.rating != null && Number.isInteger(Number(r.rating)) && r.rating >= 1 && r.rating <= 5
      ? Number(r.rating)
      : null;

    if (dateNorm == null || textAnon === '' || rating == null) {
      dropped += 1;
      continue;
    }

    cleaned.push({
      raw_review_id: r.id,
      rating,
      text: textAnon,
      date: dateNorm,
      run_id: r.run_id,
    });
  }

  if (dropped > 0) {
    console.log('  Dropped', dropped, 'rows (invalid date or empty text after normalize)');
  }

  deleteCleanedByRunId(db, runId);
  insertCleanedReviews(db, cleaned);
  const count = getCleanedCount(db, runId);
  console.log('  Cleaned rows persisted:', count, '(run_id:', runId + ')');
  db.close();

  console.log('Phase 2 Clean finished.');
  return { runId, cleaned: count };
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === __filename;
if (isMain) {
  run().catch((err) => {
    console.error('Phase 2 Clean failed:', err);
    process.exit(1);
  });
}

export { run };
