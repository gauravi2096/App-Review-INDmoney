/**
 * Unit tests for anonymizer (strip emails and IDs).
 */
import { anonymize } from '../anonymizer.js';

function runTests() {
  let passed = 0;
  let failed = 0;

  const withEmail = anonymize('Contact me at john.doe@example.com for help.');
  if (withEmail.includes('[email redacted]') && !withEmail.includes('john.doe@example.com')) {
    console.log('  ok: email redacted');
    passed++;
  } else {
    console.log('  fail: email', withEmail);
    failed++;
  }

  const withId = anonymize('My user id 12345678 for reference.');
  if (withId.includes('[id redacted]')) {
    console.log('  ok: user id pattern redacted');
    passed++;
  } else {
    console.log('  fail: id', withId);
    failed++;
  }

  const plain = anonymize('The app is great.');
  if (plain === 'The app is great.') {
    console.log('  ok: no PII unchanged');
    passed++;
  } else {
    console.log('  fail: plain', plain);
    failed++;
  }

  console.log('');
  process.exit(failed === 0 ? 0 : 1);
}

runTests();
