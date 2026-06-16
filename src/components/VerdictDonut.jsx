// Bonus: donut chart summarizing how the facility's hospitalization/ED measures
// stack up against the NATIONAL benchmark — a parts-of-a-whole view of the
// 4 measures (better / at / worse / no data). Lower is better for these measures.
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const SEGMENTS = [
  { key: 'better', label: 'Better than national', color: '#10b981' },
  { key: 'same', label: 'At national avg', color: '#9ca3af' },
  { key: 'worse', label: 'Worse than national', color: '#ef4444' },
  { key: 'na', label: 'No benchmark', color: '#e5e7eb' },
];

export default function VerdictDonut({ metrics }) {
  const counts = metrics.reduce((acc, m) => {
    acc[m.verdictNational] = (acc[m.verdictNational] || 0) + 1;
    return acc;
  }, {});
  const data = SEGMENTS.map((s) => ({ ...s, value: counts[s.key] || 0 })).filter((s) => s.value > 0);

  const scored = metrics.filter((m) => m.verdictNational !== 'na').length;
  const betterOrSame = (counts.better || 0) + (counts.same || 0);

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold">Benchmark Breakdown</h3>
      <p className="mb-2 mt-0.5 text-xs text-subtle">Measures vs. national average</p>

      <div className="flex items-center gap-4">
        <div className="relative h-40 w-40 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="label"
                innerRadius={48}
                outerRadius={72}
                paddingAngle={2}
                stroke="none"
              >
                {data.map((d) => (
                  <Cell key={d.key} fill={d.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v, n) => [`${v} measure${v === 1 ? '' : 's'}`, n]} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-semibold tabular-nums">
              {scored ? `${betterOrSame}/${scored}` : '—'}
            </span>
            <span className="text-[10px] text-subtle">at/better</span>
          </div>
        </div>

        <ul className="flex-1 space-y-1.5">
          {SEGMENTS.map((s) => (
            <li key={s.key} className="flex items-center gap-2 text-xs">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: s.color }} />
              <span className="text-ink">{s.label}</span>
              <span className="ml-auto font-semibold tabular-nums text-subtle">{counts[s.key] || 0}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
