/**
 * Unit tests for date normalizer (ISO 8601).
 */
import { normalizeDate } from '../dateNormalizer.js';

function runTests() {
  let passed = 0;
  let failed = 0;

  const iso = normalizeDate('2025-01-15T10:00:00.000Z');
  if (iso === '2025-01-15T10:00:00.000Z') {
    console.log('  ok: ISO string unchanged');
    passed++;
  } else {
    console.log('  fail: ISO', iso);
    failed++;
  }

  const parsed = normalizeDate('January 15, 2025');
  if (parsed !== null && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(parsed) && parsed.includes('2025')) {
    console.log('  ok: readable date parsed to ISO');
    passed++;
  } else {
    console.log('  fail: parsed', parsed);
    failed++;
  }

  if (normalizeDate('not-a-date') === null && normalizeDate('') === null && normalizeDate(null) === null) {
    console.log('  ok: invalid dates return null');
    passed++;
  } else {
    console.log('  fail: invalid');
    failed++;
  }

  console.log('');
  process.exit(failed === 0 ? 0 : 1);
}

runTests();
