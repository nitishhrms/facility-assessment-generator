import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { INSIGHTS_SYSTEM, summarizeReport } from './src/lib/insightsPrompt.js';

// CMS Provider Data Catalog dataset identifiers (kept in sync with src/config/fieldMap.js)
const DATASETS = {
  provider: '4pq5-n9py', // Nursing Home Provider Information
  claims: 'ijh5-nb2v', // Medicare Claims Quality Measures
  averages: 'xcdc-v8bm', // State / US Averages
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

// Dev-only middleware so `npm run dev` works without the Netlify CLI.
// Mirrors the production proxy in netlify/functions/cms.js.
function cmsDevProxy() {
  return {
    name: 'cms-dev-proxy',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url || !req.url.startsWith('/api/cms')) return next();
        const url = new URL(req.url, 'http://localhost');
        const dataset = url.searchParams.get('dataset');
        const ccn = url.searchParams.get('ccn');
        res.setHeader('Content-Type', 'application/json');
        if (!DATASETS[dataset]) {
          res.statusCode = 400;
          return res.end(JSON.stringify({ error: 'Unknown dataset' }));
        }
        fetch(buildUpstreamUrl(dataset, ccn))
          .then((r) => r.text())
          .then((body) => res.end(body))
          .catch((e) => {
            res.statusCode = 502;
            res.end(JSON.stringify({ error: `Upstream CMS request failed: ${e}` }));
          });
      });
    },
  };
}

// Dev-only middleware for the AI insights endpoint, mirroring the production
// Netlify function so `npm run dev` works without `netlify dev`. Reads the key
// from .env (server-side; never exposed to the browser).
function insightsDevProxy(apiKey) {
  return {
    name: 'insights-dev-proxy',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url || !req.url.startsWith('/api/insights')) return next();
        res.setHeader('Content-Type', 'application/json');
        if (req.method !== 'POST') {
          res.statusCode = 405;
          return res.end(JSON.stringify({ error: 'Use POST.' }));
        }
        if (!apiKey) {
          res.statusCode = 500;
          return res.end(JSON.stringify({ error: 'AI insights unavailable: ANTHROPIC_API_KEY not set in .env.' }));
        }
        try {
          let body = '';
          for await (const chunk of req) body += chunk;
          const report = JSON.parse(body || '{}');
          const { default: Anthropic } = await import('@anthropic-ai/sdk');
          const client = new Anthropic({ apiKey });
          const msg = await client.messages.create({
            model: process.env.CHAT_MODEL || 'claude-opus-4-8',
            max_tokens: 500,
            system: INSIGHTS_SYSTEM,
            messages: [{ role: 'user', content: summarizeReport(report) }],
          });
          const insight = (msg.content || [])
            .filter((b) => b.type === 'text')
            .map((b) => b.text)
            .join('')
            .trim();
          res.end(JSON.stringify({ insight }));
        } catch (e) {
          res.statusCode = 502;
          res.end(JSON.stringify({ error: `AI insight failed: ${e.message || e}` }));
        }
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  // Load ALL env (incl. non-VITE_ vars like ANTHROPIC_API_KEY) for server-side use.
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react(), cmsDevProxy(), insightsDevProxy(env.ANTHROPIC_API_KEY)],
    // Proxy the chat backend so the SPA hits a same-origin path (and SSE streams through).
    // Start the backend with:  uvicorn chat.app:app --port 8000
    server: {
      proxy: {
        '/api/chat': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/chat/, '/chat'),
        },
      },
    },
  };
});
