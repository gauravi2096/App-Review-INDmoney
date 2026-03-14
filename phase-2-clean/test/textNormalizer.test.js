/**
 * Unit tests for text normalizer (trim, collapse whitespace).
 */
import { normalizeText } from '../textNormalizer.js';

function runTests() {
  let passed = 0;
  let failed = 0;

  if (normalizeText('  hello   world  ') === 'hello world') {
    console.log('  ok: trim and collapse spaces');
    passed++;
  } else {
    console.log('  fail: trim and collapse');
    failed++;
  }

  if (normalizeText('line1\n\nline2\nline3') === 'line1 line2 line3') {
    console.log('  ok: newlines collapsed to space');
    passed++;
  } else {
    console.log('  fail: newlines');
    failed++;
  }

  if (normalizeText('') === '' && normalizeText(null) === '' && normalizeText(undefined) === '') {
    console.log('  ok: null/empty return empty string');
    passed++;
  } else {
    console.log('  fail: null/empty');
    failed++;
  }

  console.log('');
  process.exit(failed === 0 ? 0 : 1);
}

runTests();
