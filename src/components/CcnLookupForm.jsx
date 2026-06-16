import { useState } from 'react';

// A nursing-home CCN is exactly 6 digits (e.g. 686123).
const CCN_PATTERN = /^\d{6}$/;

// CCN lookup: input + fetch button + status feedback (spinner / not-found / error).
export default function CcnLookupForm({ ccn, setCcn, status, error, onFetch }) {
  const loading = status === 'loading';
  const [validationError, setValidationError] = useState('');

  // Validate client-side BEFORE hitting the API — a malformed CCN can never
  // match, so block it with a clear hint instead of a wasted round-trip.
  function handleSubmit(e) {
    e.preventDefault();
    const clean = ccn.trim();
    if (!CCN_PATTERN.test(clean)) {
      setValidationError('Enter a valid 6-digit CCN (e.g. 686123).');
      return;
    }
    setValidationError('');
    onFetch(e);
  }

  function handleChange(e) {
    // Keep digits only and cap at 6 — the input can't hold an invalid CCN.
    setCcn(e.target.value.replace(/\D/g, '').slice(0, 6));
    if (validationError) setValidationError('');
  }

  return (
    <section className="card p-6">
      <h2 className="text-lg font-semibold">Facility Lookup</h2>
      <p className="mt-1 text-sm text-subtle">
        Enter a CMS Certification Number (CCN) to pull live public data.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          className="field-input flex-1"
          inputMode="numeric"
          maxLength={6}
          placeholder="e.g. 686123"
          value={ccn}
          onChange={handleChange}
          aria-label="CCN"
          aria-invalid={!!validationError}
        />
        <button type="submit" className="btn-primary sm:w-40" disabled={loading}>
          {loading ? (
            <>
              <Spinner /> Fetching…
            </>
          ) : (
            'Fetch Data'
          )}
        </button>
      </form>

      {validationError && <Banner tone="warn">{validationError}</Banner>}
      {status === 'notfound' && (
        <Banner tone="warn">
          Facility not found — please check the CCN and try again.
        </Banner>
      )}
      {status === 'error' && (
        <Banner tone="error">{error || 'Something went wrong. Please try again.'}</Banner>
      )}
      {status === 'success' && (
        <Banner tone="ok">Facility data loaded. Review the report below.</Banner>
      )}
    </section>
  );
}

function Spinner() {
  return (
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
  );
}

function Banner({ tone, children }) {
  const tones = {
    ok: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warn: 'bg-amber-50 text-amber-700 border-amber-200',
    error: 'bg-red-50 text-red-700 border-red-200',
  };
  return (
    <div className={`mt-4 rounded-xl border px-4 py-2.5 text-sm ${tones[tone]}`}>
      {children}
    </div>
  );
}
