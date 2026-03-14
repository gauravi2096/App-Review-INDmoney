/**
 * Language filter: keep only reviews detected as English.
 * Uses franc (ISO 639-3); keeps only when result is 'eng'.
 * Non-English and undetected (e.g. too short) are dropped.
 */

import { franc } from 'franc';

const ENGLISH_CODE = 'eng';

/**
 * @param {Array<{ rating: number, title?: string, text: string, date: string }>} reviews
 * @returns {{ filtered: Array<{ rating: number, title?: string, text: string, date: string }>, droppedCount: number }}
 */
function filterEnglish(reviews) {
  const filtered = [];
  let droppedCount = 0;

  for (const r of reviews) {
    const text = r.text != null ? String(r.text).trim() : '';
    const lang = franc(text, { minLength: 1 });
    if (lang === ENGLISH_CODE) {
      filtered.push(r);
    } else {
      droppedCount += 1;
    }
  }

  return { filtered, droppedCount };
}

export { filterEnglish };
