/**
 * Simple CLI to view fetched reviews from raw_reviews table.
 * Usage: node view-reviews.js [limit]
 * Limit defaults to 50; max 500. Set P1_DB_PATH to use another DB.
 */

import config from './config.js';
import { openDb, getRawReviewCount, getRawReviews } from './db.js';

const limit = Math.min(500, Math.max(1, parseInt(process.argv[2] || '50', 10)));

const db = openDb(config.dbPath);
const total = getRawReviewCount(db);
const reviews = getRawReviews(db, { limit });

console.log(`raw_reviews: ${total} total, showing latest ${reviews.length}\n`);

if (reviews.length === 0) {
  console.log('No reviews in DB. Run: npm run ingest');
  process.exit(0);
}

for (const r of reviews) {
  const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
  console.log('─'.repeat(60));
  console.log(`#${r.id}  ${stars}  ${r.date}  (run: ${r.run_id})`);
  console.log(r.text || '(no text)');
  console.log('');
}

db.close();
