import type { LibraryItem, ResumePositionEntry, ResumePositionMediaType } from '../../api/dtos';
import { getBrowserStorage, getStorageItem, type BrowserStorage } from '../../utils/browserStorage';

const MEDIA_MEMORY_PREFIX = 'media-memory';
const MIN_MEANINGFUL_TIME_SECONDS = 5;
const MIN_MEANINGFUL_SENTENCE = 1;

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
  updatedAt: number;
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

export function resolveResumeEntryBadge(entry: ResumePositionEntry | null | undefined): LibraryResumeBadge | null {
  if (!entry) {
    return null;
  }
  const mediaType = entry.media_type ?? null;
  if (entry.kind === 'sentence') {
    const sentence = typeof entry.sentence === 'number' && Number.isFinite(entry.sentence)
      ? Math.trunc(entry.sentence)
      : 0;
    const position = normalizePosition(entry.position);
    if (sentence <= MIN_MEANINGFUL_SENTENCE) {
      return null;
    }
    if (position > MIN_MEANINGFUL_TIME_SECONDS) {
      const formatted = formatPlaybackTime(position);
      return {
        label: `Continue sentence ${sentence} · ${formatted}`,
        title: `Continue ${mediaLabel(mediaType)} playback from sentence ${sentence} at ${formatted}`,
        position,
        updatedAt: normalizePosition(entry.updated_at),
        mediaType,
      };
    }
    return {
      label: `Continue sentence ${sentence}`,
      title: `Continue ${mediaLabel(mediaType)} playback from sentence ${sentence}`,
      position: 0,
      updatedAt: normalizePosition(entry.updated_at),
      mediaType,
    };
  }

  const position = normalizePosition(entry.position);
  if (position <= MIN_MEANINGFUL_TIME_SECONDS) {
    return null;
  }
  const formatted = formatPlaybackTime(position);
  return {
    label: `Continue ${formatted}`,
    title: `Continue ${mediaLabel(mediaType)} playback from ${formatted}`,
    position,
    updatedAt: normalizePosition(entry.updated_at),
    mediaType,
  };
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
    updatedAt: 0,
    mediaType: best.mediaType,
  };
}

function chooseBadge(
  localBadge: LibraryResumeBadge | null | undefined,
  serverBadge: LibraryResumeBadge | null | undefined,
): LibraryResumeBadge | null {
  if (!localBadge) {
    return serverBadge ?? null;
  }
  if (!serverBadge) {
    return localBadge;
  }
  if (localBadge.position > 0 && serverBadge.position > 0) {
    return localBadge.position >= serverBadge.position ? localBadge : serverBadge;
  }
  return localBadge.updatedAt >= serverBadge.updatedAt ? localBadge : serverBadge;
}

export function buildLibraryResumeBadgeMap(
  items: Pick<LibraryItem, 'jobId'>[],
  serverEntries: ResumePositionEntry[] = [],
  storage: BrowserStorage | null = getBrowserStorage('session'),
): Map<string, LibraryResumeBadge> {
  const badges = new Map<string, LibraryResumeBadge>();
  const serverBadges = new Map<string, LibraryResumeBadge>();
  serverEntries.forEach((entry) => {
    const badge = resolveResumeEntryBadge(entry);
    if (badge) {
      serverBadges.set(entry.job_id, badge);
    }
  });
  items.forEach((item) => {
    const localBadge = storage
      ? resolveLibraryResumeBadge(getStorageItem(storage, `${MEDIA_MEMORY_PREFIX}:${item.jobId}`))
      : null;
    const badge = chooseBadge(localBadge, serverBadges.get(item.jobId));
    if (badge) {
      badges.set(item.jobId, badge);
    }
  });
  return badges;
}
