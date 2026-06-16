import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearCmsCache, fetchAverages, fetchClaims, fetchProvider } from './cms.js';

const ok = (results) => ({ ok: true, json: async () => ({ results }) });

beforeEach(() => clearCmsCache());
afterEach(() => vi.unstubAllGlobals());

describe('CMS client memoization', () => {
  it('fetches a provider once, then serves the same object from cache', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok([{ provider_name: 'KENDALL LAKES' }]));
    vi.stubGlobal('fetch', fetchMock);

    const a = await fetchProvider('686123');
    const b = await fetchProvider('686123'); // re-use existing CCN

    expect(a).toBe(b); // same cached reference
    expect(fetchMock).toHaveBeenCalledTimes(1); // API NOT called again
  });

  it('caches a not-found (null) result so a bad CCN is not re-queried', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok([]));
    vi.stubGlobal('fetch', fetchMock);

    expect(await fetchProvider('000000')).toBeNull();
    expect(await fetchProvider('000000')).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('fetches the averages dataset only once across many lookups', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok([{ state_or_nation: 'NATION' }]));
    vi.stubGlobal('fetch', fetchMock);

    await fetchAverages();
    await fetchAverages();
    await fetchAverages();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('keys claims by CCN (different CCNs each hit once)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok([{ measure_code: '521' }]));
    vi.stubGlobal('fetch', fetchMock);

    await fetchClaims('686123');
    await fetchClaims('686123');
    await fetchClaims('015009');
    expect(fetchMock).toHaveBeenCalledTimes(2); // one per distinct CCN
  });

  it('does not cache failures (errors retry on next call)', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 502, json: async () => ({ error: 'upstream' }) })
      .mockResolvedValueOnce(ok([{ provider_name: 'X' }]));
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchProvider('686123')).rejects.toThrow('upstream');
    const ok2 = await fetchProvider('686123'); // retried, now succeeds
    expect(ok2.provider_name).toBe('X');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
