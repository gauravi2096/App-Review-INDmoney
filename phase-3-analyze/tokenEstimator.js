/**
 * Token estimator for LLM provider selection.
 * Rough approximation: ~4 chars per token for English.
 */

/**
 * Estimate token count for a string (approximate).
 * @param {string} text
 * @returns {number}
 */
function estimateTokens(text) {
  if (text == null || typeof text !== 'string') return 0;
  return Math.ceil(text.length / 4);
}

export { estimateTokens };
