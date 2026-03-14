/**
 * Phase 2 Clean configuration.
 * Reads raw_reviews from the same DB as Phase 1; writes cleaned_reviews.
 */
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Database path. Default: Phase 1 product-pulse.db. */
const defaultDbPath = path.join(__dirname, '..', 'phase-1-ingest', 'data', 'product-pulse.db');

export default {
  dbPath: process.env.P2_DB_PATH || defaultDbPath,
};
