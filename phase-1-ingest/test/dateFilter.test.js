/**
 * Unit tests for date filter (last N weeks).
 */
import { filterByDateWindow } from '../dateFilter.js';

const now = new Date();
const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
const tenWeeksAgo = new Date(now.getTime() - 10 * 7 * 24 * 60 * 60 * 1000);
const fourteenWeeksAgo = new Date(now.getTime() - 14 * 7 * 24 * 60 * 60 * 1000);

const reviews = [
  { rating: 5, title: 'a', text: 'b', date: now.toISOString() },
  { rating: 4, title: 'c', text: 'd', date: oneWeekAgo.toISOString() },
  { rating: 3, title: 'e', text: 'f', date: tenWeeksAgo.toISOString() },
  { rating: 2, title: 'g', text: 'h', date: fourteenWeeksAgo.toISOString() },
  { rating: 5, title: 'i', text: 'j', date: null },
  { rating: 5, title: 'k', text: 'l', date: '' },
];

function runTests() {
  let passed = 0;
  let failed = 0;

  const filtered12 = filterByDateWindow(reviews, 12);
  if (filtered12.length === 3) {
    console.log('  ok: 12-week window returns 3 reviews (drops null, empty, 14 weeks)');
    passed++;
  } else {
    console.log('  fail: expected 3, got', filtered12.length);
    failed++;
  }

  const filtered8 = filterByDateWindow(reviews, 8);
  if (filtered8.length === 2) {
    console.log('  ok: 8-week window returns 2 reviews');
    passed++;
  } else {
    console.log('  fail: expected 2, got', filtered8.length);
    failed++;
  }

  const empty = filterByDateWindow([], 12);
  if (empty.length === 0) {
    console.log('  ok: empty input returns empty');
    passed++;
  } else {
    console.log('  fail: expected 0, got', empty.length);
    failed++;
  }

  console.log('');
  return failed === 0 ? 0 : 1;
}

process.exit(runTests());
