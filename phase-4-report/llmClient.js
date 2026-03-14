/**
 * Gemini-only client for Phase 4 report composition.
 * Returns plain text (no JSON) for the one-pager narrative.
 * Retries on 429 (rate limit) with exponential backoff.
 * Logs full prompt, estimated token count, and request payload for quota/debugging.
 */

const MAX_RETRIES = 3;
const INITIAL_DELAY_MS = 2000;

/** Rough approximation: ~4 chars per token for English. */
function estimateTokens(text) {
  if (text == null || typeof text !== 'string') return 0;
  return Math.ceil(text.length / 4);
}

/**
 * Call Gemini generateContent for plain-text one-pager.
 * Logs the exact LLM call: full prompt, estimated input tokens, and request payload.
 * @param {string} prompt
 * @param {{ apiKey: string, model: string, maxOutputTokens?: number }} opts
 * @returns {Promise<string>} Plain text response
 */
export async function geminiCompleteText(prompt, { apiKey, model, maxOutputTokens = 1024 }) {
  if (!apiKey) throw new Error('GEMINI_API_KEY is not set in .env');

  const estimatedInputTokens = estimateTokens(prompt);
  const requestPayload = {
    model,
    contents: prompt,
    config: {
      temperature: 0.4,
      maxOutputTokens,
    },
  };

  console.log('\n--- Phase 4 Gemini LLM call ---');
  console.log('Full prompt sent:\n' + '---\n' + prompt + '\n---');
  console.log('Estimated input token count:', estimatedInputTokens);
  console.log('Request payload:', JSON.stringify({ model: requestPayload.model, config: requestPayload.config, contentsLength: prompt.length, contentsPreview: prompt.slice(0, 200) + (prompt.length > 200 ? '...' : '') }, null, 2));
  console.log('(Total request size: input ~' + estimatedInputTokens + ' tokens, max output ' + maxOutputTokens + ' tokens.)');
  console.log('--------------------------------\n');

  const { GoogleGenAI } = await import('@google/genai');
  const ai = new GoogleGenAI({ apiKey });

  let lastError;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await ai.models.generateContent({
        model: requestPayload.model,
        contents: requestPayload.contents,
        config: requestPayload.config,
      });

      const text = response?.text;
      if (text == null) throw new Error('Gemini API: no text in response');
      return text.trim();
    } catch (err) {
      lastError = err;
      const status = err?.status ?? err?.code;
      const is429 = status === 429 || status === 'RESOURCE_EXHAUSTED' || (err?.message && String(err.message).includes('429'));
      if (is429 && attempt < MAX_RETRIES) {
        const msg = err?.message ? String(err.message) : '';
        const retryMatch = msg.match(/[Rr]etry in (\d+(?:\.\d+)?)\s*s/);
        const suggestedSec = retryMatch ? parseFloat(retryMatch[1]) : null;
        const delay = suggestedSec != null ? Math.ceil(suggestedSec * 1000) + 1000 : INITIAL_DELAY_MS * Math.pow(2, attempt);
        console.warn(`Gemini rate limit (429). Retrying in ${Math.round(delay / 1000)}s (attempt ${attempt + 1}/${MAX_RETRIES})...`);
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      throw err;
    }
  }
  throw lastError;
}
