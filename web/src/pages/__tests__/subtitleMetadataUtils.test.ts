import { describe, expect, it } from 'vitest';
import {
  coerceRecord,
  formatEpisodeCode,
  normalizeTextValue,
  updateSubtitleMediaMetadataDraft,
  updateSubtitleMediaMetadataSection
} from '../subtitle-tool/subtitleMetadataUtils';

describe('subtitle metadata helpers', () => {
  it('copies the current draft before applying top-level metadata edits', () => {
    const current = {
      job_label: 'Original label',
      show: { name: 'Example Show' }
    };

    const next = updateSubtitleMediaMetadataDraft(current, (draft) => {
      draft['job_label'] = 'Updated label';
    });

    expect(next).toEqual({
      job_label: 'Updated label',
      show: { name: 'Example Show' }
    });
    expect(current).toEqual({
      job_label: 'Original label',
      show: { name: 'Example Show' }
    });
    expect(next).not.toBe(current);
  });

  it('creates a draft when editing metadata without an existing payload', () => {
    expect(
      updateSubtitleMediaMetadataDraft(null, (draft) => {
        draft['job_label'] = 'New label';
      })
    ).toEqual({
      job_label: 'New label'
    });
  });

  it('copies nested metadata sections before applying edits', () => {
    const episode = { season: 1, number: 2, name: 'Old title' };
    const current = {
      episode,
      show: { name: 'Example Show' }
    };

    const next = updateSubtitleMediaMetadataSection(current, 'episode', (section) => {
      section['name'] = 'New title';
      section['number'] = 3;
    });

    expect(next).toEqual({
      episode: { season: 1, number: 3, name: 'New title' },
      show: { name: 'Example Show' }
    });
    expect(current.episode).toBe(episode);
    expect(current.episode).toEqual({ season: 1, number: 2, name: 'Old title' });
    expect(next.episode).not.toBe(episode);
  });

  it('creates missing nested metadata sections', () => {
    expect(
      updateSubtitleMediaMetadataSection(null, 'show', (section) => {
        section['name'] = 'Example Show';
      })
    ).toEqual({
      show: { name: 'Example Show' }
    });
  });

  it('coerces plain objects and rejects arrays or primitives', () => {
    const record = { name: 'Example' };

    expect(coerceRecord(record)).toBe(record);
    expect(coerceRecord(['Example'])).toBeNull();
    expect(coerceRecord('Example')).toBeNull();
    expect(coerceRecord(null)).toBeNull();
  });

  it('normalizes non-empty text values only', () => {
    expect(normalizeTextValue('  Example  ')).toBe('Example');
    expect(normalizeTextValue('   ')).toBeNull();
    expect(normalizeTextValue(42)).toBeNull();
  });

  it('formats finite positive season and episode numbers', () => {
    expect(formatEpisodeCode(1, 2)).toBe('S01E02');
    expect(formatEpisodeCode(12.9, 3.1)).toBe('S12E03');
    expect(formatEpisodeCode(0, 2)).toBeNull();
    expect(formatEpisodeCode(1, Number.NaN)).toBeNull();
    expect(formatEpisodeCode('1', 2)).toBeNull();
  });
});
