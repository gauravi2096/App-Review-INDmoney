/**
 * Date normalizer: single format (ISO 8601) and consistent representation.
 */

/**
 * Normalize date string to ISO 8601 (YYYY-MM-DDTHH:mm:ss.sssZ).
 * Invalid or missing dates return null so caller can drop the row.
 * @param {string} dateStr
 * @returns {string | null}
 */
function normalizeDate(dateStr) {
  if (dateStr == null || typeof dateStr !== 'string') return null;
  const trimmed = dateStr.trim();
  if (trimmed === '') return null;
  const d = new Date(trimmed);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

export { normalizeDate };
