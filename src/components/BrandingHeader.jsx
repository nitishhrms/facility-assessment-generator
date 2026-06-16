// Mandatory corporate branding banner.
// GUARDRAIL: "INFINITE" is the static internal platform brand and must NEVER
// be replaced by the facility name. The facility name only appears in the
// report body under "Name of Facility".
export default function BrandingHeader({ state }) {
  return (
    <header className="sticky top-0 z-10 border-b border-hairline bg-white/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-3xl flex-col items-center px-6 py-5 text-center">
        <div className="text-2xl font-bold tracking-tight">
          <span className="text-brand-pink">INFINITE</span>
          <span className="ml-2 align-middle text-sm font-semibold text-brand-blue">
            Managed by MEDELITE
          </span>
        </div>
        <h1 className="mt-2 text-[13px] font-semibold uppercase tracking-[0.18em] text-subtle">
          Facility Assessment Snapshot
        </h1>
        {state ? (
          <span className="mt-1 rounded-full bg-canvas px-3 py-0.5 text-xs font-semibold text-ink">
            {state}
          </span>
        ) : null}
      </div>
    </header>
  );
}
