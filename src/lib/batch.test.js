import { describe, it, expect } from 'vitest';
import { parseCcns, toSummaryCsv } from './batch';

describe('parseCcns', () => {
  it('keeps valid 6-digit CCNs, one per line', () => {
    expect(parseCcns('686123\n015009\n105007')).toEqual(['686123', '015009', '105007']);
  });

  it('skips a header row and reads the first CSV column', () => {
    const csv = 'ccn,name\n686123,Kendall Lakes\n015009,Burns';
    expect(parseCcns(csv)).toEqual(['686123', '015009']);
  });

  it('de-duplicates while preserving order', () => {
    expect(parseCcns('686123\n686123\n015009')).toEqual(['686123', '015009']);
  });

  it('ignores blank lines and non-6-digit tokens', () => {
    expect(parseCcns('\n12345\n686123\nabc\n1234567')).toEqual(['686123']);
  });

  it('returns [] for empty input', () => {
    expect(parseCcns('')).toEqual([]);
  });
});

describe('toSummaryCsv', () => {
  it('writes a header and one row per result', () => {
    const results = [
      {
        ccn: '686123',
        status: 'ok',
        completeness: 100,
        report: {
          name: 'Kendall Lakes',
          state: 'FL',
          qaSummary: '2 of 4 measures at or better than national.',
          ratings: [{ label: 'Overall Star Rating', text: '5' }],
        },
      },
      { ccn: '105007', status: 'notfound' },
      { ccn: '999999', status: 'error', error: 'boom' },
    ];
    const csv = toSummaryCsv(results);
    const lines = csv.split('\n');
    expect(lines[0]).toBe('ccn,status,name,state,overall_rating,qa_summary,completeness,error');
    expect(lines[1]).toContain('686123,ok,Kendall Lakes,FL,5,');
    expect(lines[1]).toContain('100');
    expect(lines[2]).toBe('105007,notfound,,,,,,');
    expect(lines[3]).toContain('999999,error');
    expect(lines[3]).toContain('boom');
  });

  it('quotes cells containing commas', () => {
    const results = [
      {
        ccn: '686123',
        status: 'ok',
        report: { name: 'Burns Nursing Home, Inc.', ratings: [] },
      },
    ];
    expect(toSummaryCsv(results)).toContain('"Burns Nursing Home, Inc."');
  });
});
