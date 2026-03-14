/**
 * Count words in plain text for enforcing one-pager limit.
 */

/**
 * @param {string} text
 * @returns {number}
 */
export function countWords(text) {
  if (typeof text !== 'string' || !text.trim()) return 0;
  return text.trim().split(/\s+/).filter(Boolean).length;
}

/**
 * Truncate text to at most maxWords by cutting at word boundary.
 * @param {string} text
 * @param {number} maxWords
 * @returns {{ text: string, truncated: boolean }}
 */
export function truncateToWordCount(text, maxWords) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) return { text: text.trim(), truncated: false };
  return {
    text: words.slice(0, maxWords).join(' '),
    truncated: true,
  };
}
