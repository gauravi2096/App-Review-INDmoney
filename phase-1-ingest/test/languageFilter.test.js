/**
 * Unit tests for language filter (keep English only).
 */
import { filterEnglish } from '../languageFilter.js';

function runTests() {
  let passed = 0;
  let failed = 0;

  const englishReview = { rating: 5, text: 'This app is very nice and easy to use.', date: '2025-01-15T10:00:00.000Z' };
  const hindiReview = { rating: 4, text: 'यह ऐप बहुत अच्छा है और उपयोग करने में आसान है।', date: '2025-01-15T10:00:00.000Z' };
  const spanishReview = { rating: 3, text: 'Esta aplicación es muy buena y fácil de usar.', date: '2025-01-15T10:00:00.000Z' };

  const { filtered: f1, droppedCount: d1 } = filterEnglish([englishReview]);
  if (f1.length === 1 && d1 === 0) {
    console.log('  ok: English review kept');
    passed++;
  } else {
    console.log('  fail: English review', { f1, d1 });
    failed++;
  }

  const { filtered: f2, droppedCount: d2 } = filterEnglish([hindiReview]);
  if (f2.length === 0 && d2 === 1) {
    console.log('  ok: non-English review dropped');
    passed++;
  } else {
    console.log('  fail: non-English should be dropped', { f2, d2 });
    failed++;
  }

  const { filtered: f3, droppedCount: d3 } = filterEnglish([englishReview, spanishReview, englishReview]);
  if (f3.length === 2 && d3 === 1) {
    console.log('  ok: mixed list keeps only English');
    passed++;
  } else {
    console.log('  fail: mixed list', { f3, d3 });
    failed++;
  }

  console.log('');
  return failed === 0 ? 0 : 1;
}

process.exit(runTests());
