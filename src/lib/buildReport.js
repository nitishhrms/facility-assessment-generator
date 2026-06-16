// Merges CMS API data + manual operational inputs into ONE normalized report
// model that the on-screen preview, the PDF, and the Word export all consume.

import { CLAIMS_MEASURES, RATING_FIELDS, medicareUrl } from '../config/fieldMap.js';

export const NA = 'N/A';

function toNum(v) {
  if (v === '' || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

function fmt(v, decimals, unit = '') {
  const n = toNum(v);
  return n === null ? NA : `${n.toFixed(decimals)}${unit}`;
}

// For every hospitalization / ED measure, a LOWER value is better (fewer
// hospitalizations / ED visits). Compare the facility value to a benchmark and
// return a QA verdict the rest of the app can render and export.
//   below benchmark -> 'better', above -> 'worse', tied/missing -> 'same'/'na'.
function verdictVs(facility, benchmark) {
  if (facility === null || benchmark === null) return 'na';
  if (facility < benchmark) return 'better';
  if (facility > benchmark) return 'worse';
  return 'same';
}

function composeLocation(p) {
  // Build from discrete address parts for predictable formatting. The raw CMS
  // `location` field is a geocoded string (no spacing), so we only fall back
  // to it if the parts are unavailable.
  const cityStateZip = [p.citytown, [p.state, p.zip_code].filter(Boolean).join(' ')]
    .filter(Boolean)
    .join(', ');
  const composed = [p.provider_address, cityStateZip].filter(Boolean).join(', ');
  return composed || p.location || NA;
}

export function buildReport(provider, claims, averages, manual) {
  if (!provider) return null;

  const state = provider.state || '';
  const ccn = provider.cms_certification_number_ccn || '';

  // Name of Facility: manual override wins, else official CMS legal name.
  const officialName = provider.provider_name || NA;
  const name = (manual.overrideName || '').trim() || officialName;

  // Star ratings.
  const ratings = RATING_FIELDS.map((f) => ({
    label: f.label,
    value: toNum(provider[f.key]),
    text: provider[f.key] ? String(provider[f.key]) : NA,
  }));

  // Averages: find the NATION row and the facility's state row.
  const nation = averages.find((r) => r.state_or_nation === 'NATION') || {};
  const stateRow = averages.find((r) => r.state_or_nation === state) || {};
  const claimByCode = Object.fromEntries(claims.map((c) => [c.measure_code, c]));

  const metrics = CLAIMS_MEASURES.map((m) => {
    const facilityRaw = claimByCode[m.code]?.adjusted_score;
    const facility = toNum(facilityRaw);
    const national = toNum(nation[m.avgColumn]);
    const state = toNum(stateRow[m.avgColumn]);
    return {
      code: m.code,
      group: m.group,
      shortName: m.shortName,
      unit: m.unit,
      facilityLabel: m.facilityLabel,
      nationalLabel: m.nationalLabel,
      stateLabel: m.stateLabel,
      facility,
      national,
      state,
      facilityText: fmt(facilityRaw, m.decimals, m.unit),
      nationalText: fmt(nation[m.avgColumn], m.decimals, m.unit),
      stateText: fmt(stateRow[m.avgColumn], m.decimals, m.unit),
      // QA analytics: facility vs benchmark (lower is better for these measures).
      vsNational: national === null || facility === null ? null : facility - national,
      vsState: state === null || facility === null ? null : facility - state,
      verdictNational: verdictVs(facility, national),
      verdictState: verdictVs(facility, state),
    };
  });

  // Headline QA verdict: how many measures are at or better than the national avg.
  const scored = metrics.filter((m) => m.verdictNational !== 'na');
  const betterOrSame = scored.filter((m) => m.verdictNational !== 'worse').length;
  const qaSummary = scored.length
    ? `${betterOrSame} of ${scored.length} hospitalization/ED measures at or better than the national average.`
    : 'No hospitalization/ED benchmark data available for this facility.';

  // Ordered label/value rows mirroring the Facility Assessment Snapshot template.
  const tableRows = [
    ['Name of Facility', name],
    ['Location', composeLocation(provider)],
    ['EMR', manual.emr || NA],
    ['Census Capacity', provider.number_of_certified_beds || NA],
    ['Current Census', manual.currentCensus || NA],
    ['Type of Patient', manual.patientType || NA],
    ['Previous Coverage from Medelite', manual.previousCoverage || NA],
    ['Previous Provider Performance from Medelite', manual.previousPerformance || NA],
    ['Medical Coverage', manual.medicalCoverage || NA],
    ...ratings.map((r) => [r.label, r.text]),
  ];
  for (const m of metrics) {
    tableRows.push([m.facilityLabel, m.facilityText]);
    tableRows.push([m.nationalLabel, m.nationalText]);
    tableRows.push([m.stateLabel, m.stateText]);
  }

  return {
    ccn,
    state,
    name,
    officialName,
    location: composeLocation(provider),
    medicareUrl: medicareUrl(ccn, state),
    processingDate: provider.processing_date || nation.processing_date || null,
    ratings,
    metrics,
    qaSummary,
    tableRows,
  };
}
