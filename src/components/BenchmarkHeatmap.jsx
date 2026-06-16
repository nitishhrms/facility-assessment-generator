// Bonus: heatmap of the facility's gap to each benchmark. Rows = the 4
// hospitalization/ED measures; the "vs State" / "vs National" cells are
// heat-colored — green when the facility is BELOW the benchmark (lower = better
// for these measures), red when above, intensity scaled by the % gap.
const NA = 'N/A';

// delta = facility - benchmark (negative = better). Returns an inline style.
function heatStyle(delta, benchmark) {
  if (delta == null || benchmark == null || benchmark === 0) return { backgroundColor: '#f5f5f7', color: '#9ca3af' };
  const pct = delta / Math.abs(benchmark);          // signed fractional gap
  const intensity = Math.min(1, Math.abs(pct) / 0.5); // 50% gap -> full color
  const alpha = (0.12 + 0.55 * intensity).toFixed(2);
  const rgb = delta < 0 ? '16, 185, 129' : '239, 68, 68'; // green better / red worse
  return { backgroundColor: `rgba(${rgb}, ${alpha})`, color: '#1d1d1f' };
}

function fmtDelta(delta, unit) {
  if (delta == null) return NA;
  const sign = delta > 0 ? '+' : '';
  return `${sign}${delta.toFixed(2)}${unit}`;
}

export default function BenchmarkHeatmap({ metrics }) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold">Performance Heatmap</h3>
      <p className="mb-3 mt-0.5 text-xs text-subtle">
        Facility gap to each benchmark — <span className="text-emerald-600">green = better</span>,{' '}
        <span className="text-red-600">red = worse</span> (lower is better).
      </p>

      <div className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-1 text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wide text-subtle">
              <th className="px-2 py-1 text-left font-medium">Measure</th>
              <th className="px-2 py-1 text-right font-medium">Facility</th>
              <th className="px-2 py-1 text-center font-medium">vs State</th>
              <th className="px-2 py-1 text-center font-medium">vs National</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr key={m.code}>
                <td className="px-2 py-1.5 font-medium text-ink">
                  {m.shortName}
                  <span className="ml-1 text-xs text-subtle">{m.unit || '/1k'}</span>
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums">{m.facilityText}</td>
                <td className="rounded-md px-2 py-1.5 text-center tabular-nums" style={heatStyle(m.vsState, m.state)}>
                  {fmtDelta(m.vsState, m.unit)}
                </td>
                <td className="rounded-md px-2 py-1.5 text-center tabular-nums" style={heatStyle(m.vsNational, m.national)}>
                  {fmtDelta(m.vsNational, m.unit)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
