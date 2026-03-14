/**
 * Phase 4 Report Generation configuration.
 * Reads analysis from same DB as P1–P3; writes report_metadata and report artifact to storage.
 * Uses Gemini for composing the one-pager. Loads .env from repo root.
 */
import path from 'path';
import { fileURLToPath } from 'url';
import { config as loadEnv } from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
loadEnv({ path: path.join(__dirname, '..', '.env') });

const defaultDbPath = path.join(__dirname, '..', 'phase-1-ingest', 'data', 'product-pulse.db');
const defaultReportsDir = path.join(__dirname, 'reports');

export default {
  dbPath: process.env.P4_DB_PATH || defaultDbPath,
  /** Directory for generated report HTML files (object storage). */
  reportsDir: process.env.P4_REPORTS_DIR || defaultReportsDir,
  geminiApiKey: process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '',
  geminiModel: process.env.P4_GEMINI_MODEL || 'gemini-2.5-flash',
  /** Max words for the one-pager. */
  maxWords: parseInt(process.env.P4_MAX_WORDS || '400', 10),
};
