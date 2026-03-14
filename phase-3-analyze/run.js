#!/usr/bin/env node
/**
 * Phase 3 LLM Analysis: read cleaned_reviews, batch by token limit, call LLM per batch,
 * synthesize to final 3–5 themes / 3 quotes / 3 action ideas, persist.
 *
 * Usage: node run.js [run_id]
 * Env: P3_DB_PATH, P3_GROQ_TOKEN_LIMIT, P3_BATCH_TOKEN_LIMIT, GROQ_API_KEY, GEMINI_API_KEY
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import config from './config.js';
import { openDb, getCleanedReviews, upsertAnalysis, getLatestAnalysis } from './db.js';
import { estimateTokens } from './tokenEstimator.js';
import { buildPrompt } from './promptBuilder.js';
import { buildSynthesisPrompt } from './synthesisPromptBuilder.js';
import { parseResponse, normalizeActionIdea } from './responseParser.js';
import { complete } from './llmClient.js';
import { splitReviewsIntoBatches } from './batcher.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function run() {
  const runIdArg = process.argv[2];
  const dbPath = config.dbPath;

  console.log('Phase 3 Analyze starting');
  console.log('  dbPath:', dbPath);
  if (runIdArg) console.log('  runId:', runIdArg);

  const db = openDb(dbPath);
  const reviews = getCleanedReviews(db, runIdArg ? { runId: runIdArg } : {});

  if (reviews.length === 0) {
    console.log('  No cleaned reviews to analyze. Run Phase 2 clean first.');
    db.close();
    return { runId: null, analyzed: false };
  }

  const runId = reviews[0].run_id;
  console.log('  Cleaned reviews to analyze:', reviews.length, '(run_id:', runId + ')');

  if (!config.groqApiKey) {
    console.error('  Phase 3 uses Groq only. Set GROQ_API_KEY in .env.');
    db.close();
    process.exitCode = 1;
    return { runId, analyzed: false };
  }

  const batches = splitReviewsIntoBatches(reviews, config.batchTokenLimit);
  console.log('  Batches:', batches.length, '(batch token limit:', config.batchTokenLimit + ')');
  console.log('  Provider: groq (Phase 3 uses Groq only)');

  const delay = (ms) => new Promise((r) => setTimeout(r, ms));
  const maxRetries = 4;
  const batchResults = [];
  for (let i = 0; i < batches.length; i++) {
    if (i > 0 && config.batchDelayMs > 0) {
      console.log('  Waiting', config.batchDelayMs, 'ms before next batch...');
      await delay(config.batchDelayMs);
    }
    const batch = batches[i];
    const prompt = buildPrompt(batch);
    let raw;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        raw = await complete('groq', prompt, config);
        break;
      } catch (err) {
        const is429 = err.message && err.message.includes('429');
        const waitMatch = err.message && err.message.match(/try again in (\d+(?:\.\d+)?)\s*s/i);
        const waitSec = waitMatch ? Math.ceil(parseFloat(waitMatch[1])) + 2 : 25;
        if (is429 && attempt < maxRetries) {
          console.warn('  Batch', i + 1, 'rate limited; waiting', waitSec, 's then retry', attempt + 1 + '/', maxRetries);
          await delay(waitSec * 1000);
        } else {
          console.error('  Batch', i + 1, 'LLM failed:', err.message);
          db.close();
          throw err;
        }
      }
    }
    const parsed = parseResponse(raw);
    if (parsed) batchResults.push(parsed);
    else console.warn('  Batch', i + 1, 'parse failed; skipping.');
  }

  if (batchResults.length === 0) {
    console.error('  No valid batch results.');
    db.close();
    throw new Error('No valid batch results');
  }

  let analysis;
  if (batchResults.length === 1) {
    analysis = batchResults[0];
  } else {
    const synthesisPrompt = buildSynthesisPrompt(batchResults);
    console.log('  Synthesis: groq');
    let rawSynthesis;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        rawSynthesis = await complete('groq', synthesisPrompt, config);
        break;
      } catch (err) {
        const is429 = err.message && err.message.includes('429');
        const waitMatch = err.message && err.message.match(/try again in (\d+(?:\.\d+)?)\s*s/i);
        const waitSec = waitMatch ? Math.ceil(parseFloat(waitMatch[1])) + 2 : 25;
        if (is429 && attempt < maxRetries) {
          console.warn('  Synthesis rate limited; waiting', waitSec, 's then retry', attempt + 1 + '/', maxRetries);
          await delay(waitSec * 1000);
        } else {
          db.close();
          throw err;
        }
      }
    }
    analysis = parseResponse(rawSynthesis);
    if (!analysis) {
      console.error('  Synthesis response parse failed.');
      db.close();
      throw new Error('Invalid synthesis response format');
    }
  }

  upsertAnalysis(db, runId, analysis);
  console.log('  Themes:', analysis.themes.length);
  console.log('  Quotes:', analysis.quotes.length);
  console.log('  Action ideas:', analysis.actionIdeas.length);

  const latest = getLatestAnalysis(db);
  db.close();
  if (latest) {
    const actionIdeas = (latest.actionIdeas || []).map((a) =>
      typeof a === 'string' ? a : normalizeActionIdea(a)
    );
    const toExport = { ...latest, actionIdeas };
    const exportPath = path.join(__dirname, 'phase3-analysis.json');
    fs.writeFileSync(exportPath, JSON.stringify(toExport, null, 2), 'utf8');
    console.log('  Exported to', exportPath);
  }

  console.log('Phase 3 Analyze finished.');
  return { runId, analyzed: true, analysis };
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === __filename;
if (isMain) {
  run().catch((err) => {
    console.error('Phase 3 Analyze failed:', err);
    process.exit(1);
  });
}

export { run };
