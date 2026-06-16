import { describe, it, expect } from 'vitest';
import JSZip from 'jszip';
import { buildZipBlob } from './batch';

const mkReport = (ccn, name) => ({
  ccn,
  name,
  state: 'FL',
  medicareUrl: 'https://example.test/' + ccn,
  qaSummary: '2 of 4 measures at or better than national.',
  ratings: [{ label: 'Overall Star Rating', text: '5' }],
  tableRows: [
    ['Name of Facility', name],
    ['Location', 'Miami, FL'],
  ],
});

describe('buildZipBlob', () => {
  it('packages a PDF per ok facility plus summary.csv', async () => {
    const results = [
      { ccn: '686123', status: 'ok', name: 'Kendall Lakes', completeness: 100, report: mkReport('686123', 'Kendall Lakes') },
      { ccn: '015009', status: 'ok', name: 'Burns NH', completeness: 100, report: mkReport('015009', 'Burns NH') },
      { ccn: '105007', status: 'notfound' },
    ];

    const blob = await buildZipBlob(results);
    expect(blob.size).toBeGreaterThan(0);

    const zip = await JSZip.loadAsync(Buffer.from(await blob.arrayBuffer()));
    const names = Object.keys(zip.files);

    // One PDF per successful facility (under reports/), and the summary.
    const pdfs = names.filter((n) => n.endsWith('.pdf'));
    expect(pdfs).toHaveLength(2);
    expect(names).toContain('summary.csv');

    const csv = await zip.file('summary.csv').async('string');
    expect(csv.split('\n')).toHaveLength(4); // header + 3 rows
    expect(csv).toContain('105007,notfound');
  });
});
