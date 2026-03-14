#!/usr/bin/env node
/**
 * Phase 4: Generate weekly one-pager report from latest (or specified) analysis.
 * Uses Gemini to compose narrative; writes HTML to storage and report_metadata to DB.
 *
 * Usage:
 *   node run.js           # report from latest analysis
 *   node run.js <run_id>  # report for specific analysis run
 */

import fs from 'fs';
import path from 'path';
import config from './config.js';
import { openDb, getLatestAnalysis, getAnalysis, getReviewStatsForRun, insertReportMetadata } from './db.js';
import { composeOnePager } from './composer.js';
import { countWords, truncateToWordCount } from './wordCounter.js';
import { textToHtml, textToMarkdown } from './renderer.js';

async function main() {
  const runIdArg = process.argv[2] || null;

  if (!config.geminiApiKey) {
    console.error('Missing GEMINI_API_KEY. Add it to the repo root .env file.');
    process.exit(1);
  }

  const db = openDb(config.dbPath);

  let analysis;
  let runId;
  let analyzedAt;

  if (runIdArg) {
    const forRun = db.prepare('SELECT run_id, analyzed_at FROM analysis WHERE run_id = ?').get(runIdArg);
    if (!forRun) {
      console.error('No analysis found for run_id:', runIdArg);
      process.exit(1);
    }
    analysis = getAnalysis(db, runIdArg);
    runId = runIdArg;
    analyzedAt = forRun.analyzed_at;
  } else {
    const latest = getLatestAnalysis(db);
    if (!latest) {
      console.error('No analysis found in DB. Run Phase 3 first.');
      process.exit(1);
    }
    analysis = latest;
    runId = latest.run_id;
    analyzedAt = latest.analyzed_at;
  }

  if (!analysis.themes?.length && !(analysis.quotes?.length) && !(analysis.actionIdeas?.length)) {
    console.error('Analysis has no themes, quotes, or action ideas. Nothing to report.');
    process.exit(1);
  }

  const reviewStats = getReviewStatsForRun(db, runId);
  const reportContext = {
    totalReviews: reviewStats.totalReviews,
    dateMin: reviewStats.dateMin,
    dateMax: reviewStats.dateMax,
  };

  console.log('Composing one-pager with Gemini for run:', runId);
  let bodyText = await composeOnePager(analysis, config, reportContext);

  let wordCount = countWords(bodyText);
  if (wordCount > config.maxWords) {
    const { text, truncated } = truncateToWordCount(bodyText, config.maxWords);
    bodyText = text;
    wordCount = countWords(text);
    if (truncated) console.log('Truncated to', config.maxWords, 'words.');
  }

  const html = textToHtml(bodyText, { title: 'Product Pulse Weekly' });

  const reportsDir = path.resolve(config.reportsDir);
  if (!fs.existsSync(reportsDir)) {
    fs.mkdirSync(reportsDir, { recursive: true });
  }

  const reportFileName = `${runId}.html`;
  const storagePath = path.join(reportsDir, reportFileName);
  fs.writeFileSync(storagePath, html, 'utf8');
  console.log('Wrote report:', storagePath);

  const md = textToMarkdown(bodyText, { title: 'Product Pulse Weekly' });
  const mdPath = path.join(reportsDir, `${runId}.md`);
  fs.writeFileSync(mdPath, md, 'utf8');
  console.log('Wrote Markdown:', mdPath);

  const weekStartDate = analyzedAt ? analyzedAt.slice(0, 10) : new Date().toISOString().slice(0, 10);
  const storageArtifactPath = path.join('reports', reportFileName);
  insertReportMetadata(db, {
    reportId: runId,
    runId,
    weekStartDate,
    wordCount,
    storagePath: storageArtifactPath,
  });
  console.log('Saved report_metadata for report_id:', runId, 'word_count:', wordCount);

  db.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
