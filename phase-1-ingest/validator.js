/**
 * Validator: enforce required fields for raw reviews.
 * Required: rating (1–5), text with at least 5 words, date (valid date).
 * Returns only valid rows; invalid rows are dropped (no PII in artifacts).
 */

/**
 * @param {Array<{ rating: number, text: string, date: string }>} reviews
 * @returns {{ valid: Array<{ rating: number, text: string, date: string }>, invalidCount: number }}
 */
function validateReviews(reviews) {
  const valid = [];
  let invalidCount = 0;

  for (const r of reviews) {
    const rating = r.rating != null ? Number(r.rating) : NaN;
    const rawText = r.text != null ? String(r.text) : '';
    const text = rawText.trim();
    const dateStr = r.date != null ? String(r.date).trim() : '';

    const validRating = Number.isInteger(rating) && rating >= 1 && rating <= 5;
    const validDate = dateStr !== '' && !Number.isNaN(new Date(dateStr).getTime());
    const wordCount = text === '' ? 0 : text.split(/\s+/).filter(Boolean).length;
    const validText = wordCount >= 5;

    if (validRating && validDate && validText) {
      valid.push({
        rating: Math.floor(rating),
        text,
        date: new Date(dateStr).toISOString(),
      });
    } else {
      invalidCount += 1;
    }
  }

  return { valid, invalidCount };
}

export { validateReviews };
