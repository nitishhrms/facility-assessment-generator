import { useMemo, useState } from 'react';
import { parseCcns, runBatch, buildZipBlob, toSummaryCsv, downloadBlob } from '../lib/batch';

// Batch mode: upload/paste a list of CCNs, generate every report at once, and
// download a ZIP of PDFs + a roll-up summary CSV. Reuses the single-report core.
export default function BatchUpload() {
  const [text, setText] = useState('');
  const [status, setStatus] = useState('idle'); // idle | running | done
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [results, setResults] = useState([]);
  const [building, setBuilding] = useState(false);

  const ccns = useMemo(() => parseCcns(text), [text]);

  const counts = useMemo(() => {
    const by = { ok: 0, notfound: 0, error: 0 };
    for (const r of results) by[r.status] = (by[r.status] || 0) + 1;
    return by;
  }, [results]);

  function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ''));
    reader.readAsText(file);
  }

  async function handleRun() {
    if (!ccns.length) return;
    setStatus('running');
    setResults([]);
    setProgress({ done: 0, total: ccns.length });
    const res = await runBatch(ccns, {
      concurrency: 5,
      onProgress: (done, total) => setProgress({ done, total }),
    });
    setResults(res);
    setStatus('done');
  }

  async function handleZip() {
    setBuilding(true);
    try {
      const blob = await buildZipBlob(results);
      downloadBlob(blob, `facility_reports_${new Date().toISOString().slice(0, 10)}.zip`);
    } finally {
      setBuilding(false);
    }
  }

  function handleCsv() {
    downloadBlob(new Blob([toSummaryCsv(results)], { type: 'text/csv' }), 'facility_summary.csv');
  }

  const pct = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <section className="card p-6">
      <h2 className="text-lg font-semibold">Batch Reports</h2>
      <p className="mt-1 text-sm text-subtle">
        Upload or paste a list of CCNs (one per line, or a CSV with a <code>ccn</code> column)
        to generate every report at once and download them as a ZIP.
      </p>

      <div className="mt-4 flex flex-col gap-3">
        <input
          type="file"
          accept=".csv,.txt"
          onChange={handleFile}
          className="text-sm text-subtle file:mr-3 file:rounded-lg file:border-0 file:bg-neutral-100 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-neutral-200"
          aria-label="Upload CSV of CCNs"
        />
        <textarea
          className="field-input h-28 font-mono text-sm"
          placeholder={'686123\n015009\n105007'}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label="CCNs"
        />

        <div className="flex flex-wrap items-center gap-3">
          <button
            className="btn-primary sm:w-48"
            onClick={handleRun}
            disabled={!ccns.length || status === 'running'}
          >
            {status === 'running' ? `Processing… ${pct}%` : `Generate ${ccns.length || ''} Report${ccns.length === 1 ? '' : 's'}`.trim()}
          </button>
          <span className="text-sm text-subtle">
            {ccns.length} valid CCN{ccns.length === 1 ? '' : 's'} detected
          </span>
        </div>

        {status === 'running' && (
          <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
            <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
          </div>
        )}

        {status === 'done' && (
          <div className="flex flex-col gap-3">
            <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm">
              <span className="font-semibold text-emerald-700">{counts.ok} ok</span>
              {counts.notfound ? <span className="ml-3 text-amber-700">{counts.notfound} not found</span> : null}
              {counts.error ? <span className="ml-3 text-red-700">{counts.error} error</span> : null}
            </div>

            <div className="max-h-48 overflow-auto rounded-xl border border-neutral-200">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-neutral-50 text-xs uppercase tracking-wide text-subtle">
                  <tr>
                    <th className="px-3 py-2">CCN</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Facility</th>
                    <th className="px-3 py-2">QA</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr key={r.ccn} className="border-t border-neutral-100">
                      <td className="px-3 py-1.5 font-mono">{r.ccn}</td>
                      <td className="px-3 py-1.5">
                        <StatusChip status={r.status} />
                      </td>
                      <td className="px-3 py-1.5">{r.name || (r.error ?? '—')}</td>
                      <td className="px-3 py-1.5 text-subtle">
                        {r.completeness != null ? `${r.completeness}% complete` : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <button className="btn-primary" onClick={handleZip} disabled={building || !counts.ok}>
                {building ? 'Building ZIP…' : '⬇ Download ZIP (PDFs + summary)'}
              </button>
              <button className="btn-secondary" onClick={handleCsv}>
                ⬇ Download summary CSV
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function StatusChip({ status }) {
  const map = {
    ok: 'bg-emerald-50 text-emerald-700',
    notfound: 'bg-amber-50 text-amber-700',
    error: 'bg-red-50 text-red-700',
  };
  const label = { ok: 'ok', notfound: 'not found', error: 'error' }[status] || status;
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${map[status] || ''}`}>{label}</span>;
}
