/**
 * Review Fetcher: uses google-play-scraper to fetch reviews for an app.
 * Paginates with sort NEWEST, delay between pages, and retries on transient errors.
 * Returns reviews with fields: rating, title, text, date (ISO string).
 */

import gplay from 'google-play-scraper';

const RETRYABLE_CODES = new Set(['ECONNRESET', 'ETIMEDOUT', 'ECONNREFUSED', 'ENOTFOUND', 'EAI_AGAIN', 'EPROTO', 'ENETRESET', 'ECONNABORTED']);

function isRetryableError(err) {
  const code = err && (err.code || err.errno);
  if (code && RETRYABLE_CODES.has(String(code))) return true;
  const msg = err && typeof err.message === 'string' ? err.message : '';
  if (/timeout|ECONNRESET|network|socket hang up/i.test(msg)) return true;
  return false;
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Call gplay.reviews with retries and exponential backoff.
 * @param {object} opts - Options for gplay.reviews
 * @param {number} maxRetries - Max retry attempts per request
 * @param {number} retryDelayMs - Base delay before first retry (doubles each attempt)
 * @param {(msg: string) => void} [onRetry] - Called when a retry is about to happen
 */
async function reviewsWithRetry(opts, maxRetries, retryDelayMs, onRetry) {
  let lastErr;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await gplay.reviews(opts);
    } catch (err) {
      lastErr = err;
      if (attempt < maxRetries && isRetryableError(err)) {
        const wait = retryDelayMs * Math.pow(2, attempt);
        if (onRetry) onRetry(`Request failed (${err.code || err.message}), retrying in ${wait}ms (attempt ${attempt + 1}/${maxRetries})`);
        await delay(wait);
      } else {
        throw err;
      }
    }
  }
  throw lastErr;
}

/**
 * @param {object} options
 * @param {string} options.appId - Play Store app ID (e.g. in.indwealth)
 * @param {string} [options.lang='en']
 * @param {string} [options.country='us']
 * @param {number} [options.paginationDelayMs=1500] - Delay between page requests (increase to reduce rate limiting)
 * @param {number} [options.maxRetries=3] - Max retries per request on transient errors
 * @param {number} [options.retryDelayMs=3000] - Base delay before first retry (exponential backoff)
 * @returns {Promise<Array<{ rating: number, title: string, text: string, date: string }>>}
 */
async function fetchAllReviews({
  appId,
  lang = 'en',
  country = 'us',
  paginationDelayMs = 1500,
  maxRetries = 3,
  retryDelayMs = 3000,
}) {
  const results = [];
  let nextToken = undefined;

  do {
    const opts = {
      appId,
      lang,
      country,
      sort: gplay.sort.NEWEST,
      paginate: true,
    };
    if (nextToken !== undefined) {
      opts.nextPaginationToken = nextToken;
    }

    const res = await reviewsWithRetry(opts, maxRetries, retryDelayMs, (msg) => console.warn('  [ingest]', msg));
    const data = res.data || [];

    for (const r of data) {
      const date = r.date != null ? (typeof r.date === 'string' ? r.date : new Date(r.date).toISOString()) : null;
      results.push({
        rating: r.score != null ? Number(r.score) : null,
        title: r.title != null ? String(r.title) : '',
        text: r.text != null ? String(r.text) : '',
        date,
      });
    }

    nextToken = res.nextPaginationToken || null;
    if (nextToken && paginationDelayMs > 0) {
      await delay(paginationDelayMs);
    }
  } while (nextToken);

  return results;
}

export { fetchAllReviews };
