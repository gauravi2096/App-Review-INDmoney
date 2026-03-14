/**
 * Unit tests for validator (rating 1-5, text >= 5 words, date).
 */
import { validateReviews } from '../validator.js';

const validReview = {
  rating: 5,
  text: 'This app is very nice',
  date: '2025-01-15T10:00:00.000Z',
};
const invalidRating = { rating: 0, text: 'This app is very nice', date: '2025-01-15T10:00:00.000Z' };
const invalidDate = { rating: 5, text: 'This app is very nice', date: 'not-a-date' };
const shortText = { rating: 5, text: 'Too short', date: '2025-01-15T10:00:00.000Z' };

function runTests() {
  let passed = 0;
  let failed = 0;

  const { valid: v1, invalidCount: i1 } = validateReviews([validReview]);
  if (v1.length === 1 && i1 === 0 && v1[0].rating === 5 && v1[0].date) {
    console.log('  ok: valid review passes');
    passed++;
  } else {
    console.log('  fail: valid review', { v1, i1 });
    failed++;
  }

  const { valid: v2, invalidCount: i2 } = validateReviews([invalidRating]);
  if (v2.length === 0 && i2 === 1) {
    console.log('  ok: invalid rating dropped');
    passed++;
  } else {
    console.log('  fail: invalid rating', { v2, i2 });
    failed++;
  }

  const { valid: v3, invalidCount: i3 } = validateReviews([invalidDate]);
  if (v3.length === 0 && i3 === 1) {
    console.log('  ok: invalid date dropped');
    passed++;
  } else {
    console.log('  fail: invalid date', { v3, i3 });
    failed++;
  }

  const { valid: vShort, invalidCount: iShort } = validateReviews([shortText]);
  if (vShort.length === 0 && iShort === 1) {
    console.log('  ok: short text (less than 5 words) dropped');
    passed++;
  } else {
    console.log('  fail: short text should be invalid', { vShort, iShort });
    failed++;
  }

  const { valid: v4 } = validateReviews([{ ...validReview, rating: 1 }, { ...validReview, rating: 5 }]);
  if (v4.length === 2) {
    console.log('  ok: multiple valid pass');
    passed++;
  } else {
    console.log('  fail: expected 2 valid, got', v4.length);
    failed++;
  }

  console.log('');
  return failed === 0 ? 0 : 1;
}

process.exit(runTests());
