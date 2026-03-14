import { countWords, truncateToWordCount } from '../wordCounter.js';

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

assert(countWords('') === 0, 'empty');
assert(countWords('  ') === 0, 'spaces');
assert(countWords('one') === 1, 'one');
assert(countWords('one two three') === 3, 'three');
assert(countWords('  one   two  ') === 2, 'trim and collapse');

const { text, truncated } = truncateToWordCount('a b c', 5);
assert(text === 'a b c' && !truncated, 'no truncate');

const { text: t2, truncated: tr2 } = truncateToWordCount('a b c d e f', 3);
assert(t2 === 'a b c' && tr2 === true, 'truncate to 3');

console.log('wordCounter tests passed');
