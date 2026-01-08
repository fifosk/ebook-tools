import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createPlaybackBookmark,
  deletePlaybackBookmark,
  fetchPlaybackBookmarks,
  getAuthContext,
} from '../api/client';
import type {
  PlaybackBookmarkCreatePayload,
  PlaybackBookmarkEntry as ApiPlaybackBookmarkEntry,
} from '../api/dtos';

export type BookmarkKind = 'time' | 'sentence';
export type BookmarkMediaType = 'text' | 'audio' | 'video';

export interface PlaybackBookmark {
  id: string;
  createdAt: number;
  kind: BookmarkKind;
  label: string;
  position?: number | null;
  sentence?: number | null;
  mediaType?: BookmarkMediaType | null;
  mediaId?: string | null;
  baseId?: string | null;
}

const STORAGE_PREFIX = 'player.bookmarks';
const MAX_BOOKMARKS = 200;

type StorageProvider = Pick<Storage, 'getItem' | 'setItem'>;

function getLocalStorage(): StorageProvider | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return window.localStorage;
  } catch (error) {
    return null;
  }
}

function loadBookmarks(storage: StorageProvider | null, jobId: string | null | undefined): PlaybackBookmark[] {
  if (!storage || !jobId) {
    return [];
  }
  const raw = storage.getItem(`${STORAGE_PREFIX}:${jobId}`);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((entry) => entry && typeof entry === 'object') as PlaybackBookmark[];
  } catch (error) {
    return [];
  }
}

function persistBookmarks(storage: StorageProvider | null, jobId: string | null | undefined, bookmarks: PlaybackBookmark[]) {
  if (!storage || !jobId) {
    return;
  }
  try {
    storage.setItem(`${STORAGE_PREFIX}:${jobId}`, JSON.stringify(bookmarks));
  } catch (error) {
    // Ignore quota errors.
  }
}

function buildBookmarkId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normaliseTime(value: number | null | undefined): number | null {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return null;
  }
  return Math.max(0, Math.round(value * 1000) / 1000);
}

function isDuplicate(existing: PlaybackBookmark, next: PlaybackBookmark): boolean {
  if (existing.kind !== next.kind) {
    return false;
  }
  if (existing.mediaType !== next.mediaType) {
    return false;
  }
  if (existing.kind === 'sentence') {
    return Boolean(existing.sentence) && existing.sentence === next.sentence;
  }
  const existingTime = normaliseTime(existing.position);
  const nextTime = normaliseTime(next.position);
  if (existingTime === null || nextTime === null) {
    return false;
  }
  return Math.abs(existingTime - nextTime) < 0.5;
}

export function formatBookmarkTime(seconds: number): string {
  const total = Math.max(0, Math.trunc(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remaining = total % 60;
  const parts = [minutes.toString().padStart(2, '0'), remaining.toString().padStart(2, '0')];
  if (hours > 0) {
    parts.unshift(hours.toString().padStart(2, '0'));
  }
  return parts.join(':');
}

interface UsePlaybackBookmarksArgs {
  jobId: string | null | undefined;
  userId?: string | null;
  useRemote?: boolean;
}

const toLocalBookmark = (entry: ApiPlaybackBookmarkEntry): PlaybackBookmark => ({
  id: entry.id,
  createdAt: Math.round((entry.created_at ?? 0) * 1000),
  kind: entry.kind,
  label: entry.label,
  position: entry.position ?? null,
  sentence: entry.sentence ?? null,
  mediaType: entry.media_type ?? null,
  mediaId: entry.media_id ?? null,
  baseId: entry.base_id ?? null,
});

const toApiPayload = (
  entry: Omit<PlaybackBookmark, 'id' | 'createdAt'> & {
    id?: string | null;
    createdAt?: number | null;
  }
): PlaybackBookmarkCreatePayload => ({
  id: entry.id ?? null,
  label: entry.label,
  kind: entry.kind,
  created_at: typeof entry.createdAt === 'number' ? entry.createdAt / 1000 : null,
  position: entry.position ?? null,
  sentence: entry.sentence ?? null,
  media_type: entry.mediaType ?? null,
  media_id: entry.mediaId ?? null,
  base_id: entry.baseId ?? null,
});

export function usePlaybackBookmarks({ jobId, userId, useRemote }: UsePlaybackBookmarksArgs) {
  const storage = getLocalStorage();
  const [bookmarks, setBookmarks] = useState<PlaybackBookmark[]>(() => loadBookmarks(storage, jobId));
  const authContext = getAuthContext();
  const resolvedUserId = userId ?? authContext.userId;
  const remoteEnabled = useRemote ?? Boolean(resolvedUserId);

  useEffect(() => {
    if (!jobId) {
      setBookmarks([]);
      return;
    }
    let cancelled = false;
    if (!remoteEnabled) {
      setBookmarks(loadBookmarks(storage, jobId));
      return;
    }
    void fetchPlaybackBookmarks(jobId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        const mapped = response.bookmarks.map(toLocalBookmark);
        setBookmarks(mapped);
        persistBookmarks(storage, jobId, mapped);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setBookmarks(loadBookmarks(storage, jobId));
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, remoteEnabled, storage]);

  const updateBookmarks = useCallback(
    (updater: (current: PlaybackBookmark[]) => PlaybackBookmark[]) => {
      setBookmarks((current) => {
        const next = updater(current);
        persistBookmarks(storage, jobId, next);
        return next;
      });
    },
    [jobId, storage],
  );

  const addBookmark = useCallback(
    (entry: Omit<PlaybackBookmark, 'id' | 'createdAt'>) => {
      if (!jobId || !remoteEnabled) {
        updateBookmarks((current) => {
          const createdAt = Date.now();
          const next: PlaybackBookmark = {
            id: buildBookmarkId(),
            createdAt,
            kind: entry.kind,
            label: entry.label,
            position: normaliseTime(entry.position),
            sentence: entry.sentence ?? null,
            mediaType: entry.mediaType ?? null,
            mediaId: entry.mediaId ?? null,
            baseId: entry.baseId ?? null,
          };
          if (current.some((existing) => isDuplicate(existing, next))) {
            return current;
          }
          const merged = [next, ...current];
          if (merged.length > MAX_BOOKMARKS) {
            return merged.slice(0, MAX_BOOKMARKS);
          }
          return merged;
        });
        return;
      }
      void (async () => {
        const createdAt = Date.now();
        const payload = toApiPayload({
          ...entry,
          id: null,
          createdAt,
          position: normaliseTime(entry.position),
        });
        try {
          const response = await createPlaybackBookmark(jobId, payload);
          const mapped = toLocalBookmark(response);
          updateBookmarks((current) => {
            const next = [mapped, ...current.filter((existing) => existing.id !== mapped.id)];
            return next.slice(0, MAX_BOOKMARKS);
          });
        } catch (error) {
          updateBookmarks((current) => {
            const next: PlaybackBookmark = {
              id: buildBookmarkId(),
              createdAt,
              kind: entry.kind,
              label: entry.label,
              position: normaliseTime(entry.position),
              sentence: entry.sentence ?? null,
              mediaType: entry.mediaType ?? null,
              mediaId: entry.mediaId ?? null,
              baseId: entry.baseId ?? null,
            };
            if (current.some((existing) => isDuplicate(existing, next))) {
              return current;
            }
            const merged = [next, ...current];
            return merged.slice(0, MAX_BOOKMARKS);
          });
        }
      })();
    },
    [jobId, remoteEnabled, updateBookmarks],
  );

  const removeBookmark = useCallback(
    (id: string) => {
      if (!jobId || !remoteEnabled) {
        updateBookmarks((current) => current.filter((entry) => entry.id !== id));
        return;
      }
      void (async () => {
        try {
          const response = await deletePlaybackBookmark(jobId, id);
          if (!response.deleted) {
            return;
          }
          updateBookmarks((current) => current.filter((entry) => entry.id !== id));
        } catch {
          return;
        }
      })();
    },
    [jobId, remoteEnabled, updateBookmarks],
  );

  const sortedBookmarks = useMemo(
    () => [...bookmarks].sort((a, b) => b.createdAt - a.createdAt),
    [bookmarks],
  );

  return {
    bookmarks: sortedBookmarks,
    addBookmark,
    removeBookmark,
  };
}
