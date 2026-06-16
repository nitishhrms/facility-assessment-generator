// Bonus: hospitalization/ED comparison (facility vs state vs national).
// Split into TWO charts by unit so the scales are comparable — short-stay
// metrics are percentages (~15-25), long-stay are per-1,000 resident days
// (~1-3); plotting them on one axis would crush the long-stay bars.
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

export default function MetricsChart({ metrics }) {
  const shortStay = metrics.filter((m) => m.group === 'Short Stay');
  const longStay = metrics.filter((m) => m.group === 'Long Stay');

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold">Hospitalization &amp; ED — Facility vs Averages</h3>
      <p className="mb-3 mt-0.5 text-xs text-subtle">
        Lower is better. Short-stay measures are percentages; long-stay are per 1,000 resident days.
      </p>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <GroupedBars title="Short-Stay (STR)" unit="%" metrics={shortStay} />
        <GroupedBars title="Long-Stay (LT)" unit=" per 1k" metrics={longStay} />
      </div>

      {/* QA verdict per measure vs the national benchmark (lower = better). */}
      <div className="mt-4 flex flex-wrap gap-2">
        {metrics.map((m) => (
          <VerdictChip key={m.code} label={m.shortName} verdict={m.verdictNational} />
        ))}
      </div>
    </div>
  );
}

function GroupedBars({ title, unit, metrics }) {
  const data = metrics.map((m) => ({
    name: m.shortName,
    Facility: m.facility,
    State: m.state,
    National: m.national,
  }));
  const hasData = data.some((d) => d.Facility != null || d.State != null || d.National != null);

  return (
    <div>
      <div className="mb-1 text-xs font-medium text-subtle">{title}</div>
      {hasData ? (
        <div className="h-60 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ececef" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6e6e73' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#6e6e73' }} axisLine={false} tickLine={false} />
              <Tooltip
                formatter={(v) => (v == null ? 'N/A' : `${v}${unit}`)}
                contentStyle={{ borderRadius: 12, border: '1px solid #d2d2d7', fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Facility" fill="#0071e3" radius={[4, 4, 0, 0]} />
              <Bar dataKey="State" fill="#9ca3af" radius={[4, 4, 0, 0]} />
              <Bar dataKey="National" fill="#1d1d1f" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex h-60 items-center justify-center rounded-xl bg-neutral-50 text-xs text-subtle">
          No benchmark data available
        </div>
      )}
    </div>
  );
}

function VerdictChip({ label, verdict }) {
  const styles = {
    better: { cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', text: '↓ better than national' },
    worse: { cls: 'bg-red-50 text-red-700 border-red-200', text: '↑ worse than national' },
    same: { cls: 'bg-gray-50 text-gray-600 border-gray-200', text: '= at national avg' },
    na: { cls: 'bg-gray-50 text-gray-400 border-gray-200', text: 'no benchmark' },
  };
  const s = styles[verdict] || styles.na;
  return (
    <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${s.cls}`}>
      <span className="font-semibold">{label}</span> · {s.text}
    </span>
  );
}
