import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { fetchSentenceImageInfoBatch, buildStorageUrl, resolveLibraryMediaUrl } from '../../api/client';
import type { ChunkSentenceMetadata, SentenceImageInfoResponse } from '../../api/dtos';
import { SentenceImageReel, type SentenceImageFrame } from './SentenceImageReel';
import {
  useReelScale,
  useReelVisibility,
  useReelWindowBounds,
  useImageUrlResolver,
  useBatchSize,
  extractPromptPlanBatchSize,
  extractPromptPlanSentenceRange,
  REEL_WINDOW_SIZE,
  getExportManifest,
  isBatchImagePath,
  parseBatchStartFromBatchImagePath,
} from './reel';
import type {
  UseSentenceImageReelArgs,
  UseSentenceImageReelResult,
  ImagePromptPlanSummary,
} from './reel';

// Re-export types for backward compatibility
export type { UseSentenceImageReelArgs, UseSentenceImageReelResult } from './reel';

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

  // Use modular hooks
  const { reelScale } = useReelScale();
  const { isVisible: isSentenceImageReelVisible } = useReelVisibility();

  // Sentence bounds
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

  // Export mode sentence map
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
    chunks.forEach((chunkData) => {
      const entries = chunkData?.sentences;
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

  // Image prompt plan summary
  const [imagePromptPlanSummary, setImagePromptPlanSummary] = useState<ImagePromptPlanSummary | null>(null);
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
        : buildStorageUrl(relativePath, jobId);
    } catch {
      return null;
    }
  }, [isExportMode, isLibraryMediaOrigin, jobId]);

  const hasImageMetadata = useMemo(() => {
    const entries = chunk?.sentences ?? null;
    if (!entries || entries.length === 0) {
      return false;
    }
    return entries.some((entry) => {
      const imagePayload = entry?.image ?? null;
      return Boolean(
        (typeof imagePayload?.path === 'string' && imagePayload.path.trim()) ||
          (typeof entry?.image_path === 'string' && entry.image_path.trim()) ||
          (typeof entry?.imagePath === 'string' && entry.imagePath.trim()),
      );
    });
  }, [chunk?.sentences]);

  // Load image prompt plan summary
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    setImagePromptPlanSummary(null);
    imagePromptPlanRetryRef.current = 0;
    if (isExportMode || !hasImageMetadata || !imagePromptPlanSummaryUrl) {
      return;
    }

    let cancelled = false;
    let retryTimer: number | null = null;

    const loadSummary = () => {
      fetch(imagePromptPlanSummaryUrl, { credentials: 'include' })
        .then(async (response) => {
          if (!response.ok) return null;
          try {
            const payload = (await response.json()) as unknown;
            return payload && typeof payload === 'object' ? (payload as ImagePromptPlanSummary) : null;
          } catch {
            return null;
          }
        })
        .then((payload) => {
          if (cancelled) return;
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
          if (cancelled) return;
          if (imagePromptPlanRetryRef.current < 4) {
            imagePromptPlanRetryRef.current += 1;
            retryTimer = window.setTimeout(loadSummary, 1500);
          }
        });
    };

    loadSummary();
    return () => {
      cancelled = true;
      if (retryTimer !== null) window.clearTimeout(retryTimer);
    };
  }, [hasImageMetadata, imagePromptPlanSummaryUrl, isExportMode]);

  const promptPlanBatchSize = useMemo(
    () => extractPromptPlanBatchSize(imagePromptPlanSummary),
    [imagePromptPlanSummary]
  );

  const promptPlanSentenceRange = useMemo(
    () => extractPromptPlanSentenceRange(imagePromptPlanSummary),
    [imagePromptPlanSummary]
  );

  // Batch size calculations
  const { activeImageBatchSize, resolveBatchStartForSentence } = useBatchSize({
    chunk,
    activeSentenceIndex,
    promptPlanBatchSize,
    minSentenceBound,
    promptPlanSentenceRange,
  });

  // Window bounds
  const { reelWindowBounds, reelSentenceSlots, reelPreloadSlots } = useReelWindowBounds({
    activeSentenceNumber,
    minSentenceBound,
    maxSentenceBound,
    promptPlanSentenceRange,
    chunkEndSentence: chunk?.endSentence,
  });

  // Chunk sentence map
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
      if (explicit) return true;
    }
    return false;
  }, [chunkSentenceByNumber]);

  const isReelEnabled = isSentenceImageReelVisible && hasGeneratedImages;

  // Image caching state
  const reelImageInfoCacheRef = useRef<Map<number, SentenceImageInfoResponse>>(new Map());
  const reelImageInfoInflightRef = useRef<Set<number>>(new Set());
  const reelImageInfoMissingRef = useRef<Set<number>>(new Set());
  const [reelImageInfoVersion, setReelImageInfoVersion] = useState(0);
  const [reelImageRetryTokens, setReelImageRetryTokens] = useState<Record<string, number>>({});
  const reelScrollRef = useRef<HTMLDivElement | null>(null);
  const reelPrefetchCacheRef = useRef<Set<string>>(new Set());
  const [reelReady, setReelReady] = useState(true);
  const [reelImageFailures, setReelImageFailures] = useState<Record<string, boolean>>({});

  // Reset caches on job change
  useEffect(() => {
    reelImageInfoCacheRef.current.clear();
    reelImageInfoInflightRef.current.clear();
    reelPrefetchCacheRef.current.clear();
    reelImageInfoMissingRef.current.clear();
    setReelImageInfoVersion((v) => v + 1);
    setReelImageRetryTokens({});
  }, [jobId]);

  useEffect(() => {
    setReelImageFailures({});
    setReelImageRetryTokens({});
    reelPrefetchCacheRef.current.clear();
    reelImageInfoMissingRef.current.clear();
  }, [imageRefreshToken, jobId]);

  // Image URL resolver
  const { resolveSentenceImageUrl } = useImageUrlResolver({
    jobId,
    isExportMode,
    isLibraryMediaOrigin,
    imageRefreshToken,
    reelImageRetryTokens,
  });

  // Resolve image path for a sentence
  const resolveReelImagePath = useCallback(
    (sentenceNumber: number, preferActive: boolean) => {
      if (!Number.isFinite(sentenceNumber)) return null;

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
      const cachedPath =
        typeof cached?.relative_path === 'string' && cached.relative_path.trim()
          ? cached.relative_path.trim()
          : null;

      // Get active sentence image path
      const activeSentenceImagePath = (() => {
        const entries = chunk?.sentences ?? null;
        if (entries && entries.length > 0) {
          const entry = entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))];
          const imagePayload = entry?.image ?? null;
          const explicit =
            (typeof imagePayload?.path === 'string' && imagePayload.path.trim()) ||
            (typeof entry?.image_path === 'string' && entry.image_path.trim()) ||
            (typeof entry?.imagePath === 'string' && entry.imagePath.trim()) ||
            null;
          if (explicit) return explicit.trim();
        }
        const rangeFragmentFallback = chunk?.rangeFragment ?? null;
        if (!rangeFragmentFallback || !jobId) return null;
        const targetSentence =
          activeImageBatchSize > 1 ? resolveBatchStartForSentence(activeSentenceNumber) : activeSentenceNumber;
        const paddedFallback = String(targetSentence).padStart(5, '0');
        if (activeImageBatchSize > 1) {
          return `media/images/batches/batch_${paddedFallback}.png`;
        }
        return `media/images/${rangeFragmentFallback}/sentence_${paddedFallback}.png`;
      })();

      if (preferActive && sentenceNumber === activeSentenceNumber && activeSentenceImagePath) {
        return activeSentenceImagePath;
      }

      if (explicitPath && (!preferBatchPath || isBatchImagePath(explicitPath))) {
        return explicitPath.trim();
      }
      if (cachedPath && (!preferBatchPath || isBatchImagePath(cachedPath))) {
        return cachedPath;
      }
      return computedPath;
    },
    [
      activeImageBatchSize,
      activeSentenceIndex,
      activeSentenceNumber,
      chunk?.endSentence,
      chunk?.rangeFragment,
      chunk?.sentences,
      chunk?.startSentence,
      chunkSentenceByNumber,
      jobId,
      resolveBatchStartForSentence,
    ],
  );

  // Active sentence image path
  const activeSentenceImagePath = useMemo(() => {
    return resolveReelImagePath(activeSentenceNumber, true);
  }, [activeSentenceNumber, resolveReelImagePath]);

  // Fetch missing image info
  const reelLookupSlots = useMemo(() => {
    const merged = new Set<number>();
    reelPreloadSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    return Array.from(merged);
  }, [reelPreloadSlots]);

  useEffect(() => {
    if (isExportMode || !jobId || !isReelEnabled) return;

    const cache = reelImageInfoCacheRef.current;
    const inflight = reelImageInfoInflightRef.current;
    const required = reelLookupSlots.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
    if (!required.length) return;

    let cancelled = false;
    const targets = required.filter((sentenceNumber) => {
      if (cache.has(sentenceNumber) || inflight.has(sentenceNumber)) return false;
      const path = resolveReelImagePath(sentenceNumber, false);
      return !path;
    });

    if (!targets.length) return;

    targets.forEach((sn) => inflight.add(sn));

    fetchSentenceImageInfoBatch(jobId, targets)
      .then((items) => {
        if (cancelled) return;
        let updated = false;
        const resolved = new Set<number>();
        items.forEach((info) => {
          if (!info || typeof info.sentence_number !== 'number' || !Number.isFinite(info.sentence_number)) return;
          resolved.add(info.sentence_number);
          cache.set(info.sentence_number, info);
          reelImageInfoMissingRef.current.delete(info.sentence_number);
          updated = true;
        });
        targets.forEach((sn) => {
          if (!resolved.has(sn)) reelImageInfoMissingRef.current.add(sn);
        });
        if (updated || resolved.size !== targets.length) {
          setReelImageInfoVersion((v) => v + 1);
        }
      })
      .catch(() => {})
      .finally(() => {
        targets.forEach((sn) => inflight.delete(sn));
      });

    return () => { cancelled = true; };
  }, [isExportMode, isReelEnabled, jobId, reelLookupSlots, resolveReelImagePath]);

  // Retry failed images
  useEffect(() => {
    if (!jobId || !isReelEnabled) return;
    const failedKeys = Object.entries(reelImageFailures)
      .filter(([, failed]) => failed)
      .map(([key]) => key);
    if (failedKeys.length === 0) return;

    const timer = window.setTimeout(() => {
      setReelImageFailures((prev) => {
        const next: Record<string, boolean> = { ...prev };
        failedKeys.forEach((key) => delete next[key]);
        return next;
      });
      setReelImageRetryTokens((prev) => {
        const next: Record<string, number> = { ...prev };
        failedKeys.forEach((key) => {
          next[key] = (next[key] ?? 0) + 1;
        });
        return next;
      });
    }, 3000);

    return () => window.clearTimeout(timer);
  }, [isReelEnabled, jobId, reelImageFailures]);

  // Reel ready state
  useEffect(() => {
    if (!isReelEnabled) {
      setReelReady(true);
      return;
    }
    setReelReady(false);
  }, [isReelEnabled, jobId]);

  // Build reel frames
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
      const chunkSentenceText = typeof chunkEntry?.original?.text === 'string' ? chunkEntry.original.text.trim() : null;
      const chunkPrompt = typeof chunkImagePayload?.prompt === 'string' ? chunkImagePayload.prompt.trim() : null;
      const chunkNegative = typeof chunkImagePayload?.negative_prompt === 'string' ? chunkImagePayload.negative_prompt.trim() : null;

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
        sentenceText: chunkSentenceText ?? (typeof cached?.sentence === 'string' && cached.sentence.trim() ? cached.sentence.trim() : null),
        prompt: chunkPrompt ?? (typeof cached?.prompt === 'string' && cached.prompt.trim() ? cached.prompt.trim() : null),
        negativePrompt: chunkNegative ?? (typeof cached?.negative_prompt === 'string' && cached.negative_prompt.trim() ? cached.negative_prompt.trim() : null),
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

  // Prefetch images
  useEffect(() => {
    if (!jobId || !isReelEnabled || !reelPreloadSlots.length) return;
    const cache = reelPrefetchCacheRef.current;
    reelPreloadSlots.forEach((sentenceNumber) => {
      if (typeof sentenceNumber !== 'number' || !Number.isFinite(sentenceNumber)) return;
      const imagePath = resolveReelImagePath(sentenceNumber, false);
      const url = resolveSentenceImageUrl(imagePath, sentenceNumber);
      if (!url || cache.has(url)) return;
      const image = new Image();
      image.src = url;
      cache.add(url);
    });
  }, [isReelEnabled, jobId, reelImageInfoVersion, reelPreloadSlots, resolveReelImagePath, resolveSentenceImageUrl]);

  // Reel ready timeout
  useEffect(() => {
    if (!isReelEnabled || reelReady) return;
    if (typeof window === 'undefined') return;
    const timeout = window.setTimeout(() => setReelReady(true), 1200);
    return () => window.clearTimeout(timeout);
  }, [isReelEnabled, jobId, reelReady]);

  // Check if reel is ready
  useEffect(() => {
    if (!isReelEnabled || reelVisibleFrames.length === 0) return;
    const missing = reelImageInfoMissingRef.current;
    const ready = reelVisibleFrames.every((frame) => {
      const sentenceNumber = frame.sentenceNumber;
      if (!sentenceNumber || !Number.isFinite(sentenceNumber)) return true;
      if (frame.url) return true;
      if (missing.has(sentenceNumber)) return true;
      if (reelImageFailures[String(sentenceNumber)]) return true;
      return false;
    });
    if (ready) setReelReady(true);
  }, [isReelEnabled, reelImageFailures, reelImageInfoVersion, reelVisibleFrames]);

  // Scroll to active frame
  useLayoutEffect(() => {
    if (!isReelEnabled) return;
    const container = reelScrollRef.current;
    if (!container) return;
    const activeKey = typeof activeSentenceNumber === 'number' ? activeSentenceNumber : null;
    if (!activeKey) return;
    const activeNode = container.querySelector(`[data-reel-sentence="${activeKey}"]`) as HTMLElement | null;
    if (!activeNode) return;
    const containerRect = container.getBoundingClientRect();
    const activeRect = activeNode.getBoundingClientRect();
    if (!(containerRect.width > 0 && activeRect.width > 0)) return;
    const containerCenter = containerRect.left + containerRect.width / 2;
    const activeCenter = activeRect.left + activeRect.width / 2;
    const offset = activeCenter - containerCenter;
    const maxScroll = Math.max(0, container.scrollWidth - container.clientWidth);
    const target = Math.max(0, Math.min(maxScroll, container.scrollLeft + offset));
    if (Math.abs(container.scrollLeft - target) < 1) return;
    container.scrollTo({ left: target, behavior: 'auto' });
  }, [activeSentenceNumber, isFullscreen, isReelEnabled, reelScale, reelVisibleFrames.length]);

  // Seek to sentence
  const resolveReelSentenceSeekTarget = useCallback(
    (sentenceNumber: number) => {
      if (!Number.isFinite(sentenceNumber)) return null;
      const targetSentence = Math.max(1, Math.trunc(sentenceNumber));
      if (!timelineSentences || timelineSentences.length === 0) return null;

      const resolvedRuntime = (() => {
        const match = timelineSentences.find((e) => e.sentenceNumber === targetSentence) ?? null;
        if (match) return match;
        const start = chunk?.startSentence ?? null;
        if (typeof start === 'number' && Number.isFinite(start)) {
          const candidateIndex = targetSentence - Math.max(1, Math.trunc(start));
          if (candidateIndex >= 0 && candidateIndex < timelineSentences.length) {
            return timelineSentences[candidateIndex] ?? null;
          }
        }
        return null;
      })();

      if (!resolvedRuntime) return null;

      const rawStartTime = resolvedRuntime.startTime;
      if (typeof rawStartTime !== 'number' || !Number.isFinite(rawStartTime)) {
        return { index: resolvedRuntime.index, time: null as number | null };
      }

      const epsilon = 0.02;
      const timelineStartTime = Math.max(0, rawStartTime - epsilon);

      const rawTotal = timelineSentences[timelineSentences.length - 1]?.endTime ?? null;
      const timelineTotal = typeof rawTotal === 'number' && Number.isFinite(rawTotal) && rawTotal > 0 ? rawTotal : null;

      let resolvedDuration = audioDuration;
      if (!(typeof resolvedDuration === 'number' && Number.isFinite(resolvedDuration) && resolvedDuration > 0)) {
        const normaliseUrl = (value: string) => value.split('?')[0].split('#')[0];
        const trackDurationForUrl = (url: string | null | undefined) => {
          if (!url || !audioTracks) return null;
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
          (typeof audioTracks?.orig?.duration === 'number' && Number.isFinite(audioTracks.orig.duration) && audioTracks.orig.duration > 0 ? audioTracks.orig.duration : null) ??
          (typeof audioTracks?.orig_trans?.duration === 'number' && Number.isFinite(audioTracks.orig_trans.duration) && audioTracks.orig_trans.duration > 0 ? audioTracks.orig_trans.duration : null) ??
          (typeof audioTracks?.translation?.duration === 'number' && Number.isFinite(audioTracks.translation.duration) && audioTracks.translation.duration > 0 ? audioTracks.translation.duration : null) ??
          (typeof audioTracks?.trans?.duration === 'number' && Number.isFinite(audioTracks.trans.duration) && audioTracks.trans.duration > 0 ? audioTracks.trans.duration : null) ??
          null;
      }

      const duration = typeof resolvedDuration === 'number' && Number.isFinite(resolvedDuration) && resolvedDuration > 0 ? resolvedDuration : null;

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
      if (!target) return false;
      setActiveSentenceIndex(target.index);
      if (target.time === null) return true;
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
      if (!jobId || !sentenceNumber) return;
      if (!syncPlayerToReelSentence(sentenceNumber) && onRequestSentenceJump) {
        onRequestSentenceJump(sentenceNumber);
      }
    },
    [jobId, onRequestSentenceJump, syncPlayerToReelSentence],
  );

  const handleReelFrameError = useCallback((sentenceNumber: number) => {
    setReelImageFailures((prev) => ({ ...prev, [String(sentenceNumber)]: true }));
  }, []);

  // Build the reel node
  const sentenceImageReelNode = useMemo(() => {
    if (!jobId || !isReelEnabled) return null;

    if (!reelReady) {
      return (
        <div
          className="player-panel__interactive-image-reel player-panel__interactive-image-reel--loading"
          aria-live="polite"
        >
          <div className="player-panel__interactive-image-reel-strip" role="list" aria-label="Loading sentence images">
            {Array.from({ length: REEL_WINDOW_SIZE }).map((_, index) => (
              <div
                key={`loading-${index}`}
                className="player-panel__interactive-image-reel-slot"
                role="listitem"
                aria-hidden="true"
              >
                <div className="player-panel__interactive-image-reel-frame player-panel__interactive-image-reel-frame--loading">
                  <span className="player-panel__interactive-image-reel-placeholder" aria-hidden="true">...</span>
                </div>
              </div>
            ))}
          </div>
          <div className="player-panel__interactive-image-reel-status" role="status">Loading reel...</div>
        </div>
      );
    }

    if (reelVisibleFrames.length === 0) return null;

    return (
      <SentenceImageReel
        scrollRef={reelScrollRef}
        frames={reelVisibleFrames}
        onFrameClick={handleReelFrameClick}
        onFrameError={handleReelFrameError}
      />
    );
  }, [handleReelFrameClick, handleReelFrameError, isReelEnabled, jobId, reelReady, reelVisibleFrames]);

  return {
    sentenceImageReelNode,
    activeSentenceImagePath,
    reelScale,
  };
}
