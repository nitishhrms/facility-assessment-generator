// Manual operational inputs — metrics that do not live in the public CMS DB.
import { MANUAL_FIELDS } from '../config/fieldMap';

export default function ManualInputs({ manual, setManual, officialName }) {
  const update = (key, value) => setManual((m) => ({ ...m, [key]: value }));

  return (
    <section className="card p-6">
      <h2 className="text-lg font-semibold">Operational Inputs</h2>
      <p className="mt-1 text-sm text-subtle">
        Internal fields that are merged with the public CMS data.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {MANUAL_FIELDS.map((f) => (
          <div key={f.key} className={f.key === 'overrideName' ? 'sm:col-span-2' : ''}>
            <label className="mb-1 block text-sm font-medium text-ink">{f.label}</label>

            {f.type === 'select' ? (
              <select
                className="field-input"
                value={manual[f.key]}
                onChange={(e) => update(f.key, e.target.value)}
              >
                {f.options.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="field-input"
                type={f.type}
                placeholder={
                  f.key === 'overrideName' && officialName
                    ? `Default: ${officialName}`
                    : f.placeholder
                }
                value={manual[f.key]}
                onChange={(e) => update(f.key, e.target.value)}
              />
            )}

            {f.hint && <p className="mt-1 text-xs text-subtle">{f.hint}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}
