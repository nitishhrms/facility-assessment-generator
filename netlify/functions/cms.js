// Serverless proxy for the CMS Provider Data Catalog API.
// Exists because the CMS API does not send CORS headers, so the browser
// cannot call it directly. The browser calls /api/cms (this function),
// and this function calls CMS server-side and relays the JSON back.

const DATASETS = {
  provider: '4pq5-n9py', // Nursing Home Provider Information
  claims: 'ijh5-nb2v', // Medicare Claims Quality Measures
  averages: 'xcdc-v8bm', // State / US Averages
};

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Content-Type': 'application/json',
};

function buildUpstreamUrl(dataset, ccn) {
  const id = DATASETS[dataset];
  const u = new URL(`https://data.cms.gov/provider-data/api/1/datastore/query/${id}/0`);
  if (ccn) {
    u.searchParams.set('conditions[0][property]', 'cms_certification_number_ccn');
    u.searchParams.set('conditions[0][operator]', '=');
    u.searchParams.set('conditions[0][value]', ccn);
  }
  u.searchParams.set('limit', '500');
  return u.toString();
}

export const handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS, body: '' };
  }

  const { dataset, ccn } = event.queryStringParameters || {};

  if (!DATASETS[dataset]) {
    return {
      statusCode: 400,
      headers: CORS,
      body: JSON.stringify({ error: 'Unknown or missing dataset parameter.' }),
    };
  }

  try {
    const upstream = await fetch(buildUpstreamUrl(dataset, ccn));
    const body = await upstream.text();
    if (!upstream.ok) {
      return {
        statusCode: 502,
        headers: CORS,
        body: JSON.stringify({ error: `CMS API returned ${upstream.status}.` }),
      };
    }
    return { statusCode: 200, headers: CORS, body };
  } catch (e) {
    return {
      statusCode: 502,
      headers: CORS,
      body: JSON.stringify({ error: `Upstream CMS request failed: ${e}` }),
    };
  }
};
