import { describe, it, expect } from 'vitest';
import { buildReport } from './buildReport.js';
import { dataQuality } from './dataQuality.js';
import { provider, claims, averages, manual } from './buildReport.fixtures.js';

describe('dataQuality', () => {
  it('returns null for a null report', () => {
    expect(dataQuality(null)).toBeNull();
  });

  it('reports 100% completeness when every CMS field is present', () => {
    const dq = dataQuality(buildReport(provider, claims, averages, manual));
    // 2 facility fields (Location, Census Capacity) + 4 ratings + 12 metrics.
    expect(dq.total).toBe(18);
    expect(dq.populated).toBe(18);
    expect(dq.completeness).toBe(100);
    expect(dq.status).toBe('complete');
    expect(dq.missing).toEqual([]);
  });

  it('flags missing CMS fields and lowers completeness', () => {
    const sparse = { cms_certification_number_ccn: '999999', state: 'TX' };
    const dq = dataQuality(buildReport(sparse, [], [], { previousCoverage: 'No' }));
    expect(dq.completeness).toBeLessThan(20);
    expect(dq.status).toBe('partial');
    expect(dq.missing).toContain('Census Capacity');
    expect(dq.missing).toContain('Overall Star Rating');
    expect(dq.missing).toContain('Short Term Hospitalization');
  });

  it('surfaces the CMS processing_date when available', () => {
    const dated = { ...provider, processing_date: '2025-01-01' };
    const dq = dataQuality(buildReport(dated, claims, averages, manual));
    expect(dq.processingDate).toBe('2025-01-01');
  });
});
