import { describe, expect, it } from 'vitest';
import {
  buildLibraryResumeBadgeMap,
  resolveLibraryResumeBadge
} from '../library-list/libraryListResume';
import type { LibraryItem } from '../../api/dtos';

function item(jobId: string): Pick<LibraryItem, 'jobId'> {
  return { jobId };
}

function storage(values: Record<string, string | null>) {
  return {
    getItem: (key: string) => values[key] ?? null,
    setItem: () => undefined,
    removeItem: () => undefined,
  };
}

describe('libraryListResume', () => {
  it('formats meaningful current playback memory as a continue badge', () => {
    const badge = resolveLibraryResumeBadge(
      JSON.stringify({
        current: {
          playbackPosition: 83.8,
          currentMediaType: 'audio',
          baseId: 'chunk-1',
        },
        entries: {},
      }),
    );

    expect(badge).toMatchObject({
      label: 'Continue 1:23',
      title: 'Continue audio playback from 1:23',
      mediaType: 'audio',
    });
  });

  it('uses the furthest remembered entry when current media is stale', () => {
    const badge = resolveLibraryResumeBadge(
      JSON.stringify({
        current: {
          playbackPosition: 4,
          currentMediaType: 'audio',
        },
        entries: {
          video: {
            position: 3723,
            mediaType: 'video',
          },
        },
      }),
    );

    expect(badge).toMatchObject({
      label: 'Continue 1:02:03',
      title: 'Continue video playback from 1:02:03',
      mediaType: 'video',
    });
  });

  it('ignores invalid or non-meaningful resume memory', () => {
    expect(resolveLibraryResumeBadge('not-json')).toBeNull();
    expect(resolveLibraryResumeBadge(JSON.stringify({ current: { playbackPosition: 5 } }))).toBeNull();
  });

  it('builds a badge map from existing media-memory session keys only', () => {
    const badges = buildLibraryResumeBadgeMap(
      [item('job-1'), item('job-2')],
      storage({
        'media-memory:job-1': JSON.stringify({
          current: { playbackPosition: 61, currentMediaType: 'audio' },
        }),
      }),
    );

    expect(badges.get('job-1')?.label).toBe('Continue 1:01');
    expect(badges.has('job-2')).toBe(false);
  });
});
