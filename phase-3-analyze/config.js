/**
 * Phase 3 LLM Analysis configuration.
 * Reads cleaned_reviews from same DB as P1/P2; writes analysis table.
 * Loads .env from repo root so GROQ_API_KEY etc. are available.
 */
import path from 'path';
import { fileURLToPath } from 'url';
import { config as loadEnv } from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
loadEnv({ path: path.join(__dirname, '..', '.env') });

const defaultDbPath = path.join(__dirname, '..', 'phase-1-ingest', 'data', 'product-pulse.db');

export default {
  dbPath: process.env.P3_DB_PATH || defaultDbPath,
  /** Use Groq if estimated tokens below this; else Gemini. */
  groqTokenLimit: parseInt(process.env.P3_GROQ_TOKEN_LIMIT || '6000', 10),
  /** Max tokens per batch prompt (reviews split to stay under this). */
  batchTokenLimit: parseInt(process.env.P3_BATCH_TOKEN_LIMIT || '4000', 10),
  /** Delay in ms between batch LLM calls (avoid rate limit). */
  batchDelayMs: parseInt(process.env.P3_BATCH_DELAY_MS || '15000', 10),
  groqApiKey: process.env.GROQ_API_KEY || '',
  groqModel: process.env.P3_GROQ_MODEL || 'llama-3.1-8b-instant',
  geminiApiKey: process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '',
  geminiModel: process.env.P3_GEMINI_MODEL || 'gemini-2.0-flash',
};
