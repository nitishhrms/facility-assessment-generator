// ---------------------------------------------------------------------------
// Central mapping config.
// Every "messy CMS field name -> clean report label" decision lives here, in
// one place, so the rest of the app never hard-codes government field names.
// ---------------------------------------------------------------------------

// CMS Provider Data Catalog dataset identifiers.
export const DATASETS = {
  provider: '4pq5-n9py', // Nursing Home Provider Information
  claims: 'ijh5-nb2v', // Medicare Claims Quality Measures
  averages: 'xcdc-v8bm', // State / US Averages
};

// Official Medicare Care Compare profile base URL.
export const MEDICARE_BASE =
  'https://www.medicare.gov/care-compare/details/nursing-home';

export function medicareUrl(ccn, state) {
  const qs = state ? `?state=${encodeURIComponent(state)}` : '';
  return `${MEDICARE_BASE}/${ccn}/view-all${qs}`;
}

// Star ratings: CMS field -> report label (rendered in the order shown).
export const RATING_FIELDS = [
  { key: 'overall_rating', label: 'Overall Star Rating' },
  { key: 'health_inspection_rating', label: 'Health Inspection' },
  { key: 'staffing_rating', label: 'Staffing' },
  { key: 'qm_rating', label: 'Quality of Resident Care' },
];

// The 12 hospitalization / ED metric lines come from 4 CMS claims measures.
// For each measure we emit three report rows: facility value, national avg,
// state avg. Per the brief: STR = Short-Stay, LT = Long-Stay.
//   - facility value  -> claims dataset (ijh5-nb2v), `adjusted_score`
//   - state/national  -> averages dataset (xcdc-v8bm), `avgColumn` for the
//                        matching `state_or_nation` row.
export const CLAIMS_MEASURES = [
  {
    code: '521',
    group: 'Short Stay',
    shortName: 'STR Hosp.',
    facilityLabel: 'Short Term Hospitalization',
    nationalLabel: 'STR National Avg. for Hospitalization',
    stateLabel: 'STR State National Avg. for Hospitalization',
    avgColumn: 'percentage_of_short_stay_residents_who_were_rehospitalized__1d02',
    unit: '%',
    decimals: 1,
  },
  {
    code: '522',
    group: 'Short Stay',
    shortName: 'STR ED',
    facilityLabel: 'STR ED Visit',
    nationalLabel: 'STR ED Visits National Avg.',
    stateLabel: 'STR ED Visits State Avg.',
    avgColumn: 'percentage_of_short_stay_residents_who_had_an_outpatient_em_d911',
    unit: '%',
    decimals: 1,
  },
  {
    code: '551',
    group: 'Long Stay',
    shortName: 'LT Hosp.',
    facilityLabel: 'LT Hospitalization',
    nationalLabel: 'LT National Avg. for Hospitalization',
    stateLabel: 'LT State National Avg. for Hospitalization',
    avgColumn: 'number_of_hospitalizations_per_1000_longstay_resident_days',
    unit: '',
    decimals: 2,
  },
  {
    code: '552',
    group: 'Long Stay',
    shortName: 'LT ED',
    facilityLabel: 'ED Visit',
    nationalLabel: 'LT ED Visits National Avg.',
    stateLabel: 'LT ED Visits State Avg.',
    avgColumn: 'number_of_outpatient_emergency_department_visits_per_1000_l_de9d',
    unit: '',
    decimals: 2,
  },
];

// Manual operational input fields (not available in the public CMS database).
export const MANUAL_FIELDS = [
  { key: 'overrideName', label: 'Facility Name Override', type: 'text', placeholder: 'Leave blank to use the official CMS name', hint: 'Optional — overrides the official name on the report' },
  { key: 'emr', label: 'EMR', type: 'text', placeholder: 'e.g. PCC, MatrixCare' },
  { key: 'currentCensus', label: 'Current Census', type: 'number', placeholder: 'e.g. 112' },
  { key: 'patientType', label: 'Type of Patient', type: 'text', placeholder: 'e.g. Long-term & Short-term' },
  { key: 'previousCoverage', label: 'Previous Coverage from Medelite', type: 'select', options: ['Yes', 'No'] },
  { key: 'previousPerformance', label: 'Previous Provider Performance from Medelite', type: 'text', placeholder: 'e.g. About 30 patients/day' },
  { key: 'medicalCoverage', label: 'Medical Coverage', type: 'text', placeholder: 'e.g. Optometry, PCP, Podiatry' },
];

export const DEFAULT_MANUAL = {
  overrideName: '',
  emr: '',
  currentCensus: '',
  patientType: '',
  previousCoverage: 'Yes',
  previousPerformance: '',
  medicalCoverage: '',
};
