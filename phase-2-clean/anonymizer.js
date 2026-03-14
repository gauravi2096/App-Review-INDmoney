/**
 * Anonymizer: strip emails, usernames, and obvious IDs from review text.
 * Reduces PII in cleaned data and downstream report/LLM outputs.
 */

/** Match email-like patterns. */
const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;

/** Match common "user id" / "customer id" style substrings. */
const USER_ID_REGEX = /\b(?:user[_\s]?id|customer[_\s]?id|ref[_\s]?no\.?|id[:\s#]*)\s*[#:]?\s*[a-zA-Z0-9-]{4,}\b/gi;

const REDACT_EMAIL = '[email redacted]';
const REDACT_ID = '[id redacted]';

/**
 * Anonymize text: replace emails and obvious user/customer IDs with placeholders.
 * Does not attempt to detect arbitrary usernames (too many false positives).
 * @param {string} text
 * @returns {string}
 */
function anonymize(text) {
  if (text == null || typeof text !== 'string') return '';
  let out = text
    .replace(EMAIL_REGEX, REDACT_EMAIL)
    .replace(USER_ID_REGEX, REDACT_ID);
  return out;
}

export { anonymize };
