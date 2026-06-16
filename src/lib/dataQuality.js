// QA / data-validation summary over a built report model.
// The "QA Analytics" value-add: before trusting a facility's numbers, state how
// COMPLETE and how FRESH the underlying CMS data is, and flag anything missing.
// Pure function (no I/O) so it is trivial to unit-test.

import { NA } from './buildReport.js';
import { RATING_FIELDS, CLAIMS_MEASURES } from '../config/fieldMap.js';

// The report fields that come from the CMS API (not manual entry). Data quality
// is a statement about the SOURCE data, so manual inputs are excluded.
const CMS_LABELS = [
  'Location',
  'Census Capacity',
  ...RATING_FIELDS.map((r) => r.label),
  ...CLAIMS_MEASURES.flatMap((m) => [m.facilityLabel, m.nationalLabel, m.stateLabel]),
];

export function dataQuality(report) {
  if (!report) return null;

  const valueByLabel = Object.fromEntries(report.tableRows);
  const checked = CMS_LABELS.map((label) => ({
    label,
    value: valueByLabel[label],
    ok: valueByLabel[label] !== undefined && valueByLabel[label] !== NA,
  }));

  const populated = checked.filter((c) => c.ok).length;
  const total = checked.length;
  const missing = checked.filter((c) => !c.ok).map((c) => c.label);
  const completeness = total ? Math.round((populated / total) * 100) : 0;

  return {
    populated,
    total,
    completeness, // 0–100
    missing,
    processingDate: report.processingDate || null,
    status: missing.length === 0 ? 'complete' : 'partial',
  };
}
