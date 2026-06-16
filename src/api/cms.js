// Thin client wrapper around our /api/cms serverless proxy.
// The proxy (netlify/functions/cms.js in prod, Vite middleware in dev) is what
// actually talks to data.cms.gov — this just shapes the request/response.
//
// In-memory memoization: a facility's provider/claims rows are cached by CCN, and
// the slow-changing state/national AVERAGES dataset is fetched once per session.
// Re-looking-up a CCN you've already pulled (or any second lookup, which reuses
// averages) costs ZERO extra API calls. The cache lives for the page session;
// a reload clears it. `clearCmsCache()` forces a refresh on demand.

const providerCache = new Map(); // ccn -> provider row | null (null = not found, also cached)
const claimsCache = new Map(); // ccn -> claims rows
let averagesCache = null; // the ~54 state/nation rows (identical every lookup)

async function queryDataset(dataset, ccn) {
  const params = new URLSearchParams({ dataset });
  if (ccn) params.set('ccn', ccn);

  const res = await fetch(`/api/cms?${params.toString()}`);
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (body?.error) message = body.error;
    } catch {
      /* non-JSON error body — keep default message */
    }
    throw new Error(message);
  }

  const json = await res.json();
  return json.results || [];
}

// One facility row (or null if the CCN matched nothing). Memoized by CCN.
export async function fetchProvider(ccn) {
  if (providerCache.has(ccn)) return providerCache.get(ccn);
  const rows = await queryDataset('provider', ccn);
  const provider = rows[0] || null;
  providerCache.set(ccn, provider); // caches null too -> a bad CCN isn't re-fetched
  return provider;
}

// Up to 4 claims-measure rows for the facility. Memoized by CCN.
export async function fetchClaims(ccn) {
  if (claimsCache.has(ccn)) return claimsCache.get(ccn);
  const rows = await queryDataset('claims', ccn);
  claimsCache.set(ccn, rows);
  return rows;
}

// All state/nation average rows (~54); filtered client-side in buildReport.
// Fetched once per session — it's the same data for every facility.
export async function fetchAverages() {
  if (averagesCache) return averagesCache;
  averagesCache = await queryDataset('averages');
  return averagesCache;
}

// Drop all cached data (e.g. for a manual "refresh" or in tests).
export function clearCmsCache() {
  providerCache.clear();
  claimsCache.clear();
  averagesCache = null;
}
