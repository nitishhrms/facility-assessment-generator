import { useState } from 'react';

// Bonus (the brief: "AI USE IS ENCOURAGED"): an on-demand AI assessment of the
// facility. Posts the report summary to the /api/insights serverless function,
// which calls Claude server-side and returns a short analyst-style takeaway.
export default function AiInsights({ report }) {
  const [status, setStatus] = useState('idle'); // idle | loading | done | error
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  async function run() {
    setStatus('loading');
    setError('');
    try {
      const res = await fetch('/api/insights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: report.name,
          state: report.state,
          ratings: report.ratings,
          metrics: report.metrics,
          qaSummary: report.qaSummary,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status}).`);
      setText(data.insight || 'No insight returned.');
      setStatus('done');
    } catch (e) {
      setError(e.message || 'Something went wrong.');
      setStatus('error');
    }
  }

  return (
    <section className="card border-l-4 border-l-accent bg-accent/[0.03] p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">AI Assessment</h3>
          <p className="text-xs text-subtle">A Claude-generated partnership takeaway from this facility's data.</p>
        </div>
        <button className="btn-primary shrink-0 px-4" onClick={run} disabled={status === 'loading'}>
          {status === 'loading' ? 'Analyzing…' : status === 'done' ? '↻ Regenerate' : '✨ Generate'}
        </button>
      </div>

      {status === 'done' && (
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink">{text}</p>
      )}
      {status === 'error' && (
        <p className="mt-3 text-sm text-red-700">⚠ {error}</p>
      )}
    </section>
  );
}
