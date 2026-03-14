/**
 * Date filter: keep only reviews from the last N weeks (configurable 8–12).
 * Compares review date to (now - N weeks). Reviews without a valid date are dropped.
 */

/**
 * @param {Array<{ rating: number, title: string, text: string, date: string | null }>} reviews
 * @param {number} weeks - Include reviews from the last N weeks (e.g. 8 or 12)
 * @returns {Array<{ rating: number, title: string, text: string, date: string }>}
 */
function filterByDateWindow(reviews, weeks) {
  const cutoffMs = Date.now() - weeks * 7 * 24 * 60 * 60 * 1000;
  const cutoff = new Date(cutoffMs);

  return reviews.filter((r) => {
    if (r.date == null || r.date === '') return false;
    const d = new Date(r.date);
    if (Number.isNaN(d.getTime())) return false;
    return d >= cutoff;
  });
}

export { filterByDateWindow };
