/**
 * Unit tests for token estimator.
 */
import { estimateTokens } from '../tokenEstimator.js';

function runTests() {
  let passed = 0;
  let failed = 0;

  if (estimateTokens('hello') === 2) {
    console.log('  ok: short string ~chars/4');
    passed++;
  } else {
    console.log('  fail:', estimateTokens('hello'));
    failed++;
  }

  if (estimateTokens('') === 0 && estimateTokens(null) === 0) {
    console.log('  ok: empty/null zero');
    passed++;
  } else {
    console.log('  fail: empty/null');
    failed++;
  }

  const long = 'a'.repeat(400);
  if (estimateTokens(long) === 100) {
    console.log('  ok: long string 400 chars -> 100 tokens');
    passed++;
  } else {
    console.log('  fail:', estimateTokens(long));
    failed++;
  }

  console.log('');
  process.exit(failed === 0 ? 0 : 1);
}

runTests();
