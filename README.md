# INFINITE — Facility Assessment Report Generator

A lightweight web app for Medelite's facility evaluation workflow. Enter a
facility's **CCN** (CMS Certification Number), pull live public data from the
**CMS Provider Data Catalog**, merge it with manual operational inputs, and
export a polished, print-ready **PDF** (or editable **Word**) report — complete
with a clickable Medicare Care Compare source link.

Built for the Medelite Technical Case Study.

## Live demo & repo

- **Live app:** https://medelite-facility-report-nitish.netlify.app
- **Repository:** https://github.com/nitishhrms/facility-assessment-generator
- **Test CCN:** `686123` (Kendall Lakes Healthcare and Rehab Center, Miami FL)

## Features

**Required MVP**
- Dynamic CCN lookup against the live CMS API
- Auto-filled facility name, location, certified beds, and all 4 star ratings
- Optional **facility name override** (custom name wins over the CMS legal name)
- Manual operational inputs (EMR, current census, patient type, Medelite history, medical coverage)
- One-click **Download PDF** — instant client-side browser download
- Clickable **Medicare Care Compare** hyperlink embedded in the export
- Static **"INFINITE — Managed by MEDELITE"** branding + dynamic state code

**Bonus (all implemented)**
- All **12 hospitalization / ED metrics** (short-stay + long-stay, with state & national averages)
- **Word (.docx)** export
- **Complex charts & cards** (Recharts): color-coded star **rating cards** (green/amber/red),
  **split comparison bar charts** (short-stay % vs long-stay per-1,000 — separate axes so
  scales are comparable), a **benchmark donut**, and a **performance heatmap**
- **Advanced error handling** — 6-digit CCN validation before any API call, not-found /
  API-failure states, and `N/A` fallbacks for missing fields
- **AI assessment** — a one-click Claude-generated partnership takeaway for the facility
  (serverless `/api/insights`; key stays server-side)
- **Lookup caching** — provider/claims memoized by CCN and the averages dataset fetched
  once per session, so repeat lookups cost zero extra CMS calls (also eases rate limits)
- **Batch mode** — upload/paste a CSV of CCNs and download every report at once as a
  **ZIP of PDFs + a roll-up summary CSV** (bounded concurrency, per-row pass/fail)

**QA Analytics extras** (beyond the brief — see [QA & Data Validation](#qa--data-validation))
- **Benchmark verdicts** — each hospitalization/ED measure is flagged *better / worse than
  the national average* (lower is better), with a headline **QA Summary** carried into the
  PDF and Word exports
- **Data Quality panel** — CMS field completeness %, the CMS `processing_date` (data
  freshness), and explicit missing-field flags
- **Client-side CCN validation** — enforces a 6-digit CCN before any API round-trip
- **38 unit tests** (`buildReport`, benchmark verdicts, `medicareUrl`, data quality, CMS-client caching)

## Tech stack

| Concern | Choice |
|---|---|
| Framework | React + Vite |
| Styling | Tailwind CSS (Apple-style neutral + system-blue accent) |
| PDF | jsPDF + jsPDF-AutoTable (client-side, real clickable link) |
| Word | `docx` |
| Charts | Recharts (bar, donut/pie) + a CSS heatmap |
| AI insights | Anthropic Claude (`claude-opus-4-8`) via `@anthropic-ai/sdk`, in a serverless function |
| State | plain `useState` |
| API access | Netlify serverless functions (CMS proxy + AI insights) |
| Tests | Vitest (38 tests) |
| Hosting | Netlify |

## How it works

```
Browser ──/api/cms?dataset=…&ccn=…──► proxy ──► data.cms.gov ──► JSON ──► report model ──► PDF / Word
```

The browser never calls CMS directly — it calls our own `/api/cms` endpoint,
which calls CMS server-side. See the assumptions below for why.

**Data sources (CMS Provider Data Catalog):**

| Report data | Dataset | ID |
|---|---|---|
| Name, address, beds, star ratings | Provider Information | `4pq5-n9py` |
| 12 hospitalization/ED metrics (facility) | Medicare Claims Quality Measures | `ijh5-nb2v` |
| State + national averages | State / US Averages | `xcdc-v8bm` |

The 12 metric lines come from 4 claims measures, each emitting facility / national
/ state rows:

| Measure code | Report metric | Source field |
|---|---|---|
| 521 | Short Term Hospitalization (STR) | `adjusted_score` |
| 522 | STR ED Visit | `adjusted_score` |
| 551 | LT Hospitalization | `adjusted_score` |
| 552 | LT ED Visit | `adjusted_score` |

Every "messy CMS field name → clean report label" decision lives in one place:
[`src/config/fieldMap.js`](src/config/fieldMap.js).

## Run locally

```bash
npm install
npm run dev          # http://localhost:5173
```

`npm run dev` includes small Vite middleware that mimics the production proxies,
so both the CMS API and the AI insights endpoint work locally without the Netlify
CLI. To exercise the real Netlify Functions instead:

```bash
npm install -g netlify-cli
netlify dev
```

**AI insights (optional):** the `/api/insights` feature calls Claude. To enable it,
copy `.env.example` to `.env` and add your key — it is read **server-side only** and
never reaches the browser:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Without a key, the rest of the app works fully; only the "Generate AI insight" button
returns a friendly "unavailable" message.

```bash
npm test             # 38 Vitest unit tests
```

## Deploy (Netlify)

1. Push this folder to a public Git repo.
2. In Netlify: **Add new site → Import from Git** → pick the repo.
   Build settings are auto-detected from `netlify.toml`
   (build `npm run build`, publish `dist`, functions `netlify/functions`).
3. Or from the CLI: `netlify deploy --build --prod`.
4. **For the AI insights feature in production**, add an environment variable in
   Netlify (**Site settings → Environment variables**): `ANTHROPIC_API_KEY=sk-ant-…`.
   The CMS lookup, exports, charts, and heatmap all work without it; only `/api/insights`
   needs it.

> **Note:** the deployed site shows the **Report Generator** only. The optional
> **Healthcare Assistant** chat tab (a separate Python/RAG service) runs locally and is
> hidden in production unless a backend URL is configured — see *Optional extension* below.

## QA & Data Validation

This role is *QA Analytics*, so the app doesn't just **display** CMS data — it **interprets
and validates** it.

**Benchmark verdicts.** For every hospitalization / ED measure a *lower* value is better
(fewer hospitalizations / ED visits). `buildReport()` compares each facility value to the
national and state averages and emits a verdict (`better` / `worse` / `same` / `na`), shown
as colored chips under the chart and rolled up into a one-line **QA Summary**
(e.g. _"2 of 4 hospitalization/ED measures at or better than the national average"_). The
summary is embedded in both the PDF and Word exports.

**Source-data quality.** Before trusting the numbers, the **Data Quality** panel reports:
- **Completeness** — how many of the CMS-sourced fields actually came back populated;
- **Freshness** — the CMS `processing_date`, so a reader knows how current the data is;
- **Missing-field flags** — any star rating or metric that returned empty is called out
  explicitly instead of silently rendering `N/A`.

The verdict and data-quality logic live in pure, unit-tested functions
([`src/lib/buildReport.js`](src/lib/buildReport.js),
[`src/lib/dataQuality.js`](src/lib/dataQuality.js)) and are covered by the test suite
(`npm test` — 38 tests).

## Engineering assumptions & notes

1. **A serverless proxy was required (CORS).** The CMS Provider Data Catalog API
   does not return CORS headers, so a direct browser `fetch` is blocked. The app
   routes requests through a one-file Netlify Function
   ([`netlify/functions/cms.js`](netlify/functions/cms.js)). This also keeps the
   CMS dataset IDs server-side and gives one place to handle upstream errors.
2. **The report shows _live_ CMS values**, which differ from the static sample
   PDF in the case materials (e.g. live shows 150 certified beds / overall
   rating 5; the sample PDF showed 120 / rating 1). The sample is treated as a
   **layout reference**, and CMS is the source of truth.
3. **Claims metric value:** the risk-adjusted `adjusted_score` is used for each
   facility measure (the value used in the CMS five-star methodology). Short-stay
   measures are shown as percentages; long-stay measures as a rate per 1,000
   resident days, matching the reference layout.
4. **Branding guardrail:** "INFINITE" is a static internal brand and is never
   overwritten by the facility name; the facility name appears only in the
   report body under "Name of Facility".
5. **Missing data** renders as `N/A` rather than breaking the report.
6. **Lookup caching.** Provider/claims rows are memoized by CCN and the averages dataset
   is fetched once per session ([`src/api/cms.js`](src/api/cms.js)), so re-querying a
   facility (or any second lookup, which reuses averages) makes **zero** extra CMS calls —
   a deliberate mitigation for CMS rate limits. A page reload clears the cache.
7. **AI insights are serverless.** `/api/insights` is a short, stateless Claude call
   ([`netlify/functions/insights.js`](netlify/functions/insights.js)), so it deploys on
   Netlify and keeps the key server-side. Requires `ANTHROPIC_API_KEY` in the environment.

## Optional extension — Healthcare Assistant (local)

Beyond the brief, the repo includes a guarded **RAG chatbot** (`chat/`) that answers
structured facility questions (SQL over a local warehouse), unstructured medical questions
(PubMed retrieval), and falls back to web search — with security + out-of-domain gating and
Claude-generated, cited answers. It runs as a local **FastAPI** service
(`uvicorn chat.app:app --port 8000`) and is **hidden in the deployed site** because its
PubMedBERT model + vector store need a persistent host (not Netlify's serverless model).
It is **not** part of the required MVP; see [`CHAT_SYSTEM_PLAN.md`](CHAT_SYSTEM_PLAN.md).
