/**
 * Unit tests for response parser (extract JSON, validate, no PII).
 */
import { parseResponse, extractJson, validateAndNormalize } from '../responseParser.js';

function runTests() {
  let passed = 0;
  let failed = 0;

  const valid = '{"themes":["A","B","C"],"quotes":["q1","q2","q3"],"actionIdeas":["x","y","z"]}';
  const out = parseResponse(valid);
  if (out && out.themes.length === 3 && out.themes[0].label === 'A' && out.quotes.length === 3 && out.actionIdeas.length === 3) {
    console.log('  ok: valid JSON parsed (themes normalized to { label, description })');
    passed++;
  } else {
    console.log('  fail: valid', out);
    failed++;
  }

  const themesWithDesc = '{"themes":[{"label":"Login","description":"Users report login failures."}],"quotes":["q1"],"actionIdeas":["Fix auth"]}';
  const out2 = parseResponse(themesWithDesc);
  if (out2 && out2.themes.length === 1 && out2.themes[0].description.includes('login')) {
    console.log('  ok: theme objects with description preserved');
    passed++;
  } else {
    console.log('  fail: themes with description', out2);
    failed++;
  }

  const withCodeBlock = '```json\n' + valid + '\n```';
  if (parseResponse(withCodeBlock)) {
    console.log('  ok: markdown code block stripped');
    passed++;
  } else {
    console.log('  fail: code block');
    failed++;
  }

  const tooManyThemes = '{"themes":["1","2","3","4","5","6"],"quotes":["a","b","c"],"actionIdeas":["i","j","k"]}';
  const normalized = validateAndNormalize(extractJson(tooManyThemes));
  if (normalized.themes.length === 5 && normalized.themes[0].label === '1') {
    console.log('  ok: themes capped at 5');
    passed++;
  } else {
    console.log('  fail: themes', normalized.themes.length, normalized.themes[0]);
    failed++;
  }

  const quoteWithEmail = '{"themes":["T"],"quotes":["Contact me at u@x.com"],"actionIdeas":["A"]}';
  const safe = parseResponse(quoteWithEmail);
  if (safe && safe.quotes.length === 0) {
    console.log('  ok: quote with email dropped');
    passed++;
  } else {
    console.log('  fail: email filter', safe);
    failed++;
  }

  if (parseResponse('not json') === null) {
    console.log('  ok: invalid JSON returns null');
    passed++;
  } else {
    console.log('  fail: invalid');
    failed++;
  }

  console.log('');
  process.exit(failed === 0 ? 0 : 1);
}

runTests();
