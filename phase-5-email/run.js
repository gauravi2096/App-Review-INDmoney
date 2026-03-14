#!/usr/bin/env node
/**
 * Phase 5: Send the latest (or specified) report to all active recipients.
 * Reads report body from P4 storage, recipient list from DB; records delivery status per recipient.
 *
 * Usage:
 *   node run.js           # send latest report
 *   node run.js <report_id>  # send specific report
 */

import fs from 'fs';
import path from 'path';
import config from './config.js';
import { openDb, getReportMetadata, getActiveRecipients, upsertDeliveryStatus } from './db.js';
import { sendEmail } from './emailService.js';

function formatOrdinalDay(day) {
  const d = Number(day);
  if (!Number.isFinite(d)) return String(day);
  const mod10 = d % 10;
  const mod100 = d % 100;
  let suffix = 'th';
  if (mod10 === 1 && mod100 !== 11) suffix = 'st';
  else if (mod10 === 2 && mod100 !== 12) suffix = 'nd';
  else if (mod10 === 3 && mod100 !== 13) suffix = 'rd';
  return `${d}${suffix}`;
}

function formatWeekOf(isoDate) {
  if (!isoDate) return '';
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return isoDate;
  const day = formatOrdinalDay(d.getDate());
  const month = d.toLocaleString('en-US', { month: 'long' });
  const year = d.getFullYear();
  return `${day} ${month} ${year}`;
}

function buildSubject(weekStartDate) {
  const pretty = formatWeekOf(weekStartDate);
  return `INDmoney weekly product review – week of ${pretty}`;
}

async function main() {
  const reportIdArg = process.argv[2] || null;

  const db = openDb(config.dbPath);
  const meta = getReportMetadata(db, reportIdArg);
  if (!meta) {
    console.error('No report metadata found. Run Phase 4 first or provide a valid report_id.');
    db.close();
    process.exit(1);
  }

  const reportsDir = path.resolve(config.reportsDir);
  const reportPath = path.join(reportsDir, meta.report_id + '.html');
  if (!fs.existsSync(reportPath)) {
    console.error('Report body not found at', reportPath);
    db.close();
    process.exit(1);
  }

  const reportHtml = fs.readFileSync(reportPath, 'utf8');
  const recipients = getActiveRecipients(db);
  if (recipients.length === 0) {
    console.log('No active recipients. Add recipients with: node add-recipient.js <email> [display_name]');
    db.close();
    process.exit(0);
  }

  const subject = buildSubject(meta.week_start_date);
  console.log('Sending report', meta.report_id, 'to', recipients.length, 'recipient(s). Subject:', subject);

  for (const r of recipients) {
    const result = await sendEmail({
      to: r.email,
      subject,
      html: reportHtml,
      replyTo: config.replyTo || undefined,
    });
    const status = result.success ? 'Sent' : 'Error';
    upsertDeliveryStatus(db, {
      reportId: meta.report_id,
      recipientEmail: r.email,
      status,
      sentAt: result.success ? new Date().toISOString() : undefined,
      errorMessage: result.error || undefined,
    });
    if (result.success) {
      console.log('  Sent:', r.email);
    } else {
      console.log('  Error:', r.email, result.error);
    }
  }

  db.close();
  console.log('Phase 5 Email Send finished.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
