import { describe, expect, it } from 'vitest';
import {
  buildLibraryResumeBadgeMap,
  resolveResumeEntryBadge,
  resolveLibraryResumeBadge
} from '../library-list/libraryListResume';
import type { LibraryItem, ResumePositionEntry } from '../../api/dtos';

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

  it('formats server sentence resume entries', () => {
    const badge = resolveResumeEntryBadge({
      job_id: 'job-1',
      kind: 'sentence',
      updated_at: 1_800_000_000,
      sentence: 42,
      media_type: 'text',
    } as ResumePositionEntry);

    expect(badge).toMatchObject({
      label: 'Continue sentence 42',
      title: 'Continue text playback from sentence 42',
      mediaType: 'text',
      updatedAt: 1_800_000_000,
    });
  });

  it('builds a badge map from existing media-memory session keys only', () => {
    const badges = buildLibraryResumeBadgeMap(
      [item('job-1'), item('job-2')],
      [],
      storage({
        'media-memory:job-1': JSON.stringify({
          current: { playbackPosition: 61, currentMediaType: 'audio' },
        }),
      }),
    );

    expect(badges.get('job-1')?.label).toBe('Continue 1:01');
    expect(badges.has('job-2')).toBe(false);
  });

  it('merges server resume entries and prefers further local time progress', () => {
    const badges = buildLibraryResumeBadgeMap(
      [item('job-1'), item('job-2')],
      [
        {
          job_id: 'job-1',
          kind: 'time',
          updated_at: 1_800_000_000,
          position: 61,
          media_type: 'audio',
        },
        {
          job_id: 'job-2',
          kind: 'time',
          updated_at: 1_800_000_100,
          position: 30,
          media_type: 'video',
        },
      ] as ResumePositionEntry[],
      storage({
        'media-memory:job-2': JSON.stringify({
          current: { playbackPosition: 90, currentMediaType: 'video' },
        }),
      }),
    );

    expect(badges.get('job-1')?.label).toBe('Continue 1:01');
    expect(badges.get('job-2')?.label).toBe('Continue 1:30');
  });
});
