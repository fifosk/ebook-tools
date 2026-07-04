import { describe, expect, it } from 'vitest';
import { normalizeDiscoveryPolicyNotes } from '../acquisitionPolicyNotes';

describe('normalizeDiscoveryPolicyNotes', () => {
  it('trims, filters, and deduplicates notes while preserving order', () => {
    expect(normalizeDiscoveryPolicyNotes([
      ' Discovery results are candidates only. ',
      '',
      'Review source rights before downloading.',
      'Review source rights before downloading.',
      '  Metadata-only handoff.  ',
    ])).toEqual([
      'Discovery results are candidates only.',
      'Review source rights before downloading.',
      'Metadata-only handoff.',
    ]);
  });

  it('accepts empty or absent note lists', () => {
    expect(normalizeDiscoveryPolicyNotes(undefined)).toEqual([]);
    expect(normalizeDiscoveryPolicyNotes(null)).toEqual([]);
  });
});
