import type { LibraryItem } from '../../api/dtos';
import type { LibraryResumeBadge } from './libraryListResume';

const NEWLY_COMPLETED_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

export type LibraryAttentionBadgeVariant = 'new' | 'attention';

export interface LibraryAttentionBadge {
  label: string;
  title: string;
  variant: LibraryAttentionBadgeVariant;
}

function parseTimestamp(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

export function resolveLibraryAttentionBadge(
  item: Pick<LibraryItem, 'mediaCompleted' | 'status' | 'updatedAt' | 'createdAt'>,
  resumeBadge: LibraryResumeBadge | null | undefined,
  nowMs = Date.now(),
): LibraryAttentionBadge | null {
  if (!item.mediaCompleted) {
    return {
      label: 'Needs attention',
      title: 'Media is missing; re-sync or regenerate before playback.',
      variant: 'attention',
    };
  }

  if (resumeBadge || item.status !== 'finished') {
    return null;
  }

  const completedAt = parseTimestamp(item.updatedAt) ?? parseTimestamp(item.createdAt);
  if (completedAt === null) {
    return null;
  }
  const ageMs = nowMs - completedAt;
  if (ageMs < 0 || ageMs > NEWLY_COMPLETED_WINDOW_MS) {
    return null;
  }
  return {
    label: 'Newly completed',
    title: 'Completed recently; ready to start listening.',
    variant: 'new',
  };
}
