import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchLiveMedia } from '../api/client';
import type { LiveMediaResponse, PipelineJobStatus, ProgressEventPayload } from '../api/dtos';
import { usePipelineEvents } from './usePipelineEvents';

type MediaFilesByType = Record<string, string[]>;

type UseLiveMediaOptions = {
  enabled?: boolean;
  onEvent?: (event: ProgressEventPayload) => void;
};

const MERGE_DEBOUNCE_MS = 200;

function normaliseMediaMap(source: Record<string, string[]> | null | undefined): MediaFilesByType {
  const result: MediaFilesByType = {};
  if (!source) {
    return result;
  }
  for (const [mediaType, entries] of Object.entries(source)) {
    const filtered = entries
      .map((entry) => entry?.trim())
      .filter((entry): entry is string => Boolean(entry && entry.length > 0));
    if (filtered.length > 0) {
      const unique = Array.from(new Set(filtered));
      result[mediaType] = unique;
    }
  }
  return result;
}

function mergeMediaMaps(base: MediaFilesByType, incoming: MediaFilesByType): MediaFilesByType {
  const next: MediaFilesByType = { ...base };
  for (const [mediaType, entries] of Object.entries(incoming)) {
    const existing = next[mediaType] ? [...next[mediaType]] : [];
    const seen = new Set(existing);
    for (const entry of entries) {
      if (!seen.has(entry)) {
        existing.push(entry);
        seen.add(entry);
      }
    }
    if (existing.length > 0) {
      next[mediaType] = existing;
    }
  }
  return next;
}

export function useLiveMedia(
  jobId: string | null,
  { enabled = true, onEvent }: UseLiveMediaOptions = {}
): {
  mediaFiles: MediaFilesByType;
  status: PipelineJobStatus | null;
  progressive: boolean;
  isLoading: boolean;
  error: string | null;
} {
  const [mediaFiles, setMediaFiles] = useState<MediaFilesByType>({});
  const [status, setStatus] = useState<PipelineJobStatus | null>(null);
  const [progressive, setProgressive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pendingRef = useRef<MediaFilesByType>({});
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    pendingRef.current = {};
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, [jobId]);

  const flushPending = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const pending = pendingRef.current;
    if (Object.keys(pending).length === 0) {
      return;
    }
    setMediaFiles((previous) => mergeMediaMaps(previous, pending));
    pendingRef.current = {};
  }, []);

  const enqueueMerge = useCallback(
    (incoming: MediaFilesByType) => {
      if (Object.keys(incoming).length === 0) {
        return;
      }
      pendingRef.current = mergeMediaMaps(pendingRef.current, incoming);
      if (timerRef.current !== null) {
        return;
      }
      timerRef.current = window.setTimeout(() => {
        flushPending();
      }, MERGE_DEBOUNCE_MS);
    },
    [flushPending]
  );

  useEffect(() => {
    if (!jobId) {
      setMediaFiles({});
      setStatus(null);
      setProgressive(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    fetchLiveMedia(jobId)
      .then((response: LiveMediaResponse) => {
        if (cancelled) {
          return;
        }
        setMediaFiles(normaliseMediaMap(response.generated_files));
        setStatus(response.status);
        setProgressive(response.progressive);
      })
      .catch((fetchError: unknown) => {
        if (cancelled) {
          return;
        }
        const message = fetchError instanceof Error ? fetchError.message : 'Unable to load live media.';
        setError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  const handleEvent = useCallback(
    (event: ProgressEventPayload) => {
      onEvent?.(event);
      const generated = normaliseMediaMap(event.snapshot.generated_files ?? null);
      if (Object.keys(generated).length > 0) {
        enqueueMerge(generated);
      }
      if (event.event_type === 'complete') {
        setProgressive(false);
      }
    },
    [enqueueMerge, onEvent]
  );

  usePipelineEvents(jobId ?? '', Boolean(jobId) && enabled, handleEvent);

  return {
    mediaFiles,
    status,
    progressive,
    isLoading,
    error
  };
}
