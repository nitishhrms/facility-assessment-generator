// Star-rating cards (bonus: responsive data cards), color-coded by performance:
// 4-5 stars = green, 3 = amber, 1-2 = red, missing = neutral.
const TONE = {
  good: { card: 'border-emerald-200 bg-emerald-50/60', num: 'text-emerald-700', star: 'text-emerald-500' },
  mid: { card: 'border-amber-200 bg-amber-50/60', num: 'text-amber-700', star: 'text-amber-500' },
  low: { card: 'border-red-200 bg-red-50/60', num: 'text-red-700', star: 'text-red-500' },
  na: { card: 'border-neutral-200', num: 'text-ink', star: 'text-hairline' },
};

function toneFor(value) {
  if (value == null) return TONE.na;
  if (value >= 4) return TONE.good;
  if (value === 3) return TONE.mid;
  return TONE.low;
}

export default function MetricCards({ ratings }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {ratings.map((r) => {
        const tone = toneFor(r.value);
        return (
          <div key={r.label} className={`card border p-4 ${tone.card}`}>
            <div className="text-xs font-medium text-subtle">{r.label}</div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className={`text-3xl font-semibold tabular-nums ${tone.num}`}>
                {r.value ?? '—'}
              </span>
              <span className="text-sm text-subtle">/ 5</span>
            </div>
            <Stars value={r.value} starClass={tone.star} />
          </div>
        );
      })}
    </div>
  );
}

function Stars({ value, starClass }) {
  const n = Math.round(value || 0);
  return (
    <div className="mt-2 flex gap-0.5" aria-hidden>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= n ? starClass : 'text-hairline'}>
          ★
        </span>
      ))}
    </div>
  );
}
