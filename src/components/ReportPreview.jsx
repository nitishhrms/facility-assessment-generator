// On-screen snapshot table that mirrors the generated PDF/Word layout exactly.
export default function ReportPreview({ report }) {
  return (
    <section className="card overflow-hidden">
      <div className="border-b border-hairline px-6 py-4">
        <div className="text-center text-lg font-bold tracking-tight">
          <span className="text-brand-pink">INFINITE</span>
          <span className="ml-2 text-xs font-semibold text-brand-blue">Managed by MEDELITE</span>
        </div>
        <div className="mt-1 text-center text-[11px] font-semibold uppercase tracking-[0.18em] text-subtle">
          Facility Assessment Snapshot{report.state ? ` · ${report.state}` : ''}
        </div>
      </div>

      <table className="w-full text-sm">
        <tbody>
          {report.tableRows.map(([label, value], i) => (
            <tr key={label} className={i % 2 ? 'bg-canvas/40' : ''}>
              <th
                scope="row"
                className="w-1/2 border-b border-hairline px-6 py-2.5 text-left font-medium text-[#3c3c43] align-top"
              >
                {label}
              </th>
              <td className="border-b border-hairline px-6 py-2.5 tabular-nums">{value}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="px-6 py-4 text-xs text-subtle">
        Source:{' '}
        <a
          href={report.medicareUrl}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-accent hover:underline"
        >
          View official Medicare Care Compare profile →
        </a>
      </div>
    </section>
  );
}
