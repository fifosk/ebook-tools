import { useEffect, useMemo, useRef, useState } from 'react';
import type { AudioTrackMetadata, ChunkSentenceMetadata } from '../../api/dtos';
import { appendAccessToken } from '../../api/client';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { coerceExportPath } from '../../utils/storageResolver';

export type SequenceTrack = 'original' | 'translation';
export type SequenceSegment = {
  track: SequenceTrack;
  start: number;
  end: number;
  sentenceIndex: number;
};
export type SelectedAudioTrack = SequenceTrack | 'combined';

type SequenceState = {
  enabled: boolean;
  plan: SequenceSegment[];
  track: SequenceTrack | null;
  setTrack: (track: SequenceTrack | null) => void;
  defaultTrack: SequenceTrack;
  trackRef: React.MutableRefObject<SequenceTrack | null>;
  indexRef: React.MutableRefObject<number>;
  pendingSeekRef: React.MutableRefObject<{ time: number; autoPlay: boolean } | null>;
  autoPlayRef: React.MutableRefObject<boolean>;
  pendingChunkAutoPlayRef: React.MutableRefObject<boolean>;
  pendingChunkAutoPlayKeyRef: React.MutableRefObject<string | null>;
  lastSequenceEndedRef: React.MutableRefObject<number | null>;
};

type UseInteractiveAudioSequenceArgs = {
  chunk: LiveMediaChunk | null;
  audioTracks: Record<string, AudioTrackMetadata> | null;
  activeAudioUrl: string | null;
  originalAudioEnabled: boolean;
  translationAudioEnabled: boolean;
  activeTimingTrack: 'mix' | 'translation' | 'original';
  isExportMode: boolean;
  jobId: string | null;
};

type UseInteractiveAudioSequenceResult = {
  sequence: SequenceState;
  effectiveAudioUrl: string | null;
  resolvedAudioUrl: string | null;
  audioResetKey: string;
  originalTrackUrl: string | null;
  translationTrackUrl: string | null;
  combinedTrackUrl: string | null;
  allowCombinedAudio: boolean;
  trackRefs: {
    originalTrackRef: string | null;
    translationTrackRef: string | null;
    combinedTrackRef: string | null;
    effectiveAudioRef: string | null;
  };
  resolvedTimingTrack: 'mix' | 'translation' | 'original';
  useCombinedPhases: boolean;
};

const normaliseAudioUrl = (value: string | null): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const stripped = trimmed.replace(/[?#].*$/, '');
  if (!stripped) {
    return null;
  }
  try {
    const base = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
    const parsed = new URL(stripped, base);
    return parsed.pathname || stripped;
  } catch {
    return stripped;
  }
};

const resolveNumericValue = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
};

const resolveDurationValue = (value: unknown): number | null => {
  const parsed = resolveNumericValue(value);
  if (parsed === null) {
    return null;
  }
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
};

const readSentenceGate = (
  sentence: ChunkSentenceMetadata | null | undefined,
  keys: string[],
): number | null => {
  if (!sentence) {
    return null;
  }
  const record = sentence as unknown as Record<string, unknown>;
  for (const key of keys) {
    const raw = record[key];
    const numeric = resolveNumericValue(raw);
    if (numeric !== null) {
      return numeric;
    }
  }
  return null;
};

const readPhaseDuration = (
  sentence: ChunkSentenceMetadata | null | undefined,
  key: string,
): number | null => {
  if (!sentence) {
    return null;
  }
  const record = sentence as unknown as Record<string, unknown>;
  const phasePayload = record.phase_durations ?? record.phaseDurations;
  if (!phasePayload || typeof phasePayload !== 'object') {
    return null;
  }
  const phases = phasePayload as Record<string, unknown>;
  return resolveDurationValue(phases[key]);
};

const resolveSentenceGate = (
  sentence: ChunkSentenceMetadata | null | undefined,
  track: SequenceTrack,
): { start: number; end: number } | null => {
  const start =
    track === 'original'
      ? readSentenceGate(sentence, ['original_start_gate', 'originalStartGate', 'original_startGate'])
      : readSentenceGate(sentence, ['start_gate', 'startGate']);
  const end =
    track === 'original'
      ? readSentenceGate(sentence, ['original_end_gate', 'originalEndGate', 'original_endGate'])
      : readSentenceGate(sentence, ['end_gate', 'endGate']);
  if (start === null || end === null) {
    return null;
  }
  const safeStart = Math.max(0, start);
  const safeEnd = Math.max(safeStart, end);
  if (!Number.isFinite(safeStart) || !Number.isFinite(safeEnd)) {
    return null;
  }
  if (safeEnd <= safeStart) {
    return null;
  }
  return { start: safeStart, end: safeEnd };
};

const resolveSentenceDuration = (
  sentence: ChunkSentenceMetadata | null | undefined,
  track: SelectedAudioTrack,
): number | null => {
  if (!sentence) {
    return null;
  }
  if (track === 'combined') {
    const record = sentence as unknown as Record<string, unknown>;
    return resolveDurationValue(record.total_duration ?? record.totalDuration ?? record.t1);
  }
  const gate = resolveSentenceGate(sentence, track);
  if (gate) {
    return Math.max(gate.end - gate.start, 0);
  }
  const phaseKey = track === 'original' ? 'original' : 'translation';
  const phaseDuration = readPhaseDuration(sentence, phaseKey);
  if (phaseDuration !== null) {
    return phaseDuration;
  }
  if (track === 'translation') {
    const record = sentence as unknown as Record<string, unknown>;
    return resolveDurationValue(record.total_duration ?? record.totalDuration ?? record.t1);
  }
  return null;
};

export function useInteractiveAudioSequence({
  chunk,
  audioTracks,
  activeAudioUrl,
  originalAudioEnabled,
  translationAudioEnabled,
  activeTimingTrack,
  isExportMode,
  jobId,
}: UseInteractiveAudioSequenceArgs): UseInteractiveAudioSequenceResult {
  const combinedTrackUrl = audioTracks?.orig_trans?.url ?? audioTracks?.orig_trans?.path ?? null;
  const originalTrackUrl = audioTracks?.orig?.url ?? audioTracks?.orig?.path ?? null;
  const translationTrackUrl =
    audioTracks?.translation?.url ??
    audioTracks?.translation?.path ??
    audioTracks?.trans?.url ??
    audioTracks?.trans?.path ??
    null;
  const allowCombinedAudio = Boolean(combinedTrackUrl) && (!originalTrackUrl || !translationTrackUrl);

  const sequencePlan = useMemo<SequenceSegment[]>(() => {
    if (!chunk) {
      return [];
    }
    const isSingleSentence =
      (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount === 1) ||
      (typeof chunk.startSentence === 'number' &&
        typeof chunk.endSentence === 'number' &&
        chunk.startSentence === chunk.endSentence);
    const buildFallbackSegments = (includeOriginal: boolean, includeTranslation: boolean): SequenceSegment[] => {
      const fallback: SequenceSegment[] = [];
      const originalDuration = audioTracks?.orig?.duration ?? null;
      const translationDuration = audioTracks?.translation?.duration ?? audioTracks?.trans?.duration ?? null;
      if (
        includeOriginal &&
        typeof originalDuration === 'number' &&
        Number.isFinite(originalDuration) &&
        originalDuration > 0
      ) {
        fallback.push({
          track: 'original',
          start: 0,
          end: originalDuration,
          sentenceIndex: 0,
        });
      }
      if (
        includeTranslation &&
        typeof translationDuration === 'number' &&
        Number.isFinite(translationDuration) &&
        translationDuration > 0
      ) {
        fallback.push({
          track: 'translation',
          start: 0,
          end: translationDuration,
          sentenceIndex: 0,
        });
      }
      return fallback;
    };

    if (!chunk.sentences || chunk.sentences.length === 0) {
      return isSingleSentence ? buildFallbackSegments(true, true) : [];
    }

    const segments: SequenceSegment[] = [];
    let hasOriginalGate = false;
    let hasTranslationGate = false;
    chunk.sentences.forEach((sentence, index) => {
      const originalGate = resolveSentenceGate(sentence, 'original');
      if (originalGate) {
        hasOriginalGate = true;
        segments.push({
          track: 'original',
          start: originalGate.start,
          end: originalGate.end,
          sentenceIndex: index,
        });
      }
      const translationGate = resolveSentenceGate(sentence, 'translation');
      if (translationGate) {
        hasTranslationGate = true;
        segments.push({
          track: 'translation',
          start: translationGate.start,
          end: translationGate.end,
          sentenceIndex: index,
        });
      }
    });

    if (!isSingleSentence) {
      return segments;
    }

    if (!hasOriginalGate || !hasTranslationGate) {
      const fallback = buildFallbackSegments(!hasOriginalGate, !hasTranslationGate);
      if (fallback.length === 0) {
        return segments;
      }
      if (!hasOriginalGate && fallback.some((segment) => segment.track === 'original')) {
        segments.unshift(...fallback.filter((segment) => segment.track === 'original'));
      }
      if (!hasTranslationGate && fallback.some((segment) => segment.track === 'translation')) {
        segments.push(...fallback.filter((segment) => segment.track === 'translation'));
      }
    }

    return segments;
  }, [audioTracks, chunk]);

  const hasOriginalSegments = useMemo(
    () => sequencePlan.some((segment) => segment.track === 'original'),
    [sequencePlan],
  );
  const hasTranslationSegments = useMemo(
    () => sequencePlan.some((segment) => segment.track === 'translation'),
    [sequencePlan],
  );
  const sequenceDefaultTrack: SequenceTrack = hasOriginalSegments ? 'original' : 'translation';
  const sequenceEnabled = Boolean(
    originalAudioEnabled &&
      translationAudioEnabled &&
      originalTrackUrl &&
      translationTrackUrl &&
      hasOriginalSegments &&
      hasTranslationSegments,
  );
  const [sequenceTrack, setSequenceTrack] = useState<SequenceTrack | null>(sequenceDefaultTrack);
  const sequenceTrackRef = useRef<SequenceTrack | null>(sequenceTrack);
  const sequenceIndexRef = useRef(0);
  const pendingSequenceSeekRef = useRef<{ time: number; autoPlay: boolean } | null>(null);
  const sequenceAutoPlayRef = useRef(false);
  const pendingChunkAutoPlayRef = useRef(false);
  const pendingChunkAutoPlayKeyRef = useRef<string | null>(null);
  const lastSequenceEndedRef = useRef<number | null>(null);

  useEffect(() => {
    sequenceTrackRef.current = sequenceTrack;
  }, [sequenceTrack]);

  const sequenceChunkKey = useMemo(() => {
    return chunk?.chunkId ?? chunk?.rangeFragment ?? chunk?.metadataPath ?? chunk?.metadataUrl ?? null;
  }, [chunk?.chunkId, chunk?.metadataPath, chunk?.metadataUrl, chunk?.rangeFragment]);
  const sequenceChunkKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const previous = sequenceChunkKeyRef.current;
    sequenceChunkKeyRef.current = sequenceChunkKey;
    if (!sequenceEnabled || !sequenceChunkKey || previous === sequenceChunkKey) {
      return;
    }
    sequenceIndexRef.current = 0;
    pendingSequenceSeekRef.current = null;
    sequenceTrackRef.current = sequenceDefaultTrack;
    setSequenceTrack(sequenceDefaultTrack);
  }, [sequenceChunkKey, sequenceDefaultTrack, sequenceEnabled]);

  const effectiveAudioUrl = useMemo(() => {
    if (sequenceEnabled) {
      const track = sequenceTrack ?? sequenceDefaultTrack;
      return track === 'original' ? originalTrackUrl : translationTrackUrl;
    }
    if (activeAudioUrl) {
      return activeAudioUrl;
    }
    if (originalAudioEnabled && originalTrackUrl) {
      return originalTrackUrl;
    }
    if (originalAudioEnabled && allowCombinedAudio && combinedTrackUrl) {
      return combinedTrackUrl;
    }
    if (translationAudioEnabled && translationTrackUrl) {
      return translationTrackUrl;
    }
    if (translationAudioEnabled && allowCombinedAudio && combinedTrackUrl) {
      return combinedTrackUrl;
    }
    if (translationTrackUrl) {
      return translationTrackUrl;
    }
    if (allowCombinedAudio && combinedTrackUrl) {
      return combinedTrackUrl;
    }
    return null;
  }, [
    activeAudioUrl,
    allowCombinedAudio,
    combinedTrackUrl,
    originalAudioEnabled,
    originalTrackUrl,
    sequenceDefaultTrack,
    sequenceEnabled,
    sequenceTrack,
    translationAudioEnabled,
    translationTrackUrl,
  ]);

  const resolvedAudioUrl = useMemo(() => {
    if (!effectiveAudioUrl) {
      return null;
    }
    if (isExportMode) {
      return coerceExportPath(effectiveAudioUrl, jobId) ?? effectiveAudioUrl;
    }
    return appendAccessToken(effectiveAudioUrl);
  }, [effectiveAudioUrl, isExportMode, jobId]);

  const audioResetKey = useMemo(() => {
    if (sequenceEnabled) {
      const chunkKey =
        chunk?.chunkId ??
        chunk?.rangeFragment ??
        chunk?.metadataPath ??
        chunk?.metadataUrl ??
        'unknown';
      return `sequence:${chunkKey}:${originalTrackUrl ?? ''}:${translationTrackUrl ?? ''}`;
    }
    return effectiveAudioUrl ?? 'none';
  }, [
    chunk?.chunkId,
    chunk?.metadataPath,
    chunk?.metadataUrl,
    chunk?.rangeFragment,
    effectiveAudioUrl,
    originalTrackUrl,
    sequenceEnabled,
    translationTrackUrl,
  ]);

  const trackRefs = useMemo(() => {
    return {
      originalTrackRef: normaliseAudioUrl(originalTrackUrl),
      translationTrackRef: normaliseAudioUrl(translationTrackUrl),
      combinedTrackRef: normaliseAudioUrl(combinedTrackUrl),
      effectiveAudioRef: normaliseAudioUrl(effectiveAudioUrl),
    };
  }, [combinedTrackUrl, effectiveAudioUrl, originalTrackUrl, translationTrackUrl]);

  const resolvedTimingTrack: 'mix' | 'translation' | 'original' = sequenceEnabled
    ? sequenceTrack ?? sequenceDefaultTrack
    : activeTimingTrack;
  const hasCombinedAudio = Boolean(combinedTrackUrl);
  const useCombinedPhases = resolvedTimingTrack === 'mix' && hasCombinedAudio;

  return {
    sequence: {
      enabled: sequenceEnabled,
      plan: sequencePlan,
      track: sequenceTrack,
      setTrack: setSequenceTrack,
      defaultTrack: sequenceDefaultTrack,
      trackRef: sequenceTrackRef,
      indexRef: sequenceIndexRef,
      pendingSeekRef: pendingSequenceSeekRef,
      autoPlayRef: sequenceAutoPlayRef,
      pendingChunkAutoPlayRef,
      pendingChunkAutoPlayKeyRef,
      lastSequenceEndedRef,
    },
    effectiveAudioUrl,
    resolvedAudioUrl,
    audioResetKey,
    originalTrackUrl,
    translationTrackUrl,
    combinedTrackUrl,
    allowCombinedAudio,
    trackRefs,
    resolvedTimingTrack,
    useCombinedPhases,
  };
}

export function resolveTrackDuration(target: LiveMediaChunk | null | undefined, track: SelectedAudioTrack): number | null {
  if (!target) {
    return null;
  }
  const extractDuration = (metadata: AudioTrackMetadata | null | undefined): number | null => {
    if (!metadata) {
      return null;
    }
    const duration = metadata.duration;
    if (typeof duration === 'number' && Number.isFinite(duration) && duration > 0) {
      return duration;
    }
    return null;
  };
  const tracks = target.audioTracks ?? null;
  if (tracks) {
    if (track === 'original') {
      const value = extractDuration(tracks.orig ?? tracks.original ?? null);
      if (value !== null) {
        return value;
      }
    } else if (track === 'translation') {
      const value = extractDuration(tracks.translation ?? tracks.trans ?? null);
      if (value !== null) {
        return value;
      }
    } else {
      const value = extractDuration(tracks.orig_trans ?? tracks.combined ?? tracks.mix ?? null);
      if (value !== null) {
        return value;
      }
    }
  }
  if (Array.isArray(target.sentences) && target.sentences.length > 0) {
    let total = 0;
    let hasDuration = false;
    target.sentences.forEach((sentence) => {
      const duration = resolveSentenceDuration(sentence, track);
      if (duration !== null) {
        total += duration;
        hasDuration = true;
      }
    });
    if (hasDuration && total > 0) {
      return total;
    }
  }
  return null;
}
