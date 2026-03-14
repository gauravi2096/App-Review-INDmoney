#!/usr/bin/env node
/**
 * Deactivate a recipient by email (set active = 0 so Phase 5 no longer sends to this address).
 *
 * Usage: node deactivate-recipient.js <email>
 */

import config from './config.js';
import { openDb, deactivateRecipient } from './db.js';

const email = process.argv[2];

if (!email) {
  console.error('Usage: node deactivate-recipient.js <email>');
  process.exit(1);
}

const db = openDb(config.dbPath);
deactivateRecipient(db, email);
db.close();
console.log('Deactivated recipient:', email);

