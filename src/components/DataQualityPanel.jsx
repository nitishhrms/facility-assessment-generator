// QA / Data Validation panel — shows how complete and how fresh the CMS source
// data is, and flags any missing fields. This is the "QA Analytics" lens: trust,
// but verify the data before acting on it.
import { dataQuality } from '../lib/dataQuality';

export default function DataQualityPanel({ report }) {
  const dq = dataQuality(report);
  if (!dq) return null;

  const complete = dq.status === 'complete';
  const barColor = dq.completeness >= 90 ? 'bg-emerald-500' : dq.completeness >= 70 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <section className="card p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Data Quality</h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
            complete ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
          }`}
        >
          {complete ? 'All CMS fields present' : `${dq.missing.length} field(s) missing`}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-canvas">
          <div className={`h-full rounded-full ${barColor}`} style={{ width: `${dq.completeness}%` }} />
        </div>
        <span className="text-sm font-semibold tabular-nums">{dq.completeness}%</span>
      </div>

      <p className="mt-2 text-xs text-subtle">
        {dq.populated} of {dq.total} CMS fields populated
        {dq.processingDate ? ` · CMS data as of ${dq.processingDate}` : ''}
      </p>

      {dq.missing.length > 0 && (
        <p className="mt-2 text-xs text-amber-700">
          Missing from CMS: {dq.missing.join(', ')}
        </p>
      )}
    </section>
  );
}
