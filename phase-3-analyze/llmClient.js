/**
 * LLM client abstraction: Groq (fetch) and Gemini (@google/genai).
 * Same prompt and response handling for both.
 */

const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions';

/**
 * Call Groq chat completions API.
 * @param {string} prompt - Full user prompt (system can be in first message).
 * @param {{ apiKey: string, model: string, maxTokens?: number }} opts
 * @returns {Promise<string>} Assistant message content
 */
async function groqComplete(prompt, { apiKey, model, maxTokens = 2048 }) {
  const res = await fetch(GROQ_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: 'You respond only with valid JSON. No markdown code blocks.' },
        { role: 'user', content: prompt },
      ],
      temperature: 0.3,
      max_tokens: maxTokens,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Groq API error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const content = data.choices?.[0]?.message?.content;
  if (content == null) throw new Error('Groq API: no content in response');
  return content;
}

/**
 * Call Gemini generateContent.
 * @param {string} prompt
 * @param {{ apiKey: string, model: string }} opts
 * @returns {Promise<string>} Text response
 */
async function geminiComplete(prompt, { apiKey, model }) {
  const { GoogleGenAI } = await import('@google/genai');
  const ai = new GoogleGenAI({ apiKey });

  const response = await ai.models.generateContent({
    model,
    contents: prompt,
    config: {
      temperature: 0.3,
      maxOutputTokens: 2048,
      responseMimeType: 'application/json',
    },
  });

  const text = response?.text;
  if (text == null) throw new Error('Gemini API: no text in response');
  return text;
}

/**
 * Complete using the chosen provider.
 * @param {'groq' | 'gemini'} provider
 * @param {string} prompt
 * @param {object} config - config.groqApiKey, config.geminiApiKey, config.groqModel, config.geminiModel
 * @returns {Promise<string>}
 */
async function complete(provider, prompt, config) {
  if (provider === 'groq') {
    if (!config.groqApiKey) throw new Error('GROQ_API_KEY is not set');
    return groqComplete(prompt, { apiKey: config.groqApiKey, model: config.groqModel });
  }
  if (provider === 'gemini') {
    if (!config.geminiApiKey) throw new Error('GEMINI_API_KEY or GOOGLE_API_KEY is not set');
    return geminiComplete(prompt, { apiKey: config.geminiApiKey, model: config.geminiModel });
  }
  throw new Error(`Unknown provider: ${provider}`);
}

export { groqComplete, geminiComplete, complete };
