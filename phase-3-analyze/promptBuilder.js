/**
 * Build a single structured prompt for theme extraction, quotes, and action ideas.
 * Output is requested as JSON for parsing.
 */

/**
 * Build the user prompt containing reviews and instructions.
 * @param {Array<{ id: number, rating: number, text: string }>} reviews
 * @returns {string}
 */
function buildPrompt(reviews) {
  const reviewList = reviews
    .map((r) => `[${r.id}] (rating ${r.rating}) ${r.text}`)
    .join('\n\n');

  return `You are analyzing app store reviews for a product team. Below are cleaned review texts with id and rating.

REVIEWS:
${reviewList}

TASK: Respond with exactly one JSON object (no markdown, no code fence) with these keys:
- "themes": array of 3 to 5 theme objects, each with "label" (short theme name), "description" (1–2 line description), and "reviewCount" (number of reviews in this batch that fit this theme; integer).
- "quotes": array of exactly 3 objects, each with "text" (one short representative quote from the reviews; exact wording where possible) and "rating" (the star rating 1–5 of the review this quote came from). Do not include emails, names, or IDs in text.
- "actionIdeas": array of exactly 3 concrete product action ideas (one line each) that the team could take based on these reviews.

Keep labels and action ideas concise. Ensure no PII in quotes.
JSON:`;
}

export { buildPrompt };
