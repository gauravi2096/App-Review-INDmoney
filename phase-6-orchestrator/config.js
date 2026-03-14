/**
 * Phase 6 Orchestrator configuration.
 * Exposes a lightweight API for UI + a weekly scheduler that runs the full pipeline.
 * Loads .env from repo root for DB path and cron config.
 */
import path from 'path';
import { fileURLToPath } from 'url';
import { config as loadEnv } from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
loadEnv({ path: path.join(__dirname, '..', '.env') });

const defaultDbPath = path.join(__dirname, '..', 'phase-1-ingest', 'data', 'product-pulse.db');

export default {
  dbPath: process.env.P6_DB_PATH || defaultDbPath,
  /** Cron expression for weekly run (default: Monday 09:00 server time). Set P6_DISABLE_CRON=true when using GitHub Actions to trigger. */
  weeklyCron: process.env.P6_DISABLE_CRON === 'true' ? '' : (process.env.P6_WEEKLY_CRON || '0 9 * * 1'),
  /** Port for the Phase 6 API server. */
  port: parseInt(process.env.P6_PORT || '4006', 10),
};

