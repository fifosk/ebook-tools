import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { MutableRefObject, ReactNode } from 'react';
import { appendAccessToken, fetchSentenceImageInfoBatch, resolveLibraryMediaUrl } from '../../api/client';
import type { AudioTrackMetadata, ChunkSentenceMetadata, SentenceImageInfoResponse } from '../../api/dtos';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { coerceExportPath, resolve as resolveStoragePath } from '../../utils/storageResolver';
import { SentenceImageReel, type SentenceImageFrame } from './SentenceImageReel';
import type { TimelineSentenceRuntime } from './types';
import type { ExportPlayerManifest } from '../../types/exportPlayer';

function getExportManifest(): ExportPlayerManifest | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const candidate = (window as Window & { __EXPORT_DATA__?: unknown }).__EXPORT_DATA__;
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }
  return candidate as ExportPlayerManifest;
}

type UseSentenceImageReelArgs = {
  jobId: string | null;
  playerMode?: 'online' | 'export';
  chunk: LiveMediaChunk | null;
  activeSentenceNumber: number;
  activeSentenceIndex: number;
  jobStartSentence?: number | null;
  jobEndSentence?: number | null;
  totalSentencesInBook?: number | null;
  bookTotalSentences?: number | null;
  isFullscreen: boolean;
  imageRefreshToken: number;
  isLibraryMediaOrigin: boolean;
  timelineSentences: TimelineSentenceRuntime[] | null;
  audioDuration: number | null;
  audioTracks?: Record<string, AudioTrackMetadata> | null;
  activeAudioUrl: string | null;
  effectiveAudioUrl: string | null;
  onRequestSentenceJump?: (sentenceNumber: number) => void;
  inlineAudioPlayingRef: MutableRefObject<boolean>;
  setActiveSentenceIndex: (index: number) => void;
  handleTokenSeek: (time: number) => void;
  seekInlineAudioToTime: (time: number) => void;
};

type UseSentenceImageReelResult = {
  sentenceImageReelNode: ReactNode | null;
  activeSentenceImagePath: string | null;
  reelScale: number;
};

const REEL_SCALE_STORAGE_KEY = 'player.sentenceImageReelScale';
const REEL_SCALE_DEFAULT = 1;
const REEL_SCALE_STEP = 0.1;
const REEL_SCALE_MIN = 0.7;
const REEL_SCALE_MAX = 1.6;

const clampReelScale = (value: number) =>
  Math.min(REEL_SCALE_MAX, Math.max(REEL_SCALE_MIN, value));

const parseBatchStartFromBatchImagePath = (path: string | null): number | null => {
  const candidate = (path ?? '').trim();
  if (!candidate) {
    return null;
  }
  const normalised = candidate.replace(/\\+/g, '/');
  const base = normalised.split('?')[0].split('#')[0];
  const match = base.match(/batch_(\\d+)\\.png$/i);
  if (!match) {
    return null;
  }
  const parsed = Number(match[1]);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return Math.max(1, Math.trunc(parsed));
};

export function useSentenceImageReel({
  jobId,
  playerMode = 'online',
  chunk,
  activeSentenceNumber,
  activeSentenceIndex,
  jobStartSentence = null,
  jobEndSentence = null,
  totalSentencesInBook = null,
  bookTotalSentences = null,
  isFullscreen,
  imageRefreshToken,
  isLibraryMediaOrigin,
  timelineSentences,
  audioDuration,
  audioTracks,
  activeAudioUrl,
  effectiveAudioUrl,
  onRequestSentenceJump,
  inlineAudioPlayingRef,
  setActiveSentenceIndex,
  handleTokenSeek,
  seekInlineAudioToTime,
}: UseSentenceImageReelArgs): UseSentenceImageReelResult {
  const isExportMode = playerMode === 'export';
  const minSentenceBound = useMemo(() => {
    const raw = jobStartSentence ?? null;
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return Math.max(1, Math.trunc(raw));
    }
    return 1;
  }, [jobStartSentence]);

  const maxSentenceBound = useMemo(() => {
    const rawEnd = jobEndSentence ?? null;
    if (typeof rawEnd === 'number' && Number.isFinite(rawEnd)) {
      return Math.max(1, Math.trunc(rawEnd));
    }
    const rawTotal = totalSentencesInBook ?? null;
    if (typeof rawTotal === 'number' && Number.isFinite(rawTotal)) {
      return Math.max(1, Math.trunc(rawTotal));
    }
    const rawBookTotal = bookTotalSentences ?? null;
    if (typeof rawBookTotal === 'number' && Number.isFinite(rawBookTotal)) {
      return Math.max(1, Math.trunc(rawBookTotal));
    }
    return null;
  }, [bookTotalSentences, jobEndSentence, totalSentencesInBook]);

  const exportSentenceByNumber = useMemo(() => {
    if (!isExportMode) {
      return null;
    }
    const manifest = getExportManifest();
    const chunks = manifest?.chunks;
    if (!Array.isArray(chunks)) {
      return null;
    }
    const map = new Map<number, ChunkSentenceMetadata>();
    chunks.forEach((chunk) => {
      const entries = chunk?.sentences;
      if (!Array.isArray(entries)) {
        return;
      }
      entries.forEach((entry) => {
        const raw = entry?.sentence_number ?? null;
        if (typeof raw !== 'number' || !Number.isFinite(raw)) {
          return;
        }
        map.set(Math.max(1, Math.trunc(raw)), entry);
      });
    });
    return map;
  }, [isExportMode]);

  const [isSentenceImageReelVisible, setSentenceImageReelVisible] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    const stored = window.localStorage.getItem('player.sentenceImageReelVisible');
    if (stored === null) {
      return true;
    }
    return stored === 'true';
  });

  const [reelScale, setReelScale] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return REEL_SCALE_DEFAULT;
    }
    const stored = window.localStorage.getItem(REEL_SCALE_STORAGE_KEY);
    if (!stored) {
      return REEL_SCALE_DEFAULT;
    }
    const parsed = Number(stored);
    if (!Number.isFinite(parsed)) {
      return REEL_SCALE_DEFAULT;
    }
    return clampReelScale(Math.round(parsed * 100) / 100);
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem('player.sentenceImageReelVisible', isSentenceImageReelVisible ? 'true' : 'false');
    } catch {
      // ignore
    }
  }, [isSentenceImageReelVisible]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(REEL_SCALE_STORAGE_KEY, String(reelScale));
    } catch {
      // ignore
    }
  }, [reelScale]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const isTypingTarget = (target: EventTarget | null): target is HTMLElement => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      if (target.isContentEditable) {
        return true;
      }
      const tag = target.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };

    const handleShortcut = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.altKey ||
        event.metaKey ||
        event.ctrlKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      const key = event.key?.toLowerCase();
      const code = event.code;
      const isPlusKey = key === '+' || key === '=' || code === 'Equal' || code === 'NumpadAdd';
      const isMinusKey = key === '-' || key === '_' || code === 'Minus' || code === 'NumpadSubtract';

      if (event.shiftKey && (isPlusKey || isMinusKey)) {
        event.preventDefault();
        setReelScale((current) => {
          const delta = isPlusKey ? REEL_SCALE_STEP : -REEL_SCALE_STEP;
          const next = clampReelScale(Math.round((current + delta) * 100) / 100);
          return next;
        });
        return;
      }

      if (key !== 'r') {
        return;
      }
      event.preventDefault();
      setSentenceImageReelVisible((value) => !value);
    };

    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, []);

  const [imagePromptPlanSummary, setImagePromptPlanSummary] = useState<Record<string, unknown> | null>(null);
  const imagePromptPlanRetryRef = useRef(0);
  const imagePromptPlanSummaryUrl = useMemo(() => {
    if (isExportMode) {
      return 'metadata/image_prompt_plan_summary.json';
    }
    if (!jobId) {
      return null;
    }
    const relativePath = 'metadata/image_prompt_plan_summary.json';
    try {
      return isLibraryMediaOrigin
        ? resolveLibraryMediaUrl(jobId, relativePath)
        : resolveStoragePath(jobId, relativePath);
    } catch {
      return null;
    }
  }, [isExportMode, isLibraryMediaOrigin, jobId]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    setImagePromptPlanSummary(null);
    imagePromptPlanRetryRef.current = 0;
    if (isExportMode) {
      return;
    }
    if (!imagePromptPlanSummaryUrl) {
      return;
    }

    let cancelled = false;
    let retryTimer: number | null = null;

    const loadSummary = () => {
      fetch(imagePromptPlanSummaryUrl, { credentials: 'include' })
        .then(async (response) => {
          if (!response.ok) {
            return null;
          }
          try {
            const payload = (await response.json()) as unknown;
            return payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : null;
          } catch {
            return null;
          }
        })
        .then((payload) => {
          if (cancelled) {
            return;
          }
          if (payload) {
            setImagePromptPlanSummary(payload);
            return;
          }
          if (imagePromptPlanRetryRef.current < 4) {
            imagePromptPlanRetryRef.current += 1;
            retryTimer = window.setTimeout(loadSummary, 1500);
          }
        })
        .catch(() => {
          if (cancelled) {
            return;
          }
          if (imagePromptPlanRetryRef.current < 4) {
            imagePromptPlanRetryRef.current += 1;
            retryTimer = window.setTimeout(loadSummary, 1500);
          }
        });
    };

    loadSummary();

    return () => {
      cancelled = true;
      if (retryTimer !== null) {
        window.clearTimeout(retryTimer);
      }
    };
  }, [imagePromptPlanSummaryUrl]);

  const batchStartCandidatesFromFiles = useMemo(() => {
    const files = chunk?.files ?? [];
    if (!files.length) {
      return [] as number[];
    }
    const starts = new Set<number>();
    files.forEach((file) => {
      const candidates = [
        typeof file.relative_path === 'string' ? file.relative_path : null,
        typeof file.path === 'string' ? file.path : null,
        typeof file.url === 'string' ? file.url : null,
      ];
      for (const candidate of candidates) {
        if (!candidate) {
          continue;
        }
        const inferred = parseBatchStartFromBatchImagePath(candidate);
        if (inferred !== null) {
          starts.add(inferred);
          break;
        }
      }
    });
    return Array.from(starts).sort((a, b) => a - b);
  }, [chunk?.files]);

  const batchSizeFromFiles = useMemo(() => {
    if (batchStartCandidatesFromFiles.length < 2) {
      return null;
    }
    const counts = new Map<number, number>();
    let bestSize: number | null = null;
    let bestCount = 0;
    for (let index = 1; index < batchStartCandidatesFromFiles.length; index += 1) {
      const diff = batchStartCandidatesFromFiles[index] - batchStartCandidatesFromFiles[index - 1];
      if (!Number.isFinite(diff) || diff <= 0) {
        continue;
      }
      const nextCount = (counts.get(diff) ?? 0) + 1;
      counts.set(diff, nextCount);
      if (nextCount > bestCount || (nextCount === bestCount && (bestSize === null || diff < bestSize))) {
        bestSize = diff;
        bestCount = nextCount;
      }
    }
    return bestSize;
  }, [batchStartCandidatesFromFiles]);

  const promptPlanBatchSize = useMemo(() => {
    const summary = imagePromptPlanSummary;
    if (!summary) {
      return null;
    }
    const quality = summary.quality;
    if (!quality || typeof quality !== 'object') {
      return null;
    }
    const record = quality as Record<string, unknown>;
    const raw = record.prompt_batch_size ?? record.promptBatchSize ?? null;
    const parsed = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN;
    if (!Number.isFinite(parsed)) {
      return null;
    }
    return Math.max(1, Math.trunc(parsed));
  }, [imagePromptPlanSummary]);

  const reelWindowSize = 7;
  const reelPrefetchBuffer = 2;
  const reelEagerPreloadBuffer = 2;

  const promptPlanSentenceRange = useMemo(() => {
    const summary = imagePromptPlanSummary;
    if (!summary || typeof summary !== 'object') {
      return null;
    }
    const record = summary as Record<string, unknown>;
    const rawStart = record.start_sentence ?? record.startSentence ?? null;
    const rawEnd = record.end_sentence ?? record.endSentence ?? null;
    const startParsed = typeof rawStart === 'number' ? rawStart : typeof rawStart === 'string' ? Number(rawStart) : NaN;
    const endParsed = typeof rawEnd === 'number' ? rawEnd : typeof rawEnd === 'string' ? Number(rawEnd) : NaN;
    if (!Number.isFinite(startParsed) || !Number.isFinite(endParsed)) {
      return null;
    }
    const start = Math.max(1, Math.trunc(startParsed));
    const end = Math.max(start, Math.trunc(endParsed));
    return { start, end };
  }, [imagePromptPlanSummary]);

  const activeImageBatchSize = useMemo(() => {
    const entries = chunk?.sentences ?? null;
    const entry =
      entries && entries.length > 0
        ? entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))]
        : null;
    const imagePayload = entry?.image ?? null;
    const raw = imagePayload?.batch_size ?? (imagePayload as any)?.batchSize ?? null;
    const parsed = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN;
    if (Number.isFinite(parsed)) {
      return Math.max(1, Math.trunc(parsed));
    }
    const rawStart = imagePayload?.batch_start_sentence ?? (imagePayload as any)?.batchStartSentence ?? null;
    const rawEnd = imagePayload?.batch_end_sentence ?? (imagePayload as any)?.batchEndSentence ?? null;
    const startParsed = typeof rawStart === 'number' ? rawStart : typeof rawStart === 'string' ? Number(rawStart) : NaN;
    const endParsed = typeof rawEnd === 'number' ? rawEnd : typeof rawEnd === 'string' ? Number(rawEnd) : NaN;
    if (Number.isFinite(startParsed) && Number.isFinite(endParsed) && endParsed >= startParsed) {
      return Math.max(1, Math.trunc(endParsed) - Math.trunc(startParsed) + 1);
    }
    if (typeof promptPlanBatchSize === 'number' && Number.isFinite(promptPlanBatchSize)) {
      return Math.max(1, Math.trunc(promptPlanBatchSize));
    }
    if (typeof batchSizeFromFiles === 'number' && Number.isFinite(batchSizeFromFiles)) {
      return Math.max(1, Math.trunc(batchSizeFromFiles));
    }
    const explicitPath =
      (typeof imagePayload?.path === 'string' && imagePayload.path.trim()) ||
      (typeof entry?.image_path === 'string' && entry.image_path.trim()) ||
      (typeof entry?.imagePath === 'string' && entry.imagePath.trim()) ||
      null;
    if (explicitPath && explicitPath.includes('/images/batches/batch_')) {
      return 10;
    }
    return 1;
  }, [activeSentenceIndex, batchSizeFromFiles, chunk?.sentences, promptPlanBatchSize]);

  const resolveBatchStartForSentence = useCallback(
    (sentenceNumber: number) => {
      const size = Math.max(1, Math.trunc(activeImageBatchSize));
      if (size <= 1) {
        return Math.max(1, Math.trunc(sentenceNumber));
      }
      const anchor = promptPlanSentenceRange?.start ?? minSentenceBound;
      const base = Math.max(1, Math.trunc(anchor));
      const current = Math.max(1, Math.trunc(sentenceNumber));
      const offset = Math.max(0, current - base);
      return base + Math.floor(offset / size) * size;
    },
    [activeImageBatchSize, minSentenceBound, promptPlanSentenceRange],
  );

  const reelWindowBounds = useMemo(() => {
    const base = Math.max(1, Math.trunc(activeSentenceNumber));
    const rangeStart = promptPlanSentenceRange?.start ?? minSentenceBound;
    const rangeEnd = promptPlanSentenceRange?.end ?? maxSentenceBound ?? chunk?.endSentence ?? base;
    const boundedStart = Math.max(minSentenceBound, rangeStart);
    const boundedEnd =
      rangeEnd === null
        ? null
        : Math.max(boundedStart, Math.min(rangeEnd, maxSentenceBound ?? rangeEnd));
    const halfWindow = Math.max(0, Math.floor(reelWindowSize / 2));

    let windowStart = base - halfWindow;
    let windowEnd = base + halfWindow;

    if (boundedEnd !== null && windowEnd > boundedEnd) {
      const overshoot = windowEnd - boundedEnd;
      windowEnd = boundedEnd;
      windowStart -= overshoot;
    }
    if (windowStart < boundedStart) {
      const overshoot = boundedStart - windowStart;
      windowStart = boundedStart;
      windowEnd = boundedEnd !== null ? Math.min(boundedEnd, windowEnd + overshoot) : windowEnd + overshoot;
    }
    if (boundedEnd !== null) {
      windowEnd = Math.min(windowEnd, boundedEnd);
    }
    windowStart = Math.max(windowStart, boundedStart);

    if (boundedEnd !== null && windowStart > boundedEnd) {
      windowStart = boundedEnd;
      windowEnd = boundedEnd;
    }

    return {
      base,
      start: Math.max(1, Math.trunc(windowStart)),
      end: Math.max(1, Math.trunc(windowEnd)),
      boundedStart,
      boundedEnd,
    };
  }, [
    activeSentenceNumber,
    chunk?.endSentence,
    maxSentenceBound,
    minSentenceBound,
    promptPlanSentenceRange,
    reelWindowSize,
  ]);

  const reelSentenceSlots = useMemo(() => {
    const { base, start, end } = reelWindowBounds;
    const slots: number[] = [];
    for (let candidate = start; candidate <= end; candidate += 1) {
      slots.push(candidate);
    }
    if (slots.length === 0) {
      slots.push(base);
    }
    return slots;
  }, [reelWindowBounds]);

  const reelPrefetchSlots = useMemo(() => {
    if (reelPrefetchBuffer <= 0) {
      return [] as number[];
    }
    const { start, end, boundedStart, boundedEnd } = reelWindowBounds;
    const visible = new Set(reelSentenceSlots);
    const slots: number[] = [];

    for (let offset = 1; offset <= reelPrefetchBuffer; offset += 1) {
      const forward = end + offset;
      const back = start - offset;
      if (
        forward >= boundedStart &&
        (boundedEnd === null || forward <= boundedEnd) &&
        !visible.has(forward)
      ) {
        slots.push(forward);
      }
      if (
        back >= boundedStart &&
        (boundedEnd === null || back <= boundedEnd) &&
        !visible.has(back)
      ) {
        slots.push(back);
      }
    }

    return slots;
  }, [reelPrefetchBuffer, reelSentenceSlots, reelWindowBounds]);

  const reelEagerSlots = useMemo(() => {
    if (reelEagerPreloadBuffer <= 0) {
      return [] as number[];
    }
    const { boundedStart, boundedEnd } = reelWindowBounds;
    const base = Math.max(1, Math.trunc(activeSentenceNumber));
    const upperBound = boundedEnd ?? Number.POSITIVE_INFINITY;
    const slots: number[] = [];
    for (let offset = 1; offset <= reelEagerPreloadBuffer; offset += 1) {
      const forward = base + offset;
      const back = base - offset;
      if (forward >= boundedStart && forward <= upperBound) {
        slots.push(forward);
      }
      if (back >= boundedStart && back <= upperBound) {
        slots.push(back);
      }
    }
    return slots;
  }, [activeSentenceNumber, reelEagerPreloadBuffer, reelWindowBounds]);

  const reelPreloadSlots = useMemo(() => {
    const merged = new Set<number>();
    reelSentenceSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    reelPrefetchSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    reelEagerSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    return Array.from(merged);
  }, [reelEagerSlots, reelPrefetchSlots, reelSentenceSlots]);

  const chunkSentenceByNumber = useMemo(() => {
    const baseMap = exportSentenceByNumber ? new Map(exportSentenceByNumber) : new Map<number, ChunkSentenceMetadata>();
    const entries = chunk?.sentences ?? null;
    if (!entries || entries.length === 0) {
      return baseMap;
    }
    entries.forEach((entry) => {
      const raw = entry?.sentence_number ?? null;
      if (typeof raw !== 'number' || !Number.isFinite(raw)) {
        return;
      }
      baseMap.set(Math.max(1, Math.trunc(raw)), entry);
    });
    return baseMap;
  }, [chunk?.sentences, exportSentenceByNumber]);

  const hasGeneratedImages = useMemo(() => {
    for (const entry of chunkSentenceByNumber.values()) {
      const imagePayload = entry?.image ?? null;
      const explicit =
        (typeof imagePayload?.path === 'string' && imagePayload.path.trim()) ||
        (typeof entry?.image_path === 'string' && entry.image_path.trim()) ||
        (typeof entry?.imagePath === 'string' && entry.imagePath.trim()) ||
        null;
      if (explicit) {
        return true;
      }
    }
    return false;
  }, [chunkSentenceByNumber]);

  const isReelEnabled = isSentenceImageReelVisible && hasGeneratedImages;

  const activeSentenceImagePath = useMemo(() => {
    const entries = chunk?.sentences ?? null;
    if (entries && entries.length > 0) {
      const entry = entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))];
      const imagePayload = entry?.image ?? null;
      const explicit =
        (typeof imagePayload?.path === 'string' && imagePayload.path.trim()) ||
        (typeof entry?.image_path === 'string' && entry.image_path.trim()) ||
        (typeof entry?.imagePath === 'string' && entry.imagePath.trim()) ||
        null;
      if (explicit) {
        return explicit.trim();
      }
    }

    const rangeFragment = chunk?.rangeFragment ?? null;
    if (!rangeFragment || !jobId) {
      return null;
    }
    const targetSentence =
      activeImageBatchSize > 1 ? resolveBatchStartForSentence(activeSentenceNumber) : activeSentenceNumber;
    const padded = String(targetSentence).padStart(5, '0');
    if (activeImageBatchSize > 1) {
      return `media/images/batches/batch_${padded}.png`;
    }
    return `media/images/${rangeFragment}/sentence_${padded}.png`;
  }, [
    activeImageBatchSize,
    activeSentenceIndex,
    activeSentenceNumber,
    chunk?.rangeFragment,
    chunk?.sentences,
    jobId,
    resolveBatchStartForSentence,
  ]);

  const reelImageInfoCacheRef = useRef<Map<number, SentenceImageInfoResponse>>(new Map());
  const reelImageInfoInflightRef = useRef<Set<number>>(new Set());
  const reelImageInfoMissingRef = useRef<Set<number>>(new Set());
  const [reelImageInfoVersion, setReelImageInfoVersion] = useState(0);
  const [reelImageRetryTokens, setReelImageRetryTokens] = useState<Record<string, number>>({});
  const reelScrollRef = useRef<HTMLDivElement | null>(null);
  const reelPrefetchCacheRef = useRef<Set<string>>(new Set());
  const [reelReady, setReelReady] = useState(true);

  useEffect(() => {
    reelImageInfoCacheRef.current.clear();
    reelImageInfoInflightRef.current.clear();
    reelPrefetchCacheRef.current.clear();
    reelImageInfoMissingRef.current.clear();
    setReelImageInfoVersion((value) => value + 1);
    setReelImageRetryTokens({});
  }, [jobId]);

  const reelLookupSlots = useMemo(() => {
    const merged = new Set<number>();
    reelPreloadSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    return Array.from(merged);
  }, [reelPreloadSlots]);

  const [reelImageFailures, setReelImageFailures] = useState<Record<string, boolean>>({});
  useEffect(() => {
    setReelImageFailures({});
    setReelImageRetryTokens({});
    reelPrefetchCacheRef.current.clear();
    reelImageInfoMissingRef.current.clear();
  }, [imageRefreshToken, jobId]);

  useEffect(() => {
    if (!jobId || !isReelEnabled) {
      return;
    }
    const failedKeys = Object.entries(reelImageFailures)
      .filter(([, failed]) => failed)
      .map(([key]) => key);
    if (failedKeys.length === 0) {
      return;
    }

    const timer = window.setTimeout(() => {
      setReelImageFailures((previous) => {
        const next: Record<string, boolean> = { ...previous };
        failedKeys.forEach((key) => {
          delete next[key];
        });
        return next;
      });
      setReelImageRetryTokens((previous) => {
        const next: Record<string, number> = { ...previous };
        failedKeys.forEach((key) => {
          next[key] = (next[key] ?? 0) + 1;
        });
        return next;
      });
    }, 3000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [isReelEnabled, jobId, reelImageFailures]);

  useEffect(() => {
    if (!isReelEnabled) {
      setReelReady(true);
      return;
    }
    setReelReady(false);
  }, [isReelEnabled, jobId]);

  const resolveSentenceImageUrl = useCallback(
    (path: string | null, sentenceNumber?: number | null) => {
      const candidate = (path ?? '').trim();
      if (!candidate) {
        return null;
      }
      if (candidate.startsWith('data:') || candidate.startsWith('blob:')) {
        return candidate;
      }

      const retryToken =
        sentenceNumber && Number.isFinite(sentenceNumber)
          ? reelImageRetryTokens[String(sentenceNumber)] ?? 0
          : 0;
      const refreshToken = imageRefreshToken + retryToken;

      const addRefreshToken = (url: string) => {
        if (refreshToken <= 0) {
          return url;
        }
        try {
          const resolved = new URL(url, typeof window !== 'undefined' ? window.location.origin : undefined);
          resolved.searchParams.set('v', String(refreshToken));
          return resolved.toString();
        } catch {
          const token = `v=${encodeURIComponent(String(refreshToken))}`;
          const hashIndex = url.indexOf('#');
          const base = hashIndex >= 0 ? url.slice(0, hashIndex) : url;
          const hash = hashIndex >= 0 ? url.slice(hashIndex) : '';
          const decorated = base.includes('?') ? `${base}&${token}` : `${base}?${token}`;
          return `${decorated}${hash}`;
        }
      };

      if (isExportMode) {
        const resolved = coerceExportPath(candidate, jobId);
        return resolved ? addRefreshToken(resolved) : null;
      }

      if (candidate.includes('://')) {
        return addRefreshToken(candidate);
      }

      if (candidate.startsWith('/api/') || candidate.startsWith('/storage/') || candidate.startsWith('/pipelines/')) {
        return addRefreshToken(appendAccessToken(candidate));
      }

      if (!jobId) {
        return null;
      }

      const normalisedCandidate = candidate.replace(/\\+/g, '/');
      const [pathPart, hashPart] = normalisedCandidate.split('#', 2);
      const [pathOnly, queryPart] = pathPart.split('?', 2);

      const coerceRelative = (value: string): string => {
        const trimmed = value.replace(/^\/+/, '');
        if (!trimmed) {
          return '';
        }

        const marker = `/${jobId}/`;
        const markerIndex = trimmed.indexOf(marker);
        if (markerIndex >= 0) {
          return trimmed.slice(markerIndex + marker.length);
        }

        const segments = trimmed.split('/');
        const mediaIndex = segments.lastIndexOf('media');
        if (mediaIndex >= 0) {
          return segments.slice(mediaIndex).join('/');
        }

        const metadataIndex = segments.lastIndexOf('metadata');
        if (metadataIndex >= 0) {
          return segments.slice(metadataIndex).join('/');
        }

        return trimmed;
      };

      const relativePath = coerceRelative(pathOnly);
      if (!relativePath) {
        return null;
      }

      try {
        const baseUrl = isLibraryMediaOrigin
          ? resolveLibraryMediaUrl(jobId, relativePath)
          : resolveStoragePath(jobId, relativePath);
        if (!baseUrl) {
          return null;
        }
        const withQuery = queryPart ? `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}${queryPart}` : baseUrl;
        const withHash = hashPart ? `${withQuery}#${hashPart}` : withQuery;
        return addRefreshToken(withHash);
      } catch {
        return null;
      }
    },
    [imageRefreshToken, isExportMode, isLibraryMediaOrigin, jobId, reelImageRetryTokens],
  );

  const resolveReelImagePath = useCallback(
    (sentenceNumber: number, preferActive: boolean) => {
      if (!Number.isFinite(sentenceNumber)) {
        return null;
      }
      const cache = reelImageInfoCacheRef.current;
      const rangeFragment = chunk?.rangeFragment ?? null;
      const startSentence = chunk?.startSentence ?? null;
      const endSentence = chunk?.endSentence ?? null;

      const chunkEntry = chunkSentenceByNumber.get(sentenceNumber) ?? null;
      const chunkImagePayload = chunkEntry?.image ?? null;
      const explicitPath =
        (typeof chunkImagePayload?.path === 'string' && chunkImagePayload.path.trim()) ||
        (typeof chunkEntry?.image_path === 'string' && chunkEntry.image_path.trim()) ||
        (typeof chunkEntry?.imagePath === 'string' && chunkEntry.imagePath.trim()) ||
        null;
      const cached = cache.get(sentenceNumber) ?? null;

      const resolvedRangeFragment =
        (typeof rangeFragment === 'string' && rangeFragment.trim() && (
          (typeof startSentence === 'number' &&
            typeof endSentence === 'number' &&
            Number.isFinite(startSentence) &&
            Number.isFinite(endSentence) &&
            sentenceNumber >= Math.trunc(startSentence) &&
            sentenceNumber <= Math.trunc(endSentence)) ||
          chunkEntry
        ))
          ? rangeFragment.trim()
          : typeof cached?.range_fragment === 'string' && cached.range_fragment.trim()
            ? cached.range_fragment.trim()
            : null;

      const padded = String(sentenceNumber).padStart(5, '0');
      const computedPath = (() => {
        if (activeImageBatchSize > 1) {
          const batchStart = resolveBatchStartForSentence(sentenceNumber);
          const batchPadded = String(batchStart).padStart(5, '0');
          return `media/images/batches/batch_${batchPadded}.png`;
        }
        if (resolvedRangeFragment) {
          return `media/images/${resolvedRangeFragment}/sentence_${padded}.png`;
        }
        return null;
      })();
      const preferBatchPath = activeImageBatchSize > 1;
      const isBatchPath = (value: string | null) =>
        value !== null &&
        (parseBatchStartFromBatchImagePath(value) !== null || value.includes('/images/batches/batch_'));
      const cachedPath =
        typeof cached?.relative_path === 'string' && cached.relative_path.trim()
          ? cached.relative_path.trim()
          : null;

      if (preferActive && sentenceNumber === activeSentenceNumber && activeSentenceImagePath) {
        return activeSentenceImagePath;
      }

      if (explicitPath && (!preferBatchPath || isBatchPath(explicitPath))) {
        return explicitPath.trim();
      }
      if (cachedPath && (!preferBatchPath || isBatchPath(cachedPath))) {
        return cachedPath;
      }
      return computedPath;
    },
    [
      activeImageBatchSize,
      activeSentenceImagePath,
      activeSentenceNumber,
      chunk?.endSentence,
      chunk?.rangeFragment,
      chunk?.startSentence,
      chunkSentenceByNumber,
      resolveBatchStartForSentence,
    ],
  );

  useEffect(() => {
    if (isExportMode) {
      return;
    }
    if (!jobId) {
      return;
    }
    if (!isReelEnabled) {
      return;
    }
    const cache = reelImageInfoCacheRef.current;
    const inflight = reelImageInfoInflightRef.current;
    const required = reelLookupSlots.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    if (!required.length) {
      return;
    }

    let cancelled = false;
    const targets = required.filter((sentenceNumber) => {
      if (cache.has(sentenceNumber) || inflight.has(sentenceNumber)) {
        return false;
      }
      const path = resolveReelImagePath(sentenceNumber, false);
      return !path;
    });
    if (!targets.length) {
      return;
    }
    targets.forEach((sentenceNumber) => {
      inflight.add(sentenceNumber);
    });
    fetchSentenceImageInfoBatch(jobId, targets)
      .then((items) => {
        if (cancelled) {
          return;
        }
        let updated = false;
        const resolved = new Set<number>();
        items.forEach((info) => {
          if (!info || typeof info.sentence_number !== 'number' || !Number.isFinite(info.sentence_number)) {
            return;
          }
          resolved.add(info.sentence_number);
          cache.set(info.sentence_number, info);
          reelImageInfoMissingRef.current.delete(info.sentence_number);
          updated = true;
        });
        targets.forEach((sentenceNumber) => {
          if (!resolved.has(sentenceNumber)) {
            reelImageInfoMissingRef.current.add(sentenceNumber);
          }
        });
        if (updated || resolved.size !== targets.length) {
          setReelImageInfoVersion((value) => value + 1);
        }
      })
      .catch(() => {
        // ignore
      })
      .finally(() => {
        targets.forEach((sentenceNumber) => {
          inflight.delete(sentenceNumber);
        });
      });

    return () => {
      cancelled = true;
    };
  }, [isExportMode, isReelEnabled, jobId, reelLookupSlots, resolveReelImagePath]);

  const reelFrames = useMemo(() => {
    const cache = reelImageInfoCacheRef.current;
    const rangeFragment = chunk?.rangeFragment ?? null;
    const startSentence = chunk?.startSentence ?? null;
    const endSentence = chunk?.endSentence ?? null;

    return reelSentenceSlots.map((sentenceNumber) => {
      if (typeof sentenceNumber !== 'number' || !Number.isFinite(sentenceNumber)) {
        return {
          sentenceNumber: null as number | null,
          url: null as string | null,
          imagePath: null as string | null,
          rangeFragment: null as string | null,
          sentenceText: null as string | null,
          prompt: null as string | null,
          negativePrompt: null as string | null,
          isActive: false,
          isMissing: true,
        };
      }

      const key = String(sentenceNumber);
      const failed = reelImageFailures[key] ?? false;
      const isActive = sentenceNumber === activeSentenceNumber;

      const chunkEntry = chunkSentenceByNumber.get(sentenceNumber) ?? null;
      const chunkImagePayload = chunkEntry?.image ?? null;
      const chunkSentenceTextRaw = typeof chunkEntry?.original?.text === 'string' ? chunkEntry.original.text : null;
      const chunkSentenceText =
        typeof chunkSentenceTextRaw === 'string' && chunkSentenceTextRaw.trim() ? chunkSentenceTextRaw.trim() : null;
      const chunkPrompt =
        typeof chunkImagePayload?.prompt === 'string' && chunkImagePayload.prompt.trim()
          ? chunkImagePayload.prompt.trim()
          : null;
      const chunkNegative =
        typeof chunkImagePayload?.negative_prompt === 'string' && chunkImagePayload.negative_prompt.trim()
          ? chunkImagePayload.negative_prompt.trim()
          : null;

      const cached = cache.get(sentenceNumber) ?? null;

      const resolvedRangeFragment =
        (typeof rangeFragment === 'string' && rangeFragment.trim() && (
          (typeof startSentence === 'number' &&
            typeof endSentence === 'number' &&
            Number.isFinite(startSentence) &&
            Number.isFinite(endSentence) &&
            sentenceNumber >= Math.trunc(startSentence) &&
            sentenceNumber <= Math.trunc(endSentence)) ||
          chunkEntry
        ))
          ? rangeFragment.trim()
          : typeof cached?.range_fragment === 'string' && cached.range_fragment.trim()
            ? cached.range_fragment.trim()
            : null;

      const imagePath = resolveReelImagePath(sentenceNumber, isActive);

      const url = failed ? null : resolveSentenceImageUrl(imagePath, sentenceNumber);

      return {
        sentenceNumber,
        url,
        imagePath,
        rangeFragment: resolvedRangeFragment,
        sentenceText:
          chunkSentenceText ??
          (typeof cached?.sentence === 'string' && cached.sentence.trim() ? cached.sentence.trim() : null),
        prompt:
          chunkPrompt ??
          (typeof cached?.prompt === 'string' && cached.prompt.trim() ? cached.prompt.trim() : null),
        negativePrompt:
          chunkNegative ??
          (typeof cached?.negative_prompt === 'string' && cached.negative_prompt.trim()
            ? cached.negative_prompt.trim()
            : null),
        isActive,
        isMissing: !imagePath,
      };
    });
  }, [
    activeSentenceNumber,
    chunk?.endSentence,
    chunk?.rangeFragment,
    chunk?.startSentence,
    chunkSentenceByNumber,
    reelImageFailures,
    reelImageInfoVersion,
    reelSentenceSlots,
    resolveReelImagePath,
    resolveSentenceImageUrl,
  ]);

  const reelVisibleFrames = useMemo(() => reelFrames, [reelFrames]);

  useEffect(() => {
    if (!jobId || !isReelEnabled) {
      return;
    }
    if (!reelPreloadSlots.length) {
      return;
    }
    const cache = reelPrefetchCacheRef.current;
    reelPreloadSlots.forEach((sentenceNumber) => {
      if (typeof sentenceNumber !== 'number' || !Number.isFinite(sentenceNumber)) {
        return;
      }
      const imagePath = resolveReelImagePath(sentenceNumber, false);
      const url = resolveSentenceImageUrl(imagePath, sentenceNumber);
      if (!url || cache.has(url)) {
        return;
      }
      const image = new Image();
      image.src = url;
      cache.add(url);
    });
  }, [
    isReelEnabled,
    jobId,
    reelImageInfoVersion,
    reelPreloadSlots,
    resolveReelImagePath,
    resolveSentenceImageUrl,
  ]);

  useEffect(() => {
    if (!isReelEnabled || reelReady) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const timeout = window.setTimeout(() => {
      setReelReady(true);
    }, 1200);
    return () => window.clearTimeout(timeout);
  }, [isReelEnabled, jobId, reelReady]);

  useEffect(() => {
    if (!isReelEnabled) {
      return;
    }
    if (reelVisibleFrames.length === 0) {
      return;
    }
    const missing = reelImageInfoMissingRef.current;
    const ready = reelVisibleFrames.every((frame) => {
      const sentenceNumber = frame.sentenceNumber;
      if (!sentenceNumber || !Number.isFinite(sentenceNumber)) {
        return true;
      }
      if (frame.url) {
        return true;
      }
      if (missing.has(sentenceNumber)) {
        return true;
      }
      if (reelImageFailures[String(sentenceNumber)]) {
        return true;
      }
      return false;
    });
    if (ready) {
      setReelReady(true);
    }
  }, [isReelEnabled, reelImageFailures, reelImageInfoVersion, reelVisibleFrames]);

  useLayoutEffect(() => {
    if (!isReelEnabled) {
      return;
    }
    const container = reelScrollRef.current;
    if (!container) {
      return;
    }
    const activeKey = typeof activeSentenceNumber === 'number' ? activeSentenceNumber : null;
    if (!activeKey) {
      return;
    }
    const activeNode = container.querySelector(
      `[data-reel-sentence="${activeKey}"]`,
    ) as HTMLElement | null;
    if (!activeNode) {
      return;
    }
    const containerRect = container.getBoundingClientRect();
    const activeRect = activeNode.getBoundingClientRect();
    if (!(containerRect.width > 0 && activeRect.width > 0)) {
      return;
    }
    const containerCenter = containerRect.left + containerRect.width / 2;
    const activeCenter = activeRect.left + activeRect.width / 2;
    const offset = activeCenter - containerCenter;
    const maxScroll = Math.max(0, container.scrollWidth - container.clientWidth);
    const target = Math.max(0, Math.min(maxScroll, container.scrollLeft + offset));
    if (Math.abs(container.scrollLeft - target) < 1) {
      return;
    }
    container.scrollTo({
      left: target,
      behavior: 'auto',
    });
  }, [activeSentenceNumber, isFullscreen, isReelEnabled, reelScale, reelVisibleFrames.length]);

  const resolveReelSentenceSeekTarget = useCallback(
    (sentenceNumber: number) => {
      if (!Number.isFinite(sentenceNumber)) {
        return null;
      }
      const targetSentence = Math.max(1, Math.trunc(sentenceNumber));
      if (!timelineSentences || timelineSentences.length === 0) {
        return null;
      }

      const resolvedRuntime = (() => {
        const match = timelineSentences.find((entry) => entry.sentenceNumber === targetSentence) ?? null;
        if (match) {
          return match;
        }
        const start = chunk?.startSentence ?? null;
        if (typeof start === 'number' && Number.isFinite(start)) {
          const candidateIndex = targetSentence - Math.max(1, Math.trunc(start));
          if (candidateIndex >= 0 && candidateIndex < timelineSentences.length) {
            return timelineSentences[candidateIndex] ?? null;
          }
        }
        return null;
      })();

      if (!resolvedRuntime) {
        return null;
      }

      const rawStartTime = resolvedRuntime.startTime;
      if (typeof rawStartTime !== 'number' || !Number.isFinite(rawStartTime)) {
        return { index: resolvedRuntime.index, time: null as number | null };
      }

      const epsilon = 0.02;
      const timelineStartTime = Math.max(0, rawStartTime - epsilon);

      const rawTotal = timelineSentences[timelineSentences.length - 1]?.endTime ?? null;
      const timelineTotal =
        typeof rawTotal === 'number' && Number.isFinite(rawTotal) && rawTotal > 0 ? rawTotal : null;

      let resolvedDuration = audioDuration;
      if (!(typeof resolvedDuration === 'number' && Number.isFinite(resolvedDuration) && resolvedDuration > 0)) {
        const normaliseUrl = (value: string) => value.split('?')[0].split('#')[0];
        const trackDurationForUrl = (url: string | null | undefined) => {
          if (!url || !audioTracks) {
            return null;
          }
          const needle = normaliseUrl(url);
          for (const track of Object.values(audioTracks)) {
            const candidateUrl = typeof track?.url === 'string' ? normaliseUrl(track.url) : null;
            if (candidateUrl && candidateUrl === needle) {
              const duration = track.duration ?? null;
              return typeof duration === 'number' && Number.isFinite(duration) && duration > 0 ? duration : null;
            }
          }
          return null;
        };

        resolvedDuration =
          trackDurationForUrl(effectiveAudioUrl) ??
          trackDurationForUrl(activeAudioUrl) ??
          (typeof audioTracks?.orig?.duration === 'number' &&
          Number.isFinite(audioTracks.orig.duration) &&
          audioTracks.orig.duration > 0
            ? audioTracks.orig.duration
            : null) ??
          (typeof audioTracks?.orig_trans?.duration === 'number' &&
          Number.isFinite(audioTracks.orig_trans.duration) &&
          audioTracks.orig_trans.duration > 0
            ? audioTracks.orig_trans.duration
            : null) ??
          (typeof audioTracks?.translation?.duration === 'number' &&
          Number.isFinite(audioTracks.translation.duration) &&
          audioTracks.translation.duration > 0
            ? audioTracks.translation.duration
            : null) ??
          (typeof audioTracks?.trans?.duration === 'number' &&
          Number.isFinite(audioTracks.trans.duration) &&
          audioTracks.trans.duration > 0
            ? audioTracks.trans.duration
            : null) ??
          null;
      }

      const duration =
        typeof resolvedDuration === 'number' && Number.isFinite(resolvedDuration) && resolvedDuration > 0
          ? resolvedDuration
          : null;

      if (timelineTotal !== null && duration !== null) {
        const ratio = Math.min(Math.max(timelineStartTime / timelineTotal, 0), 1);
        return { index: resolvedRuntime.index, time: ratio * duration };
      }

      return { index: resolvedRuntime.index, time: timelineStartTime };
    },
    [activeAudioUrl, audioDuration, audioTracks, chunk?.startSentence, effectiveAudioUrl, timelineSentences],
  );

  const syncPlayerToReelSentence = useCallback(
    (sentenceNumber: number) => {
      const target = resolveReelSentenceSeekTarget(sentenceNumber);
      if (!target) {
        return false;
      }
      setActiveSentenceIndex(target.index);
      if (target.time === null) {
        return true;
      }
      if (inlineAudioPlayingRef.current) {
        handleTokenSeek(target.time);
      } else {
        seekInlineAudioToTime(target.time);
      }
      return true;
    },
    [handleTokenSeek, resolveReelSentenceSeekTarget, seekInlineAudioToTime, setActiveSentenceIndex, inlineAudioPlayingRef],
  );

  const handleReelFrameClick = useCallback(
    (frame: SentenceImageFrame) => {
      const sentenceNumber = frame.sentenceNumber ?? null;
      if (!jobId || !sentenceNumber) {
        return;
      }
      if (!syncPlayerToReelSentence(sentenceNumber) && onRequestSentenceJump) {
        onRequestSentenceJump(sentenceNumber);
      }
    },
    [jobId, onRequestSentenceJump, syncPlayerToReelSentence],
  );

  const handleReelFrameError = useCallback((sentenceNumber: number) => {
    setReelImageFailures((previous) => ({ ...previous, [String(sentenceNumber)]: true }));
  }, []);

  const sentenceImageReelNode = useMemo(() => {
    if (!jobId || !isReelEnabled) {
      return null;
    }
    if (!reelReady) {
      return (
        <div
          className="player-panel__interactive-image-reel player-panel__interactive-image-reel--loading"
          aria-live="polite"
        >
          <div className="player-panel__interactive-image-reel-strip" role="list" aria-label="Loading sentence images">
            {Array.from({ length: reelWindowSize }).map((_, index) => (
              <div
                key={`loading-${index}`}
                className="player-panel__interactive-image-reel-slot"
                role="listitem"
                aria-hidden="true"
              >
                <div className="player-panel__interactive-image-reel-frame player-panel__interactive-image-reel-frame--loading">
                  <span className="player-panel__interactive-image-reel-placeholder" aria-hidden="true">
                    ...
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="player-panel__interactive-image-reel-status" role="status">
            Loading reel...
          </div>
        </div>
      );
    }
    if (reelVisibleFrames.length === 0) {
      return null;
    }
    return (
      <SentenceImageReel
        scrollRef={reelScrollRef}
        frames={reelVisibleFrames}
        onFrameClick={handleReelFrameClick}
        onFrameError={handleReelFrameError}
      />
    );
  }, [
    handleReelFrameClick,
    handleReelFrameError,
    isReelEnabled,
    jobId,
    reelReady,
    reelVisibleFrames,
    reelWindowSize,
  ]);

  return {
    sentenceImageReelNode,
    activeSentenceImagePath,
    reelScale,
  };
}
