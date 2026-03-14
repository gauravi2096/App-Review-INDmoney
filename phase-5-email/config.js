/**
 * Phase 5 Email Send configuration.
 * Reads report metadata and report body (from P4 storage); reads recipients from DB; writes delivery status.
 * Loads .env from repo root for SMTP / email provider settings.
 */
import path from 'path';
import { fileURLToPath } from 'url';
import { config as loadEnv } from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
loadEnv({ path: path.join(__dirname, '..', '.env') });

const defaultDbPath = path.join(__dirname, '..', 'phase-1-ingest', 'data', 'product-pulse.db');
const defaultReportsDir = path.join(__dirname, '..', 'phase-4-report', 'reports');

export default {
  dbPath: process.env.P5_DB_PATH || defaultDbPath,
  /** Directory where P4 writes report HTML (object storage). */
  reportsDir: process.env.P5_REPORTS_DIR || defaultReportsDir,
  /** Email sender (From). */
  fromAddress: process.env.P5_FROM_ADDRESS || process.env.EMAIL_FROM || 'product-pulse@localhost',
  replyTo: process.env.P5_REPLY_TO || process.env.EMAIL_REPLY_TO || '',
  /** SMTP: use P5_SMTP_URL (e.g. smtp://user:pass@smtp.example.com:587) or individual vars. */
  smtpUrl: process.env.P5_SMTP_URL || process.env.SMTP_URL || '',
  smtpHost: process.env.P5_SMTP_HOST || process.env.SMTP_HOST || 'localhost',
  smtpPort: parseInt(process.env.P5_SMTP_PORT || process.env.SMTP_PORT || '1025', 10),
  smtpSecure: process.env.P5_SMTP_SECURE === 'true' || process.env.SMTP_SECURE === 'true',
  smtpUser: process.env.P5_SMTP_USER || process.env.SMTP_USER || '',
  smtpPass: process.env.P5_SMTP_PASS || process.env.SMTP_PASS || '',
  /** Subject line template: %(week_start_date) is replaced. */
  subjectTemplate: process.env.P5_SUBJECT_TEMPLATE || 'INDmoney Product Pulse – %(week_start_date)',
};
