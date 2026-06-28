import { describe, expect, it } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import { resolveLibraryAttentionBadge } from '../library-list/libraryListAttention';
import type { LibraryResumeBadge } from '../library-list/libraryListResume';

type AttentionItem = Pick<LibraryItem, 'mediaCompleted' | 'status' | 'updatedAt' | 'createdAt'>;

function item(overrides: Partial<LibraryItem> = {}): AttentionItem {
  return {
    mediaCompleted: true,
    status: 'finished',
    createdAt: '2026-06-20T10:00:00Z',
    updatedAt: '2026-06-27T10:00:00Z',
    ...overrides,
  };
}

const resumeBadge: LibraryResumeBadge = {
  label: 'Continue 1:23',
  title: 'Continue audio playback from 1:23',
  position: 83,
  updatedAt: 1_782_234_000,
  mediaType: 'audio',
};

describe('libraryListAttention', () => {
  it('marks missing media as needing attention', () => {
    expect(
      resolveLibraryAttentionBadge(
        item({ mediaCompleted: false }),
        null,
        Date.parse('2026-06-28T10:00:00Z'),
      ),
    ).toEqual({
      label: 'Needs attention',
      title: 'Media is missing; re-sync or regenerate before playback.',
      variant: 'attention',
    });
  });

  it('marks recently completed entries without resume evidence as newly completed', () => {
    expect(
      resolveLibraryAttentionBadge(item(), null, Date.parse('2026-06-28T10:00:00Z')),
    ).toEqual({
      label: 'Newly completed',
      title: 'Completed recently; ready to start listening.',
      variant: 'new',
    });
  });

  it('does not show newly completed when a continue badge is already present', () => {
    expect(
      resolveLibraryAttentionBadge(item(), resumeBadge, Date.parse('2026-06-28T10:00:00Z')),
    ).toBeNull();
  });

  it('does not mark old or paused rows as newly completed', () => {
    expect(
      resolveLibraryAttentionBadge(
        item({ updatedAt: '2026-06-01T10:00:00Z' }),
        null,
        Date.parse('2026-06-28T10:00:00Z'),
      ),
    ).toBeNull();
    expect(
      resolveLibraryAttentionBadge(
        item({ status: 'paused' }),
        null,
        Date.parse('2026-06-28T10:00:00Z'),
      ),
    ).toBeNull();
  });
});
