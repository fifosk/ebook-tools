/**
 * Pure functions for sequence playback plan building, segment lookup, and seek resolution.
 *
 * Extracted from useInteractiveAudioSequence and useSequencePlaybackController
 * to enable comprehensive testing without React hook coupling.
 */

import type { ChunkSentenceMetadata, AudioTrackMetadata } from '../../api/dtos';

// ─── Types ────────────────────────────────────────────────────────────

export type SequenceTrack = 'original' | 'translation';

export type SequenceSegment = {
  track: SequenceTrack;
  start: number;
  end: number;
  sentenceIndex: number;
};

export type TextPlayerVariantKind = 'original' | 'translation' | 'translit';

export type TokenSeekTarget = {
  segmentIndex: number;
  track: SequenceTrack;
  seekTime: number;
  requiresTrackSwitch: boolean;
};

export type ChunkMeta = {
  sentenceCount?: number | null;
  startSentence?: number | null;
  endSentence?: number | null;
};

export type AudioTrackMap = Record<string, AudioTrackMetadata | null | undefined>;

// ─── Numeric helpers ──────────────────────────────────────────────────

function resolveNumeric(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

// ─── Gate reading (inline to avoid circular import) ───────────────────

function readGate(sentence: ChunkSentenceMetadata, keys: string[]): number | null {
  const record = sentence as unknown as Record<string, unknown>;
  for (const key of keys) {
    const numeric = resolveNumeric(record[key]);
    if (numeric !== null) return numeric;
  }
  return null;
}

function readSentenceGate(
  sentence: ChunkSentenceMetadata,
  track: SequenceTrack,
): { start: number; end: number } | null {
  const start =
    track === 'original'
      ? readGate(sentence, ['originalStartGate'])
      : readGate(sentence, ['startGate']);
  const end =
    track === 'original'
      ? readGate(sentence, ['originalEndGate'])
      : readGate(sentence, ['endGate']);
  if (start === null || end === null) return null;
  const safeStart = Math.max(0, start);
  const safeEnd = Math.max(safeStart, end);
  if (!Number.isFinite(safeStart) || !Number.isFinite(safeEnd)) return null;
  if (safeEnd <= safeStart) return null;
  return { start: safeStart, end: safeEnd };
}

// ─── Plan building ────────────────────────────────────────────────────

/**
 * Build a sequence playback plan from sentence metadata and audio track info.
 *
 * The plan is an ordered list of segments: each maps a sentence to a time range
 * on either the original or translation audio track. In sequence mode, playback
 * alternates between these segments.
 */
export function buildSequencePlan(
  sentences: ChunkSentenceMetadata[] | null | undefined,
  audioTracks: AudioTrackMap | null | undefined,
  chunkMeta: ChunkMeta,
): SequenceSegment[] {
  const isSingleSentence =
    (typeof chunkMeta.sentenceCount === 'number' && chunkMeta.sentenceCount === 1) ||
    (typeof chunkMeta.startSentence === 'number' &&
      typeof chunkMeta.endSentence === 'number' &&
      chunkMeta.startSentence === chunkMeta.endSentence);

  const buildFallbackSegments = (
    includeOriginal: boolean,
    includeTranslation: boolean,
  ): SequenceSegment[] => {
    const fallback: SequenceSegment[] = [];
    const originalDuration = audioTracks?.orig?.duration ?? null;
    const translationDuration =
      audioTracks?.translation?.duration ?? audioTracks?.trans?.duration ?? null;
    if (
      includeOriginal &&
      typeof originalDuration === 'number' &&
      Number.isFinite(originalDuration) &&
      originalDuration > 0
    ) {
      fallback.push({ track: 'original', start: 0, end: originalDuration, sentenceIndex: 0 });
    }
    if (
      includeTranslation &&
      typeof translationDuration === 'number' &&
      Number.isFinite(translationDuration) &&
      translationDuration > 0
    ) {
      fallback.push({ track: 'translation', start: 0, end: translationDuration, sentenceIndex: 0 });
    }
    return fallback;
  };

  if (!sentences || sentences.length === 0) {
    return isSingleSentence ? buildFallbackSegments(true, true) : [];
  }

  const segments: SequenceSegment[] = [];
  let hasOriginalGate = false;
  let hasTranslationGate = false;

  sentences.forEach((sentence, index) => {
    const originalGate = readSentenceGate(sentence, 'original');
    if (originalGate) {
      hasOriginalGate = true;
      segments.push({ track: 'original', ...originalGate, sentenceIndex: index });
    }
    const translationGate = readSentenceGate(sentence, 'translation');
    if (translationGate) {
      hasTranslationGate = true;
      segments.push({ track: 'translation', ...translationGate, sentenceIndex: index });
    }
  });

  // Derive gates from phaseDurations when gate data is absent
  if (!hasOriginalGate || !hasTranslationGate) {
    const canDerive = sentences.some((s) => s.phaseDurations);
    if (canDerive) {
      let origCursor = 0;
      let transCursor = 0;
      sentences.forEach((sentence, index) => {
        const phases = sentence.phaseDurations as Record<string, unknown> | undefined;
        const origDur = resolveNumeric(phases?.original) ?? 0;
        const transDur =
          resolveNumeric(phases?.translation) ?? resolveNumeric(sentence.totalDuration) ?? 0;
        if (!hasOriginalGate && origDur > 0) {
          segments.push({
            track: 'original',
            start: origCursor,
            end: origCursor + origDur,
            sentenceIndex: index,
          });
        }
        if (!hasTranslationGate && transDur > 0) {
          segments.push({
            track: 'translation',
            start: transCursor,
            end: transCursor + transDur,
            sentenceIndex: index,
          });
        }
        origCursor += origDur;
        transCursor += transDur;
      });
      hasOriginalGate = segments.some((s) => s.track === 'original');
      hasTranslationGate = segments.some((s) => s.track === 'translation');
    }
  }

  if (!isSingleSentence) {
    return segments;
  }

  // Single-sentence fallback: fill missing track from audio durations
  if (!hasOriginalGate || !hasTranslationGate) {
    const fallback = buildFallbackSegments(!hasOriginalGate, !hasTranslationGate);
    if (fallback.length > 0) {
      if (!hasOriginalGate && fallback.some((s) => s.track === 'original')) {
        segments.unshift(...fallback.filter((s) => s.track === 'original'));
      }
      if (!hasTranslationGate && fallback.some((s) => s.track === 'translation')) {
        segments.push(...fallback.filter((s) => s.track === 'translation'));
      }
    }
  }

  return segments;
}

// ─── Segment lookup ───────────────────────────────────────────────────

/**
 * Find the segment index for a given sentence, optionally preferring a specific track.
 * Returns -1 if not found.
 */
export function findSegmentForSentence(
  plan: SequenceSegment[],
  sentenceIndex: number,
  preferredTrack?: SequenceTrack | null,
): number {
  if (!plan.length || sentenceIndex < 0) return -1;
  if (preferredTrack) {
    const matched = plan.findIndex(
      (s) => s.sentenceIndex === sentenceIndex && s.track === preferredTrack,
    );
    if (matched >= 0) return matched;
  }
  return plan.findIndex((s) => s.sentenceIndex === sentenceIndex);
}

/**
 * Find the segment index containing the given media time on the specified track.
 * Returns -1 if no segment matches.
 */
export function findSegmentForTime(
  plan: SequenceSegment[],
  mediaTime: number,
  currentTrack: SequenceTrack,
  tolerance: number = 0.05,
): number {
  if (!plan.length || !Number.isFinite(mediaTime)) return -1;

  // Exact match within tolerance
  const exact = plan.findIndex(
    (s) =>
      s.track === currentTrack &&
      mediaTime >= s.start - tolerance &&
      mediaTime <= s.end + tolerance,
  );
  if (exact >= 0) return exact;

  // Fallback: find the next upcoming segment on this track
  const upcoming = plan.findIndex(
    (s) => s.track === currentTrack && mediaTime < s.start,
  );
  if (upcoming >= 0) return upcoming;

  // Last resort: last segment on this track
  for (let i = plan.length - 1; i >= 0; i--) {
    if (plan[i].track === currentTrack) return i;
  }
  return -1;
}

/**
 * Determine whether the current segment should advance based on playback time.
 */
export function shouldAdvanceSegment(
  plan: SequenceSegment[],
  currentIndex: number,
  mediaTime: number,
  tolerance: number = 0.03,
): boolean {
  if (currentIndex < 0 || currentIndex >= plan.length) return false;
  const segment = plan[currentIndex];
  if (!segment) return false;
  return mediaTime >= segment.end - tolerance;
}

// ─── Token seek resolution ────────────────────────────────────────────

/**
 * Resolve where to seek when a user taps/clicks a word token.
 *
 * Maps the variant kind (original/translation/transliteration) to the
 * appropriate audio track and finds the correct segment in the plan.
 *
 * Transliteration tokens are mapped to the translation track since
 * transliteration follows translation timing.
 */
export function resolveTokenSeekTarget(
  plan: SequenceSegment[],
  sentenceIndex: number,
  variantKind: TextPlayerVariantKind,
  tokenTime: number,
  currentTrack: SequenceTrack | null,
): TokenSeekTarget | null {
  if (!plan.length || sentenceIndex < 0 || !Number.isFinite(tokenTime)) return null;

  // Map variant kind to audio track
  // Transliteration maps to translation (same timing source)
  const targetTrack: SequenceTrack =
    variantKind === 'original' ? 'original' : 'translation';

  const targetIndex = findSegmentForSentence(plan, sentenceIndex, targetTrack);
  if (targetIndex < 0) return null;

  const segment = plan[targetIndex];
  if (!segment) return null;

  return {
    segmentIndex: targetIndex,
    track: targetTrack,
    seekTime: tokenTime,
    requiresTrackSwitch: currentTrack === null || currentTrack !== targetTrack,
  };
}
