/**
 * Build prompt from analysis and call Gemini to produce a weekly one-pager (≤maxWords).
 * Includes week/date range, total reviews, each theme (description + review count), quotes with rating.
 * Instructs the model to faithfully reflect Phase 3 analysis without summarizing.
 */

import { geminiCompleteText } from './llmClient.js';

/** @param {string | { text: string, rating?: number }} q */
function quoteLine(q) {
  const text = typeof q === 'object' && q && 'text' in q ? (q.text || '') : String(q || '');
  const rating = typeof q === 'object' && q && q.rating != null ? ` (${q.rating}/5 stars)` : '';
  return rating ? `- ${q.rating}/5 stars: "${text}"` : `- "${text}"`;
}

/** @param {{ label: string, description: string, reviewCount?: number }} t */
function themeLine(t) {
  const count = t.reviewCount != null ? ` (${t.reviewCount} reviews)` : '';
  return `- **${t.label}**: ${t.description || ''}${count}`;
}

/**
 * @param {{ themes: Array<{ label: string, description: string, reviewCount?: number }>, quotes: Array<string | { text: string, rating?: number }>, actionIdeas: string[] }} analysis
 * @param {{ maxWords: number, reportContext?: { totalReviews: number, dateMin: string | null, dateMax: string | null } }} opts
 * @returns {string} Prompt for Gemini
 */
function toDateOnly(isoOrDate) {
  if (!isoOrDate) return null;
  const s = String(isoOrDate);
  return s.slice(0, 10);
}

export function buildReportPrompt(analysis, { maxWords = 400, reportContext } = {}) {
  const min = reportContext?.dateMin ? toDateOnly(reportContext.dateMin) : null;
  const max = reportContext?.dateMax ? toDateOnly(reportContext.dateMax) : null;
  const dateRange =
    min && max ? `${min} to ${max}` : min ? `from ${min}` : max ? `through ${max}` : null;
  const periodLine =
    dateRange && reportContext?.totalReviews != null
      ? `Report period: ${dateRange}. Total reviews analyzed: ${reportContext.totalReviews}.`
      : reportContext?.totalReviews != null
        ? `Total reviews analyzed: ${reportContext.totalReviews}.`
        : '';

  const themesBlock = (analysis.themes || []).map(themeLine).join('\n');
  const quotesBlock = (analysis.quotes || []).map(quoteLine).join('\n');
  const actionsBlock = (analysis.actionIdeas || []).map((a) => `- ${a}`).join('\n');

  return `You are writing a weekly Product Pulse one-pager for internal stakeholders. You must FAITHFULLY reflect the Phase 3 analysis below. Do not summarize, paraphrase, or reinterpret. Use the exact theme labels and descriptions, the exact review counts, the exact quote text and ratings, and the exact action ideas as provided.

${periodLine ? periodLine + '\n\n' : ''}**THEMES (include every theme below with its full description and review count):**
${themesBlock || '(none)'}

**USER QUOTES (include each quote below with its star rating):**
${quotesBlock || '(none)'}

**ACTION IDEAS (include each action below verbatim):**
${actionsBlock || '(none)'}

TASK: Produce a plain-text report that faithfully reflects the data above. Structure:
1. A one-line title that includes the week or date range when provided.
2. A line stating the report period and total reviews analyzed (when provided).
3. "KEY THEMES" section: list each theme with its exact label, description, and review count.
4. "VOICE OF THE USER" section: list each quote with its exact text and star rating (e.g. "3/5 stars").
5. "RECOMMENDED ACTIONS" section: list each action idea exactly as given.

Rules:
- No markdown (no ** or ##). Use ALL CAPS for section headings and plain text for body.
- Maximum ${maxWords} words total. Be concise but do not omit or shorten the theme descriptions, quotes, or action ideas; use them as provided.
- No names, emails, or other PII.
- Output only the report text, nothing else.`;
}

/**
 * Compose one-pager text using Gemini.
 * @param {{ themes: Array<{ label: string, description: string, reviewCount?: number }>, quotes: Array<string | { text: string, rating?: number }>, actionIdeas: string[] }} analysis
 * @param {{ geminiApiKey: string, geminiModel: string, maxWords: number }} config
 * @param {{ totalReviews: number, dateMin: string | null, dateMax: string | null } | null} reportContext
 * @returns {Promise<string>} Plain-text one-pager
 */
export async function composeOnePager(analysis, config, reportContext = null) {
  const prompt = buildReportPrompt(analysis, {
    maxWords: config.maxWords,
    reportContext: reportContext ?? undefined,
  });
  return geminiCompleteText(prompt, {
    apiKey: config.geminiApiKey,
    model: config.geminiModel,
    maxOutputTokens: 2048,
  });
}
