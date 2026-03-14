/**
 * Split reviews into batches that stay under a token limit per prompt.
 * Ensures each batch (instruction + reviews) fits within batchTokenLimit.
 */

import { estimateTokens } from './tokenEstimator.js';
import { buildPrompt } from './promptBuilder.js';

/**
 * Compute token count of the prompt template (no reviews).
 * @returns {number}
 */
function getBasePromptTokens() {
  const emptyPrompt = buildPrompt([]);
  return estimateTokens(emptyPrompt);
}

/**
 * Split reviews into batches such that each batch's full prompt is at most maxTokens.
 * @param {Array<{ id: number, rating: number, text: string }>} reviews
 * @param {number} maxTokens - Max tokens for the whole prompt (instruction + reviews)
 * @returns {Array<Array<{ id: number, rating: number, text: string }>>}
 */
function splitReviewsIntoBatches(reviews, maxTokens) {
  if (reviews.length === 0) return [];
  const baseTokens = getBasePromptTokens();
  const budget = Math.max(0, maxTokens - baseTokens);
  if (budget <= 0) return [reviews];

  const batches = [];
  let current = [];
  let currentTokens = 0;

  for (const r of reviews) {
    const line = `[${r.id}] (rating ${r.rating}) ${r.text}`;
    const lineTokens = estimateTokens(line) + 2;

    if (current.length > 0 && currentTokens + lineTokens > budget) {
      batches.push(current);
      current = [];
      currentTokens = 0;
    }
    current.push(r);
    currentTokens += lineTokens;
  }

  if (current.length > 0) batches.push(current);
  return batches;
}

export { getBasePromptTokens, splitReviewsIntoBatches };
