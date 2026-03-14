#!/usr/bin/env node
/**
 * Phase 6: Orchestrator + lightweight API for UI.
 *
 * Features:
 * - GET /api/reports             – list reports
 * - GET /api/reports/:id         – report metadata
 * - GET /api/reports/:id/html    – HTML body
 * - GET /api/reports/:id/delivery – per-recipient delivery status
 * - GET /api/recipients          – list recipients
 * - POST /api/pipeline/run       – trigger full P1→P5 pipeline once
 *
 * Also starts a weekly cron job (configurable via P6_WEEKLY_CRON) to run the pipeline.
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import cron from 'node-cron';
import config from './config.js';
import {
  openDb,
  listReports,
  getReport,
  getDeliveryStatus,
  listRecipients,
  getDeliverySummaryPerReport,
  addRecipient,
  getRecipientById,
  updateRecipient,
  deactivateRecipientById,
} from './db.js';
import { runWeeklyPipeline } from './pipeline.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json());

const publicDir = path.join(__dirname, 'public');
const indexPath = path.join(publicDir, 'index.html');

function sendDashboard(_req, res) {
  res.type('html').sendFile(indexPath);
}

// API routes first so /api/* is never treated as dashboard
// Simple health check
app.get('/api/health', (_req, res) => {
  res.json({ ok: true, phase: 6 });
});

// List reports with delivery summary (sent, failed, not_sent per report)
app.get('/api/reports', (_req, res) => {
  const db = openDb(config.dbPath);
  try {
    const reports = listReports(db);
    const summaryMap = getDeliverySummaryPerReport(db);
    const withSummary = reports.map((r) => ({
      ...r,
      delivery_summary: summaryMap[r.report_id] || { sent: 0, failed: 0, not_sent: 0 },
    }));
    res.json(withSummary);
  } finally {
    db.close();
  }
});

// Single report metadata
app.get('/api/reports/:id', (req, res) => {
  const db = openDb(config.dbPath);
  try {
    const report = getReport(db, req.params.id);
    if (!report) return res.status(404).json({ error: 'Report not found' });
    res.json(report);
  } finally {
    db.close();
  }
});

// Report HTML body (for UI embedding)
app.get('/api/reports/:id/html', (req, res) => {
  const reportId = req.params.id;
  const reportsDir = path.join(path.dirname(config.dbPath), '..', 'phase-4-report', 'reports');
  const filePath = path.join(reportsDir, `${reportId}.html`);
  if (!fs.existsSync(filePath)) {
    return res.status(404).send('Report HTML not found');
  }
  res.type('html').send(fs.readFileSync(filePath, 'utf8'));
});

// Delivery status for a report
app.get('/api/reports/:id/delivery', (req, res) => {
  const db = openDb(config.dbPath);
  try {
    const rows = getDeliveryStatus(db, req.params.id);
    res.json(rows);
  } finally {
    db.close();
  }
});

// Recipients
app.get('/api/recipients', (_req, res) => {
  const db = openDb(config.dbPath);
  try {
    const rows = listRecipients(db);
    res.json(rows);
  } finally {
    db.close();
  }
});

app.post('/api/recipients', (req, res) => {
  const { email, display_name } = req.body || {};
  if (!email || typeof email !== 'string' || !email.trim()) {
    return res.status(400).json({ error: 'email is required' });
  }
  const db = openDb(config.dbPath);
  try {
    addRecipient(db, { email: email.trim(), display_name: display_name != null ? String(display_name).trim() || null : null });
    const rows = listRecipients(db);
    const added = rows.find((r) => r.email === email.trim());
    res.status(201).json(added || { email: email.trim(), display_name: display_name || null });
  } catch (err) {
    if (err.message && err.message.includes('UNIQUE')) return res.status(409).json({ error: 'Email already exists' });
    throw err;
  } finally {
    db.close();
  }
});

app.patch('/api/recipients/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (Number.isNaN(id)) return res.status(400).json({ error: 'Invalid id' });
  const { email, display_name } = req.body || {};
  const db = openDb(config.dbPath);
  try {
    const ok = updateRecipient(db, id, {
      ...(email !== undefined && { email: String(email).trim() }),
      ...(display_name !== undefined && { display_name: display_name === '' ? null : String(display_name).trim() }),
    });
    if (!ok) return res.status(404).json({ error: 'Recipient not found' });
    const updated = getRecipientById(db, id);
    res.json(updated);
  } finally {
    db.close();
  }
});

app.delete('/api/recipients/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (Number.isNaN(id)) return res.status(400).json({ error: 'Invalid id' });
  const db = openDb(config.dbPath);
  try {
    const ok = deactivateRecipientById(db, id);
    if (!ok) return res.status(404).json({ error: 'Recipient not found' });
    res.status(204).send();
  } finally {
    db.close();
  }
});

// Trigger pipeline once (manual run; dashboard does not expose this)
app.post('/api/pipeline/run', async (_req, res) => {
  try {
    await runWeeklyPipeline();
    res.json({ ok: true });
  } catch (err) {
    console.error('[Phase 6] Pipeline run failed:', err);
    res.status(500).json({ error: err.message || String(err) });
  }
});

// Dashboard frontend: serve static files from public/, then map / and /dashboard to index.html, then SPA fallback
app.use(express.static(publicDir, { index: false }));
app.get('/', sendDashboard);
app.get('/dashboard', sendDashboard);
app.get('/dashboard/', sendDashboard);
app.use((req, res, next) => {
  if (req.method !== 'GET' || req.path.startsWith('/api')) return next();
  sendDashboard(req, res);
});

// Schedule weekly pipeline
if (config.weeklyCron) {
  cron.schedule(config.weeklyCron, () => {
    console.log('[Phase 6] Weekly cron triggered:', config.weeklyCron);
    runWeeklyPipeline().catch((err) => {
      console.error('[Phase 6] Weekly pipeline failed:', err);
    });
  });
}

app.listen(config.port, () => {
  console.log(`Phase 6 orchestrator listening on http://localhost:${config.port}`);
  console.log('  Dashboard:        GET / (and static files from public/)');
  console.log('  Health:           GET /api/health');
  console.log('  Reports list:     GET /api/reports (includes delivery_summary)');
  console.log('  Report metadata:  GET /api/reports/:id');
  console.log('  Report HTML:      GET /api/reports/:id/html');
  console.log('  Delivery status:  GET /api/reports/:id/delivery');
  console.log('  Recipients:       GET /api/recipients');
  console.log('  Add recipient:    POST /api/recipients');
  console.log('  Edit recipient:   PATCH /api/recipients/:id');
  console.log('  Delete recipient: DELETE /api/recipients/:id');
});

