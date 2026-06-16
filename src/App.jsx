import { useMemo, useState } from 'react';
import BrandingHeader from './components/BrandingHeader';
import CcnLookupForm from './components/CcnLookupForm';
import ManualInputs from './components/ManualInputs';
import ReportPreview from './components/ReportPreview';
import MetricCards from './components/MetricCards';
import MetricsChart from './components/MetricsChart';
import VerdictDonut from './components/VerdictDonut';
import BenchmarkHeatmap from './components/BenchmarkHeatmap';
import AiInsights from './components/AiInsights';
import DataQualityPanel from './components/DataQualityPanel';
import BatchUpload from './components/BatchUpload';
import ChatPanel from './components/ChatPanel';
import { fetchProvider, fetchClaims, fetchAverages } from './api/cms';
import { buildReport } from './lib/buildReport';
import { exportPdf } from './lib/exportPdf';
import { exportDocx } from './lib/exportDocx';
import { DEFAULT_MANUAL } from './config/fieldMap';

export default function App() {
  const [ccn, setCcn] = useState('');
  const [status, setStatus] = useState('idle'); // idle | loading | success | notfound | error
  const [error, setError] = useState('');
  const [provider, setProvider] = useState(null);
  const [claims, setClaims] = useState([]);
  const [averages, setAverages] = useState([]);
  const [manual, setManual] = useState(DEFAULT_MANUAL);
  const [tab, setTab] = useState('report'); // 'report' | 'assistant'
  // The chat assistant needs the separate Python backend, which isn't hosted on
  // Netlify. Show its tab in local dev, or in prod only once a backend URL is set.
  const chatEnabled = import.meta.env.DEV || Boolean(import.meta.env.VITE_CHAT_API_URL);

  async function handleFetch(e) {
    e?.preventDefault();
    const clean = ccn.trim();
    if (!clean) {
      setStatus('error');
      setError('Please enter a CCN.');
      return;
    }
    setStatus('loading');
    setError('');
    try {
      const [p, c, a] = await Promise.all([
        fetchProvider(clean),
        fetchClaims(clean),
        fetchAverages(),
      ]);
      if (!p) {
        setProvider(null);
        setStatus('notfound');
        return;
      }
      setProvider(p);
      setClaims(c);
      setAverages(a);
      setStatus('success');
    } catch (err) {
      setStatus('error');
      setError(err.message || 'Something went wrong.');
    }
  }

  const report = useMemo(
    () => (status === 'success' ? buildReport(provider, claims, averages, manual) : null),
    [status, provider, claims, averages, manual]
  );

  return (
    <div className="min-h-screen">
      <BrandingHeader state={report?.state} />

      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-8">
        <div className="text-center">
          <h2 className="text-3xl font-semibold tracking-tight">Facility Assessment Report Generator</h2>
          <p className="mx-auto mt-2 max-w-xl text-subtle">
            Look up any skilled nursing facility by CCN, merge in your operational
            notes, and export a polished, print-ready report.
          </p>
        </div>

        {chatEnabled && (
          <>
            <div className="flex justify-center gap-1 rounded-xl bg-neutral-100 p-1">
              {[
                ['report', 'Report Generator'],
                ['assistant', 'Healthcare Assistant'],
              ].map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium transition ${
                    tab === key ? 'bg-white text-ink shadow-sm' : 'text-subtle hover:text-ink'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {tab === 'assistant' && <ChatPanel />}
          </>
        )}

        {tab === 'report' && (
          <>
            <CcnLookupForm
              ccn={ccn}
              setCcn={setCcn}
              status={status}
              error={error}
              onFetch={handleFetch}
            />

        <ManualInputs
          manual={manual}
          setManual={setManual}
          officialName={provider?.provider_name}
        />

        {report ? (
          <>
            {report.qaSummary && (
              <div className="card border-l-4 border-l-accent bg-accent/[0.03] px-5 py-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-accent">
                  QA Summary
                </div>
                <p className="mt-1 text-sm text-ink">{report.qaSummary}</p>
              </div>
            )}

            <AiInsights report={report} />
            <DataQualityPanel report={report} />
            <MetricCards ratings={report.ratings} />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <VerdictDonut metrics={report.metrics} />
              <BenchmarkHeatmap metrics={report.metrics} />
            </div>
            <MetricsChart metrics={report.metrics} />

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <button className="btn-primary" onClick={() => exportPdf(report)}>
                ⬇ Download PDF
              </button>
              <button className="btn-secondary" onClick={() => exportDocx(report)}>
                ⬇ Download Word (.docx)
              </button>
            </div>

            <ReportPreview report={report} />
          </>
        ) : (
          <div className="card p-10 text-center text-subtle">
            Enter a CCN above (try <span className="font-semibold text-ink">686123</span>) to
            generate a report.
          </div>
        )}

        <div className="my-2 flex items-center gap-3 text-xs uppercase tracking-wide text-subtle">
          <span className="h-px flex-1 bg-neutral-200" />
          or process many at once
          <span className="h-px flex-1 bg-neutral-200" />
        </div>

        <BatchUpload />
          </>
        )}

        <footer className="pb-6 pt-2 text-center text-xs text-subtle">
          Public data via the CMS Provider Data Catalog. Star ratings and metrics
          reflect the latest CMS publication.
        </footer>
      </main>
    </div>
  );
}
