/**
 * Build prompt to consolidate multiple batch analysis results into one final output.
 */

/**
 * @param {Array<{ themes: Array<{ label: string, description: string }>, quotes: string[], actionIdeas: string[] }>} batchResults
 * @returns {string}
 */
function buildSynthesisPrompt(batchResults) {
  const formatThemes = (themes) => {
    if (!Array.isArray(themes) || themes.length === 0) return 'none';
    return themes
      .map((t) => {
        if (!t || typeof t !== 'object') return String(t);
        const label = t.label || '(no label)';
        const desc = (t.description || '').trim() || '(no description)';
        const count = t.reviewCount != null ? ` (${t.reviewCount} reviews)` : '';
        return `${label}: ${desc}${count}`;
      })
      .join('\n  ');
  };
  const formatQuotes = (quotes) => {
    if (!Array.isArray(quotes) || quotes.length === 0) return 'none';
    return quotes
      .map((q) => {
        const text = typeof q === 'object' && q && 'text' in q ? String(q.text || '') : String(q);
        const rating = typeof q === 'object' && q && q.rating != null ? ` [${q.rating}/5]` : '';
        return `"${text.replace(/"/g, '\\"')}"${rating}`;
      })
      .join(' | ');
  };
  const parts = batchResults.map((b, i) => {
    const themes = formatThemes(b.themes);
    const quotes = formatQuotes(b.quotes || []);
    const actions = (b.actionIdeas || []).join('; ');
    return `Batch ${i + 1}:\nThemes:\n  ${themes}\nQuotes: ${quotes || 'none'}\nAction ideas: ${actions || 'none'}`;
  });

  return `You are consolidating analysis from multiple batches of the same app's store reviews. Each batch was analyzed separately. Below are the results.

${parts.join('\n\n')}

TASK: Produce ONE combined analysis. Merge overlapping themes into 3–5 distinct themes, each with "label", "description", and "reviewCount" (sum or estimate of reviews across batches for this theme). Pick the 3 most representative user quotes; for each quote include "text" (exact wording where possible; no PII) and "rating" (1–5, the star rating of the source review). Output exactly one JSON object (no markdown, no code fence) with keys:
- "themes": array of 3 to 5 objects with "label", "description", "reviewCount" (integer)
- "quotes": array of exactly 3 objects with "text" (string) and "rating" (1–5)
- "actionIdeas": array of exactly 3 concrete product action ideas

JSON:`;
}

export { buildSynthesisPrompt };
