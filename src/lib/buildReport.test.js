import { describe, it, expect } from 'vitest';
import { buildReport, NA } from './buildReport.js';
import { provider, claims, averages, manual } from './buildReport.fixtures.js';

// Helper: pull a value out of the ordered tableRows by its label.
const rowValue = (report, label) =>
  report.tableRows.find(([l]) => l === label)?.[1];

describe('buildReport', () => {
  it('returns null when there is no provider', () => {
    expect(buildReport(null, [], [], manual)).toBeNull();
  });

  it('uses the official CMS name when no override is given', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(r.name).toBe('KENDALL LAKES HEALTHCARE AND REHAB CENTER');
    expect(rowValue(r, 'Name of Facility')).toBe(r.name);
  });

  it('lets a manual override win over the official name', () => {
    const r = buildReport(provider, claims, averages, {
      ...manual,
      overrideName: 'Kendall Lakes (Internal)',
    });
    expect(r.name).toBe('Kendall Lakes (Internal)');
    expect(r.officialName).toBe('KENDALL LAKES HEALTHCARE AND REHAB CENTER');
  });

  it('ignores a blank/whitespace override', () => {
    const r = buildReport(provider, claims, averages, { ...manual, overrideName: '   ' });
    expect(r.name).toBe(provider.provider_name);
  });

  it('produces exactly 25 ordered snapshot rows', () => {
    const r = buildReport(provider, claims, averages, manual);
    // 9 info/manual + 4 ratings + 12 metrics
    expect(r.tableRows).toHaveLength(25);
  });

  it('composes a cleanly spaced location (not the raw geocoded string)', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(rowValue(r, 'Location')).toBe('5280 SW 157 AVENUE, MIAMI, FL 33185');
  });

  it('maps Census Capacity from number_of_certified_beds', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(rowValue(r, 'Census Capacity')).toBe('150');
  });

  it('passes manual operational inputs through to the report', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(rowValue(r, 'EMR')).toBe('PCC');
    expect(rowValue(r, 'Current Census')).toBe('112');
    expect(rowValue(r, 'Type of Patient')).toBe('Long-term & Short-term');
    expect(rowValue(r, 'Previous Coverage from Medelite')).toBe('Yes');
    expect(rowValue(r, 'Medical Coverage')).toBe('Optometry, PCP, Podiatry');
  });

  it('maps the four star ratings', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(rowValue(r, 'Overall Star Rating')).toBe('5');
    expect(rowValue(r, 'Health Inspection')).toBe('5');
    expect(rowValue(r, 'Staffing')).toBe('2');
    expect(rowValue(r, 'Quality of Resident Care')).toBe('5');
    expect(r.ratings.find((x) => x.label === 'Staffing').value).toBe(2);
  });

  it('builds the Medicare Care Compare URL from CCN + state', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(r.medicareUrl).toBe(
      'https://www.medicare.gov/care-compare/details/nursing-home/686123/view-all?state=FL'
    );
  });

  it('formats short-stay metrics as percentages (1 decimal)', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(rowValue(r, 'Short Term Hospitalization')).toBe('25.6%');
    expect(rowValue(r, 'STR ED Visit')).toBe('8.1%');
  });

  it('formats long-stay metrics as a rate (2 decimals, no unit)', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(rowValue(r, 'LT Hospitalization')).toBe('2.75');
    expect(rowValue(r, 'ED Visit')).toBe('0.91');
  });

  it('pulls national + state averages from the correct rows (ignoring other states)', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(rowValue(r, 'STR National Avg. for Hospitalization')).toBe('23.9%');
    expect(rowValue(r, 'STR State National Avg. for Hospitalization')).toBe('26.2%');
    expect(rowValue(r, 'LT National Avg. for Hospitalization')).toBe('1.90');
    expect(rowValue(r, 'LT ED Visits State Avg.')).toBe('1.16');
    // The unrelated CA row (99.9) must never leak in.
    expect(JSON.stringify(r.tableRows)).not.toContain('99.9');
  });

  it('computes a benchmark verdict per metric (lower = better)', () => {
    const r = buildReport(provider, claims, averages, manual);
    const byCode = Object.fromEntries(r.metrics.map((m) => [m.code, m]));
    // 521/551 facility above national -> worse; 522/552 below -> better.
    expect(byCode['521'].verdictNational).toBe('worse');
    expect(byCode['522'].verdictNational).toBe('better');
    expect(byCode['551'].verdictNational).toBe('worse');
    expect(byCode['552'].verdictNational).toBe('better');
    // Signed deltas (facility - benchmark) are exposed too.
    expect(byCode['522'].vsNational).toBeLessThan(0);
    expect(byCode['521'].vsNational).toBeGreaterThan(0);
  });

  it('summarizes how many measures beat the national average', () => {
    const r = buildReport(provider, claims, averages, manual);
    expect(r.qaSummary).toBe(
      '2 of 4 hospitalization/ED measures at or better than the national average.'
    );
  });

  it('marks verdicts and summary as N/A when no benchmark data exists', () => {
    const r = buildReport(provider, claims, [], manual);
    expect(r.metrics.every((m) => m.verdictNational === 'na')).toBe(true);
    expect(r.qaSummary).toMatch(/No hospitalization\/ED benchmark data/);
  });

  it('renders N/A for missing CMS fields without crashing', () => {
    const sparse = { cms_certification_number_ccn: '999999', state: 'TX' };
    const r = buildReport(sparse, [], [], { previousCoverage: 'No' });
    expect(r.name).toBe(NA);
    expect(rowValue(r, 'Census Capacity')).toBe(NA);
    expect(rowValue(r, 'Overall Star Rating')).toBe(NA);
    // No claims/averages -> every metric value is N/A
    expect(rowValue(r, 'Short Term Hospitalization')).toBe(NA);
    expect(r.tableRows).toHaveLength(25);
  });
});
