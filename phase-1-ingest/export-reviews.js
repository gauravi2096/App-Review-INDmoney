/**
 * Export raw reviews from product-pulse.db into a JSON file.
 *
 * Usage:
 *   node export-reviews.js              # writes ./reviews.json
 *   node export-reviews.js output.json  # custom path (resolved from CWD)
 *
 * Uses the same DB path as ingestion (config.dbPath / P1_DB_PATH).
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import config from './config.js';
import { openDb } from './db.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Export all rows from raw_reviews to a JSON file.
 * @param {string} dbPath - Path to product-pulse.db
 * @param {string} outputPath - Path for reviews.json
 * @returns {number} Number of reviews written
 */
function exportReviewsToFile(dbPath, outputPath) {
  const db = openDb(dbPath);
  try {
    const rows = db
      .prepare(
        'SELECT id, rating, text, date, run_id, ingested_at FROM raw_reviews ORDER BY date DESC, id DESC'
      )
      .all();
    fs.writeFileSync(outputPath, JSON.stringify(rows, null, 2), 'utf8');
    return rows.length;
  } finally {
    db.close();
  }
}

const argPath = process.argv[2];
const outputPath = argPath
  ? path.resolve(process.cwd(), argPath)
  : path.resolve(__dirname, 'reviews.json');

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(__dirname, 'export-reviews.js');
if (isMain) {
  try {
    const count = exportReviewsToFile(config.dbPath, outputPath);
    console.log(`Exported ${count} reviews to ${outputPath}`);
  } catch (err) {
    console.error('Failed to export reviews:', err);
    process.exitCode = 1;
  }
}

export { exportReviewsToFile };

