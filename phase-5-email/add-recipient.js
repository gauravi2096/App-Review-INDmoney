#!/usr/bin/env node
/**
 * Add an active recipient to the list. Phase 5 sends only to active recipients.
 *
 * Usage: node add-recipient.js <email> [display_name]
 */

import config from './config.js';
import { openDb, addRecipient } from './db.js';

const email = process.argv[2];
const displayName = process.argv[3] || null;

if (!email) {
  console.error('Usage: node add-recipient.js <email> [display_name]');
  process.exit(1);
}

const db = openDb(config.dbPath);
addRecipient(db, { email, displayName });
db.close();
console.log('Added recipient:', email, displayName ? `(${displayName})` : '');
