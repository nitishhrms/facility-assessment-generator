import { describe, it, expect } from 'vitest';
import { medicareUrl } from './fieldMap.js';

describe('medicareUrl', () => {
  it('builds the Care Compare URL with a state query param', () => {
    expect(medicareUrl('686123', 'FL')).toBe(
      'https://www.medicare.gov/care-compare/details/nursing-home/686123/view-all?state=FL'
    );
  });

  it('matches the brief example CCN format', () => {
    expect(medicareUrl('105447', 'CA')).toBe(
      'https://www.medicare.gov/care-compare/details/nursing-home/105447/view-all?state=CA'
    );
  });

  it('omits the query param when no state is provided', () => {
    expect(medicareUrl('686123', '')).toBe(
      'https://www.medicare.gov/care-compare/details/nursing-home/686123/view-all'
    );
  });

  it('url-encodes the state value', () => {
    expect(medicareUrl('686123', 'F L')).toContain('?state=F%20L');
  });
});
