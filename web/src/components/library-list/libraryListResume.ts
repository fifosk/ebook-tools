import type { LibraryItem, ResumePositionMediaType } from '../../api/dtos';
import { getBrowserStorage, getStorageItem, type BrowserStorage } from '../../utils/browserStorage';

const MEDIA_MEMORY_PREFIX = 'media-memory';
const MIN_MEANINGFUL_TIME_SECONDS = 5;

type MediaCategory = ResumePositionMediaType;

interface StoredMediaMemory {
  current?: {
    playbackPosition?: number | null;
    currentMediaType?: MediaCategory | null;
    baseId?: string | null;
  } | null;
  entries?: Record<
    string,
    {
      position?: number | null;
      mediaType?: MediaCategory | null;
      baseId?: string | null;
    }
  > | null;
}

export interface LibraryResumeBadge {
  label: string;
  title: string;
  position: number;
  mediaType: MediaCategory | null;
}

function normalizePosition(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 0;
  }
  return Math.max(value, 0);
}

function parseStoredMediaMemory(raw: string | null): StoredMediaMemory | null {
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as StoredMediaMemory;
    return typeof parsed === 'object' && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
}

function formatPlaybackTime(totalSeconds: number): string {
  const seconds = Math.max(Math.floor(totalSeconds), 0);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
  }
  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`;
}

function mediaLabel(mediaType: MediaCategory | null): string {
  switch (mediaType) {
    case 'audio':
      return 'audio';
    case 'video':
      return 'video';
    case 'text':
      return 'text';
    default:
      return 'media';
  }
}

export function resolveLibraryResumeBadge(raw: string | null): LibraryResumeBadge | null {
  const memory = parseStoredMediaMemory(raw);
  if (!memory) {
    return null;
  }

  const candidates = [
    {
      position: normalizePosition(memory.current?.playbackPosition),
      mediaType: memory.current?.currentMediaType ?? null,
    },
    ...Object.values(memory.entries ?? {}).map((entry) => ({
      position: normalizePosition(entry?.position),
      mediaType: entry?.mediaType ?? null,
    })),
  ];
  const best = candidates.reduce(
    (current, candidate) => (candidate.position > current.position ? candidate : current),
    { position: 0, mediaType: null as MediaCategory | null },
  );

  if (best.position <= MIN_MEANINGFUL_TIME_SECONDS) {
    return null;
  }

  const formatted = formatPlaybackTime(best.position);
  return {
    label: `Continue ${formatted}`,
    title: `Continue ${mediaLabel(best.mediaType)} playback from ${formatted}`,
    position: best.position,
    mediaType: best.mediaType,
  };
}

export function buildLibraryResumeBadgeMap(
  items: Pick<LibraryItem, 'jobId'>[],
  storage: BrowserStorage | null = getBrowserStorage('session'),
): Map<string, LibraryResumeBadge> {
  const badges = new Map<string, LibraryResumeBadge>();
  if (!storage) {
    return badges;
  }
  items.forEach((item) => {
    const badge = resolveLibraryResumeBadge(getStorageItem(storage, `${MEDIA_MEMORY_PREFIX}:${item.jobId}`));
    if (badge) {
      badges.set(item.jobId, badge);
    }
  });
  return badges;
}
