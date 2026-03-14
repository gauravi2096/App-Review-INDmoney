/**
 * Parse and validate LLM JSON response: max 5 themes, no PII in quotes.
 */

const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;

/**
 * Extract JSON from response (handle optional markdown code block).
 * @param {string} text
 * @returns {object | null}
 */
function extractJson(text) {
  if (text == null || typeof text !== 'string') return null;
  const trimmed = text.trim();
  const codeMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/);
  const raw = codeMatch ? codeMatch[1].trim() : trimmed;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Normalize a single theme to { label, description, reviewCount }.
 * @param {string | { label?: string, description?: string, reviewCount?: number }} t
 * @returns {{ label: string, description: string, reviewCount?: number }}
 */
function normalizeTheme(t) {
  if (t != null && typeof t === 'object' && ('label' in t || 'description' in t)) {
    const reviewCount = t.reviewCount != null ? Math.max(0, parseInt(Number(t.reviewCount), 10) || 0) : undefined;
    return {
      label: String(t.label ?? '').trim() || 'Unnamed theme',
      description: String(t.description ?? '').trim(),
      ...(reviewCount !== undefined && !Number.isNaN(reviewCount) ? { reviewCount } : {}),
    };
  }
  return { label: String(t ?? '').trim() || 'Unnamed theme', description: '' };
}

/**
 * Normalize a quote to { text, rating } or legacy string.
 * @param {string | { text?: string, rating?: number }} q
 * @returns {{ text: string, rating?: number }}
 */
function normalizeQuote(q) {
  if (q != null && typeof q === 'object' && 'text' in q) {
    const text = String(q.text ?? '').trim();
    const rating = q.rating != null ? Math.min(5, Math.max(1, parseInt(Number(q.rating), 10) || 0)) : undefined;
    return { text, ...(rating !== undefined && !Number.isNaN(rating) ? { rating } : {}) };
  }
  const text = String(q ?? '').trim();
  return { text, rating: undefined };
}

/**
 * Normalize a single action idea to a string (LLM may return objects e.g. { "idea": "..." }).
 * @param {string | { text?: string, idea?: string, action?: string, [key: string]: unknown }} a
 * @returns {string}
 */
function normalizeActionIdea(a) {
  if (typeof a === 'string') return a.trim();
  if (a != null && typeof a === 'object') {
    const s = a.text ?? a.idea ?? a.action ?? a.name;
    if (typeof s === 'string') return s.trim();
    const first = Object.values(a).find((v) => typeof v === 'string');
    if (typeof first === 'string') return first.trim();
  }
  return String(a ?? '').trim();
}

/**
 * Validate and normalize parsed analysis. Max 5 themes (each { label, description, reviewCount? }); quotes as { text, rating? }; strip PII.
 * @param {object} parsed
 * @returns {{ themes: Array<{ label: string, description: string, reviewCount?: number }>, quotes: Array<{ text: string, rating?: number }>, actionIdeas: string[] }}
 */
function validateAndNormalize(parsed) {
  const rawThemes = Array.isArray(parsed.themes) ? parsed.themes.slice(0, 5) : [];
  const themes = rawThemes.map(normalizeTheme);
  let rawQuotes = Array.isArray(parsed.quotes) ? parsed.quotes.slice(0, 3) : [];
  const actionIdeas = Array.isArray(parsed.actionIdeas)
    ? parsed.actionIdeas.map(normalizeActionIdea).filter(Boolean).slice(0, 3)
    : [];

  const quotes = rawQuotes
    .map(normalizeQuote)
    .filter((q) => q.text && !EMAIL_REGEX.test(q.text))
    .slice(0, 3);

  return { themes, quotes, actionIdeas };
}

/**
 * Parse LLM response text into validated analysis object.
 * @param {string} responseText
 * @returns {{ themes: Array<{ label: string, description: string, reviewCount?: number }>, quotes: Array<{ text: string, rating?: number }>, actionIdeas: string[] } | null}
 */
function parseResponse(responseText) {
  const parsed = extractJson(responseText);
  if (!parsed) return null;
  return validateAndNormalize(parsed);
}

export { extractJson, normalizeTheme, normalizeQuote, normalizeActionIdea, validateAndNormalize, parseResponse };
