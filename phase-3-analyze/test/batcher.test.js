/**
 * Unit tests for batcher (split reviews by token limit).
 */
import { splitReviewsIntoBatches, getBasePromptTokens } from '../batcher.js';

function runTests() {
  let passed = 0;
  let failed = 0;

  const base = getBasePromptTokens();
  if (base > 0 && base < 500) {
    console.log('  ok: base prompt tokens in expected range');
    passed++;
  } else {
    console.log('  fail: base tokens', base);
    failed++;
  }

  const shortReviews = [
    { id: 1, rating: 5, text: 'Good app' },
    { id: 2, rating: 4, text: 'Nice' },
  ];
  const oneBatch = splitReviewsIntoBatches(shortReviews, 10000);
  if (oneBatch.length === 1 && oneBatch[0].length === 2) {
    console.log('  ok: small list stays one batch');
    passed++;
  } else {
    console.log('  fail: small list', oneBatch);
    failed++;
  }

  const manyReviews = Array.from({ length: 100 }, (_, i) => ({
    id: i + 1,
    rating: 4,
    text: 'This is a review with enough text to take several tokens per review so we can test batching.',
  }));
  const batches = splitReviewsIntoBatches(manyReviews, 500);
  if (batches.length > 1 && batches.every((b) => b.length >= 1)) {
    console.log('  ok: large list split into multiple batches');
    passed++;
  } else {
    console.log('  fail: batches', batches.length, batches.map((b) => b.length));
    failed++;
  }

  console.log('');
  process.exit(failed === 0 ? 0 : 1);
}

runTests();
