/**
 * Phase 1 Ingest configuration.
 * INDmoney app ID from Play Store: in.indwealth
 */
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default {
  appId: process.env.P1_APP_ID || 'in.indwealth',
  lang: process.env.P1_LANG || 'en',
  country: process.env.P1_COUNTRY || 'in',
  /** Number of weeks to include (last N weeks). Architecture: 8–12 weeks. */
  dateWindowWeeks: parseInt(process.env.P1_DATE_WINDOW_WEEKS || '12', 10),
  /** Database path. Default: local file in phase-1-ingest/data. */
  dbPath: process.env.P1_DB_PATH || path.join(__dirname, 'data', 'product-pulse.db'),
  /** Delay in ms between pagination requests to reduce rate limiting. */
  paginationDelayMs: parseInt(process.env.P1_PAGINATION_DELAY_MS || '1500', 10),
  /** Max retries per Play Store request on transient errors (e.g. ECONNRESET). */
  maxRetries: parseInt(process.env.P1_MAX_RETRIES || '3', 10),
  /** Delay in ms before first retry; doubles each attempt (exponential backoff). */
  retryDelayMs: parseInt(process.env.P1_RETRY_DELAY_MS || '3000', 10),
};
