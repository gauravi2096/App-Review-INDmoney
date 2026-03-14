/**
 * Text normalizer: trim, collapse whitespace, normalize encoding.
 * Ensures single spaces and no leading/trailing whitespace.
 */

/**
 * Normalize text: trim and collapse runs of whitespace (including newlines) to a single space.
 * @param {string} text
 * @returns {string}
 */
function normalizeText(text) {
  if (text == null || typeof text !== 'string') return '';
  return text.trim().replace(/\s+/g, ' ');
}

export { normalizeText };
