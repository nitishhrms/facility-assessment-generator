// Batch engine: turn a list of CCNs into many reports at once, then package
// them as a ZIP of PDFs + a roll-up summary CSV. Reuses the exact same
// extraction (api/cms) and transform (buildReport) as the single-report flow.

import JSZip from 'jszip';
import { fetchProvider, fetchClaims, fetchAverages } from '../api/cms';
import { buildReport } from './buildReport';
import { dataQuality } from './dataQuality';
import { buildPdfDoc, pdfFileName } from './exportPdf';

// Parse CCNs from pasted text or a CSV. Takes the first column of each line,
// keeps valid 6-digit CCNs, skips a header row, and de-duplicates (order kept).
export function parseCcns(text) {
  if (!text) return [];
  const seen = new Set();
  const out = [];
  for (const line of text.split(/\r?\n/)) {
    const first = (line.split(',')[0] || '').trim();
    if (/^\d{6}$/.test(first) && !seen.has(first)) {
      seen.add(first);
      out.push(first);
    }
  }
  return out;
}

// Process many CCNs with a bounded concurrency pool (default 5 in flight) so we
// respect the CMS API. The averages dataset is fetched ONCE and reused.
// One failed CCN never aborts the run — it's recorded and the batch continues.
export async function runBatch(ccns, { concurrency = 5, onProgress } = {}) {
  const averages = await fetchAverages();
  const results = new Array(ccns.length);
  let nextIndex = 0;
  let completed = 0;

  async function worker() {
    while (nextIndex < ccns.length) {
      const i = nextIndex++;
      const ccn = ccns[i];
      try {
        const [provider, claims] = await Promise.all([fetchProvider(ccn), fetchClaims(ccn)]);
        if (!provider) {
          results[i] = { ccn, status: 'notfound' };
        } else {
          const report = buildReport(provider, claims, averages, {});
          const dq = dataQuality(report);
          results[i] = {
            ccn,
            status: 'ok',
            name: report.name,
            report,
            completeness: dq?.completeness ?? null,
          };
        }
      } catch (err) {
        results[i] = { ccn, status: 'error', error: err?.message || String(err) };
      }
      completed += 1;
      onProgress?.(completed, ccns.length, results[i]);
    }
  }

  const pool = Array.from({ length: Math.min(concurrency, ccns.length) }, worker);
  await Promise.all(pool);
  return results;
}

// CSV-safe cell (quote if it contains a comma, quote, or newline).
function csvCell(value) {
  const s = String(value ?? '');
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// Roll-up summary CSV across all results (one row per CCN).
export function toSummaryCsv(results) {
  const header = ['ccn', 'status', 'name', 'state', 'overall_rating', 'qa_summary', 'completeness', 'error'];
  const rows = results.map((r) => {
    const rep = r.report;
    const overall = rep?.ratings?.find((x) => x.label === 'Overall Star Rating')?.text ?? '';
    return [
      r.ccn,
      r.status,
      rep?.name ?? '',
      rep?.state ?? '',
      overall,
      rep?.qaSummary ?? '',
      r.completeness ?? '',
      r.error ?? '',
    ];
  });
  return [header, ...rows].map((cells) => cells.map(csvCell).join(',')).join('\n');
}

// Build a ZIP blob: a PDF per successful facility + the summary CSV.
export async function buildZipBlob(results) {
  const zip = new JSZip();
  const folder = zip.folder('reports');
  for (const r of results) {
    if (r.status === 'ok' && r.report) {
      folder.file(pdfFileName(r.report), buildPdfDoc(r.report).output('arraybuffer'));
    }
  }
  zip.file('summary.csv', toSummaryCsv(results));
  return zip.generateAsync({ type: 'blob' });
}

// Trigger a browser download for a Blob.
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
