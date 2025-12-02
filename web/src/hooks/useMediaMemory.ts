import { useCallback, useEffect, useMemo, useState } from 'react';
import type { LiveMediaItem } from './useLiveMedia';

type MediaCategory = 'text' | 'audio' | 'video';

export interface MediaState {
  currentMediaId: string | null;
  currentMediaType: MediaCategory | null;
  playbackPosition: number;
  baseId: string | null;
}

interface MediaEntryState {
  mediaId: string;
  mediaType: MediaCategory;
  baseId: string | null;
  position: number;
}

interface PersistentMediaState {
  current: MediaState;
  entries: Record<string, MediaEntryState>;
}

const INITIAL_STATE: PersistentMediaState = {
  current: {
    currentMediaId: null,
    currentMediaType: null,
    playbackPosition: 0,
    baseId: null,
  },
  entries: {},
};

const STORAGE_PREFIX = 'media-memory';

type StorageProvider = Pick<Storage, 'getItem' | 'setItem'>;

function getSessionStorage(): StorageProvider | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch (error) {
    return null;
  }
}

function normalizeId(value: string): string {
  try {
    return value ? value.normalize('NFC').toLowerCase() : '';
  } catch (error) {
    return value.toLowerCase();
  }
}

function parseStoredState(value: string | null): PersistentMediaState {
  if (!value) {
    return INITIAL_STATE;
  }

  try {
    const parsed = JSON.parse(value) as PersistentMediaState;
    if (typeof parsed !== 'object' || parsed === null) {
      return INITIAL_STATE;
    }
    const { current, entries } = parsed as Partial<PersistentMediaState>;
    return {
      current: {
        currentMediaId: current?.currentMediaId ?? null,
        currentMediaType: current?.currentMediaType ?? null,
        playbackPosition: Number.isFinite(current?.playbackPosition)
          ? Number(current?.playbackPosition)
          : 0,
        baseId: current?.baseId ?? null,
      },
      entries: typeof entries === 'object' && entries !== null ? entries : {},
    } satisfies PersistentMediaState;
  } catch (error) {
    return INITIAL_STATE;
  }
}

function cloneState(state: PersistentMediaState): PersistentMediaState {
  return {
    current: { ...state.current },
    entries: { ...state.entries },
  };
}

function normalisePosition(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(Number(value.toFixed(3)), 0);
}

export function deriveBaseIdFromItem(
  item: Pick<LiveMediaItem, 'name' | 'url' | 'range_fragment'> & { relative_path?: string | null },
): string | null {
  const candidate =
    item.range_fragment ??
    item.name ??
    (item.url ? item.url.split('/').pop() ?? null : null) ??
    (item.relative_path ? item.relative_path.split('/').pop() ?? null : null);
  if (!candidate) {
    return null;
  }

  let cleaned = candidate.replace(/[?#].*$/, '');
  try {
    cleaned = decodeURIComponent(cleaned);
  } catch (error) {
    void error;
  }
  const parts = cleaned.split('.');
  if (parts.length > 1) {
    parts.pop();
  }

  const base = parts.join('.').trim();
  if (!base) {
    return null;
  }

  try {
    return normalizeId(base);
  } catch (error) {
    void error;
  }
  return base.toLowerCase();
}

interface UseMediaMemoryArgs {
  jobId: string | null | undefined;
}

export interface UseMediaMemoryResult {
  state: MediaState;
  rememberSelection: (entry: { media: LiveMediaItem }) => void;
  rememberPosition: (entry: {
    mediaId: string;
    mediaType: MediaCategory;
    baseId: string | null;
    position: number;
  }) => void;
  getPosition: (mediaId: string | null | undefined) => number;
  findMatchingMediaId: (baseId: string | null, type: MediaCategory, available: LiveMediaItem[]) => string | null;
  deriveBaseId: (item: Pick<LiveMediaItem, 'name' | 'url'> | null | undefined) => string | null;
}

export function useMediaMemory({ jobId }: UseMediaMemoryArgs): UseMediaMemoryResult {
  const storage = getSessionStorage();
  const storageKey = jobId ? `${STORAGE_PREFIX}:${jobId}` : null;
  const [state, setState] = useState<PersistentMediaState>(() => {
    if (!storageKey || !storage) {
      return INITIAL_STATE;
    }
    return parseStoredState(storage.getItem(storageKey));
  });

  useEffect(() => {
    if (!storageKey || !storage) {
      setState(INITIAL_STATE);
      return;
    }

    setState(parseStoredState(storage.getItem(storageKey)));
  }, [storage, storageKey]);

  useEffect(() => {
    if (!storageKey || !storage) {
      return;
    }

    try {
      storage.setItem(storageKey, JSON.stringify(state));
    } catch (error) {
      // Ignore write failures (e.g., storage quota exceeded).
    }
  }, [state, storage, storageKey]);

  const rememberSelection = useCallback<UseMediaMemoryResult['rememberSelection']>(
    ({ media }) => {
      if (!media.url) {
        return;
      }

      const url = media.url;
      const baseId = deriveBaseIdFromItem(media);
      setState((current) => {
        const existing = current.entries[url];
        const position = existing?.position ?? 0;
        if (
          current.current.currentMediaId === url &&
          current.current.currentMediaType === media.type &&
          current.current.baseId === baseId &&
          Math.abs(current.current.playbackPosition - position) < 0.1
        ) {
          return current;
        }

        const next = cloneState(current);
        next.current = {
          currentMediaId: url,
          currentMediaType: media.type,
          playbackPosition: position,
          baseId,
        };
        next.entries[url] = {
          mediaId: url,
          mediaType: media.type,
          baseId,
          position,
        };
        return next;
      });
    },
    [],
  );

  const rememberPosition = useCallback<UseMediaMemoryResult['rememberPosition']>(
    ({ mediaId, mediaType, baseId, position }) => {
      if (!mediaId) {
        return;
      }

      const rounded = normalisePosition(position);
      setState((current) => {
        const existing = current.entries[mediaId];
        if (existing && Math.abs(existing.position - rounded) < 0.1) {
          if (
            current.current.currentMediaId === mediaId &&
            Math.abs(current.current.playbackPosition - rounded) < 0.1
          ) {
            return current;
          }
        }

        const next = cloneState(current);
        next.entries[mediaId] = {
          mediaId,
          mediaType,
          baseId,
          position: rounded,
        };
        if (next.current.currentMediaId === mediaId) {
          next.current = {
            ...next.current,
            playbackPosition: rounded,
          };
        }
        return next;
      });
    },
    [],
  );

  const getPosition = useCallback<UseMediaMemoryResult['getPosition']>(
    (mediaId) => {
      if (!mediaId) {
        return 0;
      }
      return state.entries[mediaId]?.position ?? 0;
    },
    [state.entries],
  );

  const findMatchingMediaId = useCallback<UseMediaMemoryResult['findMatchingMediaId']>(
    (baseId, type, available) => {
      if (!baseId) {
        return null;
      }

      const normalisedBase = baseId.toLowerCase();
      const matchFromEntries = Object.values(state.entries).find(
        (entry) => entry.baseId === normalisedBase && entry.mediaType === type,
      );
      if (matchFromEntries?.mediaId) {
        const exists = available.some((item) => item.url === matchFromEntries.mediaId);
        if (exists) {
          return matchFromEntries.mediaId;
        }
      }

      const matchFromList = available.find((item) => deriveBaseIdFromItem(item) === normalisedBase);
      return matchFromList?.url ?? null;
    },
    [state.entries],
  );

  const deriveBaseId = useCallback<UseMediaMemoryResult['deriveBaseId']>((item) => {
    if (!item) {
      return null;
    }
    return deriveBaseIdFromItem(item);
  }, []);

  const memoisedState = useMemo(() => state.current, [state.current]);

  return {
    state: memoisedState,
    rememberSelection,
    rememberPosition,
    getPosition,
    findMatchingMediaId,
    deriveBaseId,
  };
}

export type { MediaCategory };
