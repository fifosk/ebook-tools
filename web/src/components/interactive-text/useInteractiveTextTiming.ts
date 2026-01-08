import { useEffect, useMemo, useState } from 'react';
import type { ChunkSentenceMetadata, JobTimingResponse, TrackTimingPayload } from '../../api/dtos';
import { fetchJobTiming } from '../../api/client';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { buildWordIndex } from '../../lib/timing/wordSync';
import type { TimingPayload } from '../../types/timing';
import { WORD_SYNC } from '../player-panel/constants';
import type {
  WordSyncLane,
  WordSyncRenderableToken,
  WordSyncSentence,
} from './types';
import {
  buildTimingPayloadFromJobTiming,
  buildTimingPayloadFromWordIndex,
} from './utils';

type TimingDiagnostics = {
  policy: string | null;
  estimated: boolean;
  punctuation?: boolean;
};

type UseInteractiveTextTimingArgs = {
  jobId: string | null;
  chunk: LiveMediaChunk | null;
  isExportMode: boolean;
  resolvedTimingTrack: 'mix' | 'translation' | 'original';
  resolvedTranslationSpeed: number;
};

type UseInteractiveTextTimingResult = {
  timingPayload: TimingPayload | null;
  timingDiagnostics: TimingDiagnostics | null;
  effectivePlaybackRate: number;
  wordSyncAllowed: boolean;
  shouldUseWordSync: boolean;
  legacyWordSyncEnabled: boolean;
  wordSyncSentences: WordSyncSentence[] | null;
  activeWordSyncTrack: TrackTimingPayload | null;
  activeWordIndex: ReturnType<typeof buildWordIndex> | null;
  jobTimingResponse: JobTimingResponse | null;
  hasRemoteTiming: boolean;
};

export function useInteractiveTextTiming({
  jobId,
  chunk,
  isExportMode,
  resolvedTimingTrack,
  resolvedTranslationSpeed,
}: UseInteractiveTextTimingArgs): UseInteractiveTextTimingResult {
  const [jobTimingResponse, setJobTimingResponse] = useState<JobTimingResponse | null>(null);
  const [timingDiagnostics, setTimingDiagnostics] = useState<TimingDiagnostics | null>(null);

  const wordSyncQueryState = useMemo<boolean | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    try {
      const params = new URLSearchParams(window.location.search);
      const raw = params.get('wordsync');
      if (raw === null) {
        return null;
      }
      if (raw === '0' || raw.toLowerCase() === 'false') {
        return false;
      }
      return true;
    } catch {
      return null;
    }
  }, []);
  const wordSyncAllowed = (wordSyncQueryState ?? WORD_SYNC.FEATURE) === true;

  useEffect(() => {
    if (!jobId || !wordSyncAllowed || isExportMode) {
      setJobTimingResponse(null);
      setTimingDiagnostics(null);
      return;
    }
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    let cancelled = false;
    setJobTimingResponse(null);
    setTimingDiagnostics(null);
    (async () => {
      try {
        const response = await fetchJobTiming(jobId, controller?.signal);
        if (cancelled || controller?.signal.aborted) {
          return;
        }
        if (!response) {
          setJobTimingResponse(null);
          setTimingDiagnostics(null);
          return;
        }
        setJobTimingResponse(response);
      } catch (error) {
        if (controller?.signal.aborted || cancelled) {
          return;
        }
        if (import.meta.env.DEV) {
          console.debug('Failed to load job timing data', error);
        }
        setJobTimingResponse(null);
        setTimingDiagnostics(null);
      }
    })();
    return () => {
      cancelled = true;
      if (controller) {
        controller.abort();
      }
    };
  }, [isExportMode, jobId, wordSyncAllowed]);

  const chunkSentenceMap = useMemo(() => {
    const map = new Map<number, ChunkSentenceMetadata>();
    if (!chunk?.sentences || chunk.sentences.length === 0) {
      return map;
    }
    chunk.sentences.forEach((metadata, index) => {
      const rawId = metadata?.sentence_number;
      const sentenceId =
        typeof rawId === 'number' && Number.isFinite(rawId) ? rawId : index;
      map.set(sentenceId, metadata);
    });
    return map;
  }, [chunk?.sentences]);

  const wordSyncTracks = chunk?.timingTracks ?? null;
  const wordSyncTrackCandidates = useMemo(() => {
    if (!wordSyncTracks || wordSyncTracks.length === 0) {
      return [] as TrackTimingPayload[];
    }
    const chunkId = chunk?.chunkId ?? null;
    if (!chunkId) {
      return wordSyncTracks.filter((track): track is TrackTimingPayload => Boolean(track));
    }
    const matches = wordSyncTracks.filter(
      (track): track is TrackTimingPayload => Boolean(track && track.chunkId === chunkId),
    );
    return matches.length > 0
      ? matches
      : wordSyncTracks.filter((track): track is TrackTimingPayload => Boolean(track));
  }, [chunk?.chunkId, wordSyncTracks]);
  const wordSyncPreferredTypes = useMemo(() => {
    const preferences: TrackTimingPayload['trackType'][] = [];
    if (resolvedTimingTrack === 'original') {
      preferences.push('original');
    } else if (resolvedTimingTrack === 'mix') {
      preferences.push('original_translated');
    } else {
      preferences.push('translated');
    }
    (['translated', 'original_translated', 'original'] as TrackTimingPayload['trackType'][]).forEach(
      (candidate) => {
        if (!preferences.includes(candidate)) {
          preferences.push(candidate);
        }
      },
    );
    return preferences;
  }, [resolvedTimingTrack]);
  const selectedWordSyncTrack = useMemo(() => {
    if (wordSyncTrackCandidates.length === 0) {
      return null;
    }
    for (const type of wordSyncPreferredTypes) {
      const match = wordSyncTrackCandidates.find((track) => track.trackType === type);
      if (match) {
        return match;
      }
    }
    return wordSyncTrackCandidates[0] ?? null;
  }, [wordSyncPreferredTypes, wordSyncTrackCandidates]);
  const wordIndex = useMemo(() => {
    if (!selectedWordSyncTrack) {
      return null;
    }
    return buildWordIndex(selectedWordSyncTrack);
  }, [selectedWordSyncTrack]);

  const legacyWordSyncEnabled = false;
  const wordSyncSentences = useMemo<WordSyncSentence[] | null>(() => {
    if (!legacyWordSyncEnabled) {
      return null;
    }
    if (!wordIndex) {
      return null;
    }
    const sentences = new Map<
      number,
      { orig: WordSyncRenderableToken[]; trans: WordSyncRenderableToken[]; xlit: WordSyncRenderableToken[] }
    >();
    const ensureBuckets = (sentenceId: number) => {
      let bucket = sentences.get(sentenceId);
      if (!bucket) {
        bucket = { orig: [], trans: [], xlit: [] };
        sentences.set(sentenceId, bucket);
      }
      return bucket;
    };
    wordIndex.words.forEach((word) => {
      const bucket = ensureBuckets(word.sentenceId);
      const metadata = chunkSentenceMap.get(word.sentenceId);
      let displayText = typeof word.text === 'string' ? word.text : '';
      if (metadata) {
        const variantTokens =
          word.lang === 'orig'
            ? metadata.original?.tokens
            : word.lang === 'trans'
              ? metadata.translation?.tokens
              : metadata.transliteration?.tokens;
        if (Array.isArray(variantTokens)) {
          const token = variantTokens[word.tokenIdx];
          if (typeof token === 'string' && token.trim().length > 0) {
            displayText = token;
          }
        }
      }
      if (!displayText || !displayText.trim()) {
        displayText = word.text || '';
      }
      const renderable: WordSyncRenderableToken = {
        ...word,
        displayText,
      };
      bucket[word.lang].push(renderable);
    });
    const entries = Array.from(sentences.entries());
    if (entries.length === 0) {
      return [];
    }
    entries.sort((a, b) => a[0] - b[0]);
    return entries.map(([sentenceId, lanes]) => {
      (['orig', 'trans', 'xlit'] as WordSyncLane[]).forEach((lane) => {
        lanes[lane].sort((left, right) => {
          if (left.tokenIdx !== right.tokenIdx) {
            return left.tokenIdx - right.tokenIdx;
          }
          if (left.t0 !== right.t0) {
            return left.t0 - right.t0;
          }
          return left.id.localeCompare(right.id);
        });
      });
      return {
        id: `ws-sentence-${sentenceId}`,
        sentenceId,
        tokens: lanes,
      };
    });
  }, [chunkSentenceMap, legacyWordSyncEnabled, wordIndex]);

  const hasRemoteTiming = wordSyncAllowed && jobTimingResponse !== null;
  const hasLegacyWordSync = wordSyncAllowed && Boolean(selectedWordSyncTrack && wordIndex);
  const hasWordSyncData =
    hasRemoteTiming ||
    (hasLegacyWordSync &&
      (legacyWordSyncEnabled ? Boolean(wordSyncSentences && wordSyncSentences.length > 0) : true));
  const shouldUseWordSync = hasWordSyncData;
  const activeWordSyncTrack =
    !hasRemoteTiming && shouldUseWordSync && selectedWordSyncTrack ? selectedWordSyncTrack : null;
  const activeWordIndex =
    !hasRemoteTiming && shouldUseWordSync && wordIndex ? wordIndex : null;
  const remoteTrackPayload = useMemo<TimingPayload | null>(() => {
    if (!hasRemoteTiming || !jobTimingResponse) {
      return null;
    }
    return buildTimingPayloadFromJobTiming(jobTimingResponse, resolvedTimingTrack);
  }, [hasRemoteTiming, jobTimingResponse, resolvedTimingTrack]);

  const timingPayload = useMemo<TimingPayload | null>(() => {
    if (remoteTrackPayload) {
      return remoteTrackPayload;
    }
    if (!hasLegacyWordSync || !activeWordSyncTrack || !activeWordIndex) {
      return null;
    }
    return buildTimingPayloadFromWordIndex(activeWordSyncTrack, activeWordIndex);
  }, [activeWordIndex, activeWordSyncTrack, hasLegacyWordSync, remoteTrackPayload]);

  const timingPlaybackRate = useMemo(() => {
    const rate = timingPayload?.playbackRate;
    if (typeof rate === 'number' && Number.isFinite(rate) && rate > 0) {
      return rate;
    }
    return 1;
  }, [timingPayload]);
  const effectivePlaybackRate = useMemo(() => {
    const combined = timingPlaybackRate * resolvedTranslationSpeed;
    if (!Number.isFinite(combined) || combined <= 0) {
      return timingPlaybackRate;
    }
    return Math.round(combined * 1000) / 1000;
  }, [resolvedTranslationSpeed, timingPlaybackRate]);

  useEffect(() => {
    if (!timingPayload) {
      setTimingDiagnostics(null);
      return;
    }
    const policy =
      typeof jobTimingResponse?.highlighting_policy === 'string' &&
      jobTimingResponse.highlighting_policy.trim()
        ? jobTimingResponse.highlighting_policy.trim()
        : null;
    const policyLower = policy ? policy.toLowerCase() : null;
    const hasEstimatedSegments =
      jobTimingResponse?.has_estimated_segments === true || policyLower === 'estimated';
    setTimingDiagnostics({
      policy,
      estimated: hasEstimatedSegments,
      punctuation: policyLower === 'estimated_punct',
    });
  }, [jobTimingResponse, timingPayload]);

  return {
    timingPayload,
    timingDiagnostics,
    effectivePlaybackRate,
    wordSyncAllowed,
    shouldUseWordSync,
    legacyWordSyncEnabled,
    wordSyncSentences,
    activeWordSyncTrack,
    activeWordIndex,
    jobTimingResponse,
    hasRemoteTiming,
  };
}
