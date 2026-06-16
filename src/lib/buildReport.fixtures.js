// Trimmed real-shape fixtures captured from the CMS Provider Data Catalog for
// CCN 686123 (Kendall Lakes). Used by the offline unit tests.

export const provider = {
  cms_certification_number_ccn: '686123',
  provider_name: 'KENDALL LAKES HEALTHCARE AND REHAB CENTER',
  provider_address: '5280 SW 157 AVENUE',
  citytown: 'MIAMI',
  state: 'FL',
  zip_code: '33185',
  location: '5280 SW 157 AVENUE,MIAMI,FL,33185', // raw geocoded string (no spaces)
  number_of_certified_beds: '150',
  average_number_of_residents_per_day: '142.4',
  overall_rating: '5',
  health_inspection_rating: '5',
  staffing_rating: '2',
  qm_rating: '5',
};

export const claims = [
  { measure_code: '521', adjusted_score: '25.575578', resident_type: 'Short Stay' },
  { measure_code: '522', adjusted_score: '8.094575', resident_type: 'Short Stay' },
  { measure_code: '551', adjusted_score: '2.752503', resident_type: 'Long Stay' },
  { measure_code: '552', adjusted_score: '0.910105', resident_type: 'Long Stay' },
];

export const averages = [
  {
    state_or_nation: 'NATION',
    percentage_of_short_stay_residents_who_were_rehospitalized__1d02: '23.875617',
    percentage_of_short_stay_residents_who_had_an_outpatient_em_d911: '12.013574',
    number_of_hospitalizations_per_1000_longstay_resident_days: '1.897659',
    number_of_outpatient_emergency_department_visits_per_1000_l_de9d: '1.798049',
  },
  {
    state_or_nation: 'FL',
    percentage_of_short_stay_residents_who_were_rehospitalized__1d02: '26.203324',
    percentage_of_short_stay_residents_who_had_an_outpatient_em_d911: '9.157686',
    number_of_hospitalizations_per_1000_longstay_resident_days: '2.147753',
    number_of_outpatient_emergency_department_visits_per_1000_l_de9d: '1.156036',
  },
  {
    state_or_nation: 'CA', // unrelated row — must be ignored
    percentage_of_short_stay_residents_who_were_rehospitalized__1d02: '99.9',
    percentage_of_short_stay_residents_who_had_an_outpatient_em_d911: '99.9',
    number_of_hospitalizations_per_1000_longstay_resident_days: '99.9',
    number_of_outpatient_emergency_department_visits_per_1000_l_de9d: '99.9',
  },
];

export const manual = {
  overrideName: '',
  emr: 'PCC',
  currentCensus: '112',
  patientType: 'Long-term & Short-term',
  previousCoverage: 'Yes',
  previousPerformance: 'About 30 patients/day',
  medicalCoverage: 'Optometry, PCP, Podiatry',
};
