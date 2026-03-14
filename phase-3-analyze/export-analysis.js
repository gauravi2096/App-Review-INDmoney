/**
 * Export the latest Phase 3 analysis to phase3-analysis.json for easy viewing in the editor.
 *
 * Usage: node export-analysis.js [output path]
 * Default output: phase3-analysis.json in this directory.
 * Uses P3_DB_PATH (same DB as analyze).
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import config from './config.js';
import { openDb, getLatestAnalysis } from './db.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const defaultPath = path.join(__dirname, 'phase3-analysis.json');
const outputPath = process.argv[2] ? path.resolve(process.cwd(), process.argv[2]) : defaultPath;

const db = openDb(config.dbPath);
const analysis = getLatestAnalysis(db);
db.close();

if (!analysis) {
  console.log('No analysis in DB. Run: npm run analyze');
  process.exit(0);
}

fs.writeFileSync(outputPath, JSON.stringify(analysis, null, 2), 'utf8');
console.log('Exported latest analysis to', outputPath);
console.log('  run_id:', analysis.run_id);
console.log('  analyzed_at:', analysis.analyzed_at);
console.log('  themes:', analysis.themes.length);
console.log('  quotes:', analysis.quotes.length);
console.log('  actionIdeas:', analysis.actionIdeas.length);
