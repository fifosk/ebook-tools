/**
 * Sentence gate and duration extraction.
 *
 * Reads gate boundaries and phase durations from v3 camelCase-only
 * chunk sentence metadata.
 * Previously inlined in useInteractiveAudioSequence.
 */

import type { ChunkSentenceMetadata } from '../../api/dtos';

export type SequenceTrack = 'original' | 'translation';
export type SelectedAudioTrack = SequenceTrack | 'combined';

// ---------------------------------------------------------------------------
// Numeric value helpers
// ---------------------------------------------------------------------------

export function resolveNumericValue(value: unknown): number | null {
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
}

export function resolveDurationValue(value: unknown): number | null {
  const parsed = resolveNumericValue(value);
  if (parsed === null || !Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

// ---------------------------------------------------------------------------
// Gate reading
// ---------------------------------------------------------------------------

/**
 * Read a numeric gate value from sentence metadata by key name.
 */
export function readSentenceGate(
  sentence: ChunkSentenceMetadata | null | undefined,
  keys: string[],
): number | null {
  if (!sentence) {
    return null;
  }
  const record = sentence as unknown as Record<string, unknown>;
  for (const key of keys) {
    const numeric = resolveNumericValue(record[key]);
    if (numeric !== null) {
      return numeric;
    }
  }
  return null;
}

/**
 * Read a phase duration from `sentence.phaseDurations`.
 */
export function readPhaseDuration(
  sentence: ChunkSentenceMetadata | null | undefined,
  key: string,
): number | null {
  if (!sentence) {
    return null;
  }
  const phasePayload = sentence.phaseDurations;
  if (!phasePayload || typeof phasePayload !== 'object') {
    return null;
  }
  return resolveDurationValue(phasePayload[key]);
}

/**
 * Resolve the start/end gate pair for a sentence on a given track.
 */
export function resolveSentenceGate(
  sentence: ChunkSentenceMetadata | null | undefined,
  track: SequenceTrack,
): { start: number; end: number } | null {
  const start =
    track === 'original'
      ? readSentenceGate(sentence, ['originalStartGate'])
      : readSentenceGate(sentence, ['startGate']);
  const end =
    track === 'original'
      ? readSentenceGate(sentence, ['originalEndGate'])
      : readSentenceGate(sentence, ['endGate']);
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
}

/**
 * Resolve a sentence's duration for a given track.
 *
 * Tries gates first, then `phaseDurations`, then `totalDuration`.
 */
export function resolveSentenceDuration(
  sentence: ChunkSentenceMetadata | null | undefined,
  track: SelectedAudioTrack,
): number | null {
  if (!sentence) {
    return null;
  }
  if (track === 'combined') {
    return resolveDurationValue(sentence.totalDuration);
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
    return resolveDurationValue(sentence.totalDuration);
  }
  return null;
}
