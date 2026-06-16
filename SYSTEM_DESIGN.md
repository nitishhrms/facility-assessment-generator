# System Design — Facility Assessment Report Generator

> One-page engineering design for the Medelite technical case study.
> Audience: the live walkthrough reviewer.

---

## 1. Problem

A Medelite director needs a fast way to evaluate a skilled nursing facility
before outreach. Today that means digging through public CMS databases and
internal notes by hand. We want a single screen where a user types a facility's
**CCN**, instantly sees its public performance data merged with internal
operational notes, and downloads a polished, print-ready report.

**Constraints**
- ~4–6 hour MVP, hosted live.
- Data comes from the public CMS Provider Data Catalog.
- Output must be a clean PDF with a *clickable* Medicare source link.
- Fixed "INFINITE — Managed by MEDELITE" branding (must not be overwritten).

---

## 2. High-level architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          BROWSER (React + Vite)                        │
│                                                                        │
│   CcnLookupForm ─┐                                                     │
│   ManualInputs ──┼─► App state (useState) ─► buildReport() ─► report   │
│                  │                                  │   model           │
│                  │                                  ├─► ReportPreview   │
│                  │                                  ├─► MetricCards     │
│                  │                                  ├─► MetricsChart    │
│                  │                                  ├─► exportPdf()     │
│                  │                                  └─► exportDocx()    │
│                  │                                                      │
│             fetch /api/cms?dataset=…&ccn=…                             │
└──────────────────────┬─────────────────────────────────────────────────┘
                        │  (same origin — no CORS problem)
                        ▼
        ┌───────────────────────────────────┐
        │  Netlify Function  (/api/cms)      │   ← server-side, no CORS limit
        │  netlify/functions/cms.js          │
        └───────────────┬───────────────────┘
                        │  server-to-server fetch
                        ▼
        ┌───────────────────────────────────┐
        │  CMS Provider Data Catalog API     │
        │  data.cms.gov/provider-data        │
        └───────────────────────────────────┘
```

**Key decision — the proxy.** The CMS API returns **no CORS headers**, so a
browser `fetch` is blocked. A one-file serverless function calls CMS
server-to-server and relays JSON to the browser. Bonus: dataset IDs and error
handling live in one server-side place. In local dev, a tiny Vite middleware
mimics the function so `npm run dev` "just works."

---

## 3. Data model & sources

Three CMS datasets, fetched in parallel on lookup:

| Concern | Dataset | ID | Keyed by |
|---|---|---|---|
| Facility info + 4 star ratings | Provider Information | `4pq5-n9py` | CCN |
| 12 hospitalization/ED metrics (facility) | Medicare Claims Quality Measures | `ijh5-nb2v` | CCN (4 rows) |
| State + national averages | State / US Averages | `xcdc-v8bm` | `state_or_nation` |

**The 12 metrics** = 4 claims measures × {facility, national, state}:

| Code | Resident type | Metric | Facility source | Avg source (wide column) |
|---|---|---|---|---|
| 521 | Short-stay | Rehospitalization | `adjusted_score` | `percentage_of_short_stay…rehospitalized…` |
| 522 | Short-stay | Outpatient ED visit | `adjusted_score` | `percentage_of_short_stay…outpatient_em…` |
| 551 | Long-stay | Hospitalizations / 1,000 days | `adjusted_score` | `number_of_hospitalizations_per_1000…` |
| 552 | Long-stay | Outpatient ED / 1,000 days | `adjusted_score` | `number_of_outpatient_emergency…per_1000…` |

Per the brief: **STR → Short-Stay**, **LT → Long-Stay**.

---

## 4. Core data flow — `buildReport()`

The single pure function that turns raw API payloads + manual inputs into one
normalized `report` model consumed by the preview, the PDF, and the Word export.

```
buildReport(provider, claims[], averages[], manual)
  ├─ name        = manual.overrideName || provider.provider_name   (override wins)
  ├─ location    = composed from address parts (clean spacing)
  ├─ ratings[]   = RATING_FIELDS mapped from provider row
  ├─ metrics[]   = CLAIMS_MEASURES → { facility (claims), state & national (averages) }
  ├─ tableRows[] = 25 ordered [label, value] pairs mirroring the snapshot template
  └─ medicareUrl = care-compare/details/nursing-home/{ccn}/view-all?state={state}
```

One model, three renderers → the on-screen table, the PDF, and the .docx are
always identical by construction.

---

## 5. Document generation

**PDF — jsPDF + AutoTable (client-side).**
Draws real vector text and a real link annotation via `doc.textWithLink(...)`.
Chosen over the HTML-to-image route (html2canvas) because a screenshot produces
blurry text and a *non-clickable* link — the brief explicitly requires a
clickable hyperlink. Layout: static branding banner → title + state → two-column
table → clickable Medicare source link → instant `doc.save()`.

**Word — `docx`.** Mirrors the PDF (banner, table, `ExternalHyperlink`),
produced as a Blob and downloaded via an object URL.

---

## 6. Component map

| File | Responsibility |
|---|---|
| `src/App.jsx` | State, fetch orchestration, layout |
| `src/api/cms.js` | Client wrapper around `/api/cms` |
| `src/lib/buildReport.js` | Merge CMS + manual → report model |
| `src/lib/exportPdf.js` | jsPDF report |
| `src/lib/exportDocx.js` | Word report |
| `src/config/fieldMap.js` | **Central** CMS-field → label mapping |
| `src/components/*` | BrandingHeader, CcnLookupForm, ManualInputs, ReportPreview, MetricCards, MetricsChart |
| `netlify/functions/cms.js` | Serverless CMS proxy |

---

## 7. Failure handling

| Case | Behavior |
|---|---|
| Empty CCN | Inline "Please enter a CCN." |
| CCN matches nothing (0 rows) | "Facility not found — check the CCN." |
| Proxy / CMS error | Error banner with the message; download stays disabled |
| Missing individual field | Renders `N/A`, report still generates |
| Loading | Spinner on the button; downloads disabled until success |

---

## 8. Trade-offs & assumptions

- **Live data ≠ sample PDF.** The sample is a layout reference; CMS is the
  source of truth (live: 150 beds / overall 5 vs. sample 120 / 1).
- **`adjusted_score`** (risk-adjusted, used in CMS five-star) is the displayed
  facility metric value.
- **State management:** plain `useState` — Redux would be over-engineering here.
- **Averages fetched whole** (~54 rows) and filtered client-side — simpler than
  parameterizing the proxy per state.
- **No persistence/auth** — single-session tool; nothing is stored.

---

## 9. Possible extensions (not built)

- Cache CMS responses at the edge to cut repeat latency.
- Code-split the PDF/Word/chart libraries (current bundle ~1.2 MB).
- Batch lookups (CSV of CCNs → multiple reports).

---

## 10. Walkthrough cheat-sheet (questions I expect)

- **Why a serverless proxy?** The CMS Provider Data Catalog API sends no CORS
  headers, so a direct browser `fetch` is blocked. `/api/cms` (Netlify Function in
  prod, Vite middleware in dev) calls CMS server-side and relays JSON. It also
  keeps dataset IDs server-side and gives one place to handle upstream errors.
- **Why `adjusted_score`?** It's the risk-adjusted value CMS itself uses in the
  five-star methodology — the fair facility-vs-benchmark comparison.
- **How do the 12 metrics map?** 4 claims measures (521/522 short-stay,
  551/552 long-stay), each emitting facility + national + state rows. STR→Short-Stay,
  LT→Long-Stay per the brief. All mapping lives in `src/config/fieldMap.js`.
- **The INFINITE guardrail.** "INFINITE" is a static brand and is *never* replaced
  by the facility name; the facility name appears only under "Name of Facility".
  Enforced in the preview and both exporters.
- **QA verdict logic.** Lower = better for hospitalization/ED; `buildReport()`
  derives `verdictNational`/`verdictState` and a roll-up `qaSummary`. Pure +
  unit-tested.
- **Data quality.** `dataQuality()` reports CMS field completeness, freshness
  (`processing_date`), and missing-field flags — the "verify before you trust" lens.
- **Why live data differs from the sample PDF.** Sample is a layout reference;
  CMS is the source of truth (live: 150 beds / overall 5 vs. sample 120 / 1).
- **Testing.** `npm test` → 25 unit tests across `buildReport`, benchmark verdicts,
  `medicareUrl`, and `dataQuality`.
