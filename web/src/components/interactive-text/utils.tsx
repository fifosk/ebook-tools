import type { ReactNode } from 'react';
import type { JobTimingEntry, JobTimingResponse, TrackTimingPayload } from '../../api/dtos';
import { LANGUAGE_CODES } from '../../constants/languageCodes';
import type { WordIndex } from '../../lib/timing/wordSync';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import type { Segment, TimingPayload, TrackKind, WordToken } from '../../types/timing';
import { groupBy } from '../../utils/groupBy';
import { normalizeLanguageLabel, sortLanguageLabelsByName } from '../../utils/languages';
import type { ParagraphFragment, SentenceFragment, SentenceGate } from './types';
import {
  sanitizeLookupQuery as _sanitizeLookupQuery,
  tokenizeSentenceText as _tokenizeSentenceText,
  loadStored,
  storeValue,
  loadStoredBool,
} from '../../lib/linguist';

export function containsNonLatinLetters(text: string): boolean {
  const value = text.trim();
  if (!value) {
    return false;
  }

  try {
    const letterRegex = new RegExp('\\\\p{Letter}', 'u');
    const latinRegex = new RegExp('\\\\p{Script=Latin}', 'u');
    for (const char of value) {
      if (letterRegex.test(char) && !latinRegex.test(char)) {
        return true;
      }
    }
    return false;
  } catch {
    return /[\u0370-\u03FF\u0400-\u052F\u0590-\u05FF\u0600-\u06FF\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0E00-\u0E7F\u0E80-\u0EFF\u0F00-\u0FFF\u1000-\u109F\u1100-\u11FF\u1200-\u137F\u13A0-\u13FF\u1400-\u167F\u1680-\u169F\u16A0-\u16FF\u1700-\u171F\u1720-\u173F\u1740-\u175F\u1760-\u177F\u1780-\u17FF\u1800-\u18AF\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF]/.test(
      value,
    );
  }
}

export function toTrackKind(track: TrackTimingPayload): TrackKind {
  if (track.trackType === 'original_translated') {
    return 'original_translation_combined';
  }
  if (track.trackType === 'original') {
    return 'original_only';
  }
  return 'translation_only';
}

export function renderWithNonLatinBoost(text: string, boostedClassName: string): ReactNode {
  const value = text ?? '';
  if (!value) {
    return value;
  }

  const parts = value.split(/(\s+)/);
  if (parts.length <= 1) {
    return containsNonLatinLetters(value) ? <span className={boostedClassName}>{value}</span> : value;
  }

  return parts.map((part, index) =>
    containsNonLatinLetters(part) ? (
      <span key={`${boostedClassName}-${index}`} className={boostedClassName}>
        {part}
      </span>
    ) : (
      part
    ),
  );
}

export function extractPlaybackRate(track: TrackTimingPayload): number | undefined {
  const raw = Number(track.tempoFactor);
  if (!Number.isFinite(raw) || raw <= 0) {
    return undefined;
  }
  return Math.round(raw * 1000) / 1000;
}

export function buildTimingPayloadFromWordIndex(
  track: TrackTimingPayload,
  index: WordIndex,
): TimingPayload {
  const segmentsById = new Map<
    number,
    {
      id: string;
      tokens: WordToken[];
      t0: number;
      t1: number;
    }
  >();

  index.words.forEach((word) => {
    if (word.lang !== 'orig' && word.lang !== 'trans') {
      return;
    }
    const lane: WordToken['lane'] = word.lang === 'orig' ? 'orig' : 'tran';
    const segmentId = word.sentenceId;
    const segmentKey = Number.isFinite(segmentId) ? Math.trunc(segmentId) : 0;
    const segId = String(segmentKey);
    const token: WordToken = {
      id: word.id,
      text: word.text,
      t0: word.t0,
      t1: word.t1,
      lane,
      segId,
    };
    const entry = segmentsById.get(segmentKey);
    if (entry) {
      entry.tokens.push(token);
      if (token.t0 < entry.t0) {
        entry.t0 = token.t0;
      }
      if (token.t1 > entry.t1) {
        entry.t1 = token.t1;
      }
    } else {
      segmentsById.set(segmentKey, {
        id: segId,
        tokens: [token],
        t0: token.t0,
        t1: token.t1,
      });
    }
  });

  if (segmentsById.size === 0) {
    return {
      trackKind: toTrackKind(track),
      playbackRate: extractPlaybackRate(track),
      segments: [],
    };
  }

  const segments: Segment[] = Array.from(segmentsById.values()).map((segment) => {
    segment.tokens.sort((left, right) => {
      if (left.t0 !== right.t0) {
        return left.t0 - right.t0;
      }
      if (left.t1 !== right.t1) {
        return left.t1 - right.t1;
      }
      if (left.lane !== right.lane) {
        return left.lane.localeCompare(right.lane);
      }
      return left.id.localeCompare(right.id);
    });
    return {
      id: segment.id,
      t0: segment.t0,
      t1: segment.t1,
      tokens: segment.tokens,
    };
  });

  segments.sort((left, right) => {
    if (left.t0 !== right.t0) {
      return left.t0 - right.t0;
    }
    if (left.t1 !== right.t1) {
      return left.t1 - right.t1;
    }
    return left.id.localeCompare(right.id);
  });

  return {
    trackKind: toTrackKind(track),
    playbackRate: extractPlaybackRate(track),
    segments,
  };
}

export function normalizeNumber(value: unknown): number | undefined {
  if (value === null || value === undefined) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function normaliseTextPlayerVariant(value: unknown): TextPlayerVariantKind | null {
  if (typeof value !== 'string') {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (normalized === 'original' || normalized === 'translit' || normalized === 'translation') {
    return normalized;
  }
  return null;
}

// Linguist utilities — delegate to canonical lib/linguist implementations.
// These re-exports maintain backward compatibility for existing callers.
export const sanitizeLookupQuery = _sanitizeLookupQuery;
export const tokenizeSentenceText = _tokenizeSentenceText;
export const loadMyLinguistStored = loadStored;
export const storeMyLinguistStored = storeValue;
export const loadMyLinguistStoredBool = loadStoredBool;

export function buildMyLinguistLanguageOptions(
  preferredLanguages: Array<string | null | undefined>,
  fallback?: string,
): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  const append = (value?: string | null) => {
    const normalized = normalizeLanguageLabel(value);
    if (!normalized) {
      return;
    }
    const key = normalized.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    result.push(normalized);
  };

  preferredLanguages.forEach(append);
  sortLanguageLabelsByName(Object.keys(LANGUAGE_CODES)).forEach(append);

  if (result.length === 0 && fallback) {
    append(fallback);
  }

  return result;
}

export function buildMyLinguistModelOptions(
  currentModel: string | null | undefined,
  availableModels: string[],
  fallbackModel: string,
): string[] {
  const seen = new Set<string>();
  const models: string[] = [];
  const append = (value: string | null | undefined) => {
    if (!value) {
      return;
    }
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    const key = trimmed.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    models.push(trimmed);
  };

  append(currentModel);
  append(fallbackModel);
  availableModels.forEach(append);

  if (models.length === 0 && fallbackModel) {
    return [fallbackModel];
  }

  return models;
}

export function normalizeValidation(
  raw: JobTimingEntry['validation'],
): { drift?: number; count?: number } | undefined {
  if (!raw || typeof raw !== 'object') {
    return undefined;
  }
  const drift = normalizeNumber((raw as { drift?: unknown }).drift);
  const countRaw = normalizeNumber((raw as { count?: unknown }).count);
  if (drift === undefined && countRaw === undefined) {
    return undefined;
  }
  const payload: { drift?: number; count?: number } = {};
  if (drift !== undefined) {
    payload.drift = drift;
  }
  if (countRaw !== undefined) {
    payload.count = Math.max(0, Math.round(countRaw));
  }
  return payload;
}

export function buildSentenceGateList(payload?: TimingPayload | null): SentenceGate[] {
  if (!payload || !Array.isArray(payload.segments) || payload.segments.length === 0) {
    return [];
  }
  const isSingleTrack = payload.trackKind !== 'original_translation_combined';
  const entries: Array<{ token: WordToken; segmentIndex: number }> = [];
  payload.segments.forEach((segment, segmentIndex) => {
    if (!segment || !Array.isArray(segment.tokens)) {
      return;
    }
    segment.tokens.forEach((token) => {
      if (token) {
        entries.push({ token, segmentIndex });
      }
    });
  });
  if (entries.length === 0) {
    return [];
  }
  const grouped = groupBy(entries, (entry) => {
    if (typeof entry.token.sentenceIdx === 'number' && Number.isFinite(entry.token.sentenceIdx)) {
      return entry.token.sentenceIdx;
    }
    const numericSeg = Number(entry.token.segId);
    return Number.isFinite(numericSeg) ? numericSeg : entry.token.segId;
  });
  const gates: SentenceGate[] = [];
  for (const [key, group] of grouped.entries()) {
    if (!group || group.length === 0) {
      continue;
    }
    const candidate = group.find(
      ({ token }) => Number.isFinite(token.startGate) && Number.isFinite(token.endGate),
    );
    if (!candidate) {
      continue;
    }
    let start = Number(candidate.token.startGate);
    let end = Number(candidate.token.endGate);
    if (isSingleTrack) {
      const firstWord = group.reduce<number>((min, { token }) => {
        if (token && Number.isFinite(token.t0)) {
          return Math.min(min, Number(token.t0));
        }
        return min;
      }, Number.POSITIVE_INFINITY);
      const lastWord = group.reduce<number>((max, { token }) => {
        if (token && Number.isFinite(token.t1)) {
          return Math.max(max, Number(token.t1));
        }
        return max;
      }, Number.NEGATIVE_INFINITY);
      if (Number.isFinite(firstWord) && Number.isFinite(lastWord)) {
        start = firstWord;
        end = lastWord;
      }
    }
    if (!Number.isFinite(start) || !Number.isFinite(end)) {
      continue;
    }
    const numericKey = typeof key === 'number' ? key : Number(key);
    const sentenceIdx =
      typeof candidate.token.sentenceIdx === 'number' && Number.isFinite(candidate.token.sentenceIdx)
        ? candidate.token.sentenceIdx
        : Number.isFinite(numericKey)
          ? numericKey
          : undefined;
    if (sentenceIdx === undefined) {
      continue;
    }
    gates.push({
      start,
      end,
      sentenceIdx,
      segmentIndex: candidate.segmentIndex,
      pauseBeforeMs: candidate.token.pauseBeforeMs,
      pauseAfterMs: candidate.token.pauseAfterMs,
    });
  }
  gates.sort((left, right) => left.start - right.start);
  return gates;
}

export function buildTimingPayloadFromJobTiming(
  response: JobTimingResponse,
  trackName: 'mix' | 'translation' | 'original',
): TimingPayload | null {
  if (!response || !response.tracks || !response.tracks[trackName]) {
    return null;
  }
  const trackPayload = response.tracks[trackName];
  const rawSegments = Array.isArray(trackPayload.segments) ? trackPayload.segments : [];
  if (rawSegments.length === 0) {
    return null;
  }

  type Bucket = {
    id: string;
    tokens: WordToken[];
    min: number;
    max: number;
    sentenceIdx?: number;
    gateStart?: number;
    gateEnd?: number;
    pauseBeforeMs?: number;
    pauseAfterMs?: number;
  };

  const buckets = new Map<string, Bucket>();

  rawSegments.forEach((entry, index) => {
    if (!entry) {
      return;
    }
    const rawStart = Number(
      entry.start ?? entry.t0 ?? entry.begin ?? entry.offset ?? entry.time ?? Number.NaN,
    );
    const rawEnd = Number(entry.end ?? entry.t1 ?? entry.stop ?? rawStart);
    if (!Number.isFinite(rawStart)) {
      return;
    }
    const canonicalStartGate = normalizeNumber(entry.startGate);
    const canonicalEndGate = normalizeNumber(entry.endGate);
    let t0 = Math.max(0, rawStart);
    let t1 = Number.isFinite(rawEnd) ? Math.max(rawEnd, t0) : t0;
    const sentenceIdxCandidate =
      entry.sentenceIdx ?? entry.id ?? null;
    const sentenceIdxValue = normalizeNumber(sentenceIdxCandidate);
    const sentenceRef =
      entry.sentenceIdx ?? entry.id ?? `seg-${index}`;
    const segmentId = sentenceRef === null || sentenceRef === undefined || sentenceRef === ''
      ? `seg-${index}`
      : String(sentenceRef);
    let bucket = buckets.get(segmentId);
    if (!bucket) {
      bucket = {
        id: segmentId,
        tokens: [],
        min: Number.POSITIVE_INFINITY,
        max: Number.NEGATIVE_INFINITY,
      };
      buckets.set(segmentId, bucket);
    }
    const startGate = canonicalStartGate;
    const endGate = canonicalEndGate;
    const pauseBeforeMs = normalizeNumber(entry.pauseBeforeMs);
    const pauseAfterMs = normalizeNumber(entry.pauseAfterMs);
    const validation = normalizeValidation(entry.validation);
    const textValue =
      typeof entry.text === 'string'
        ? entry.text
        : typeof entry.token === 'string'
          ? entry.token
          : '';
    const lane =
      trackName === 'mix'
        ? entry.lane === 'orig'
          ? 'orig'
          : 'tran'
        : trackName === 'original'
          ? 'orig'
          : 'tran';
    const tokenId = `${segmentId}-${bucket.tokens.length}`;
    bucket.tokens.push({
      id: tokenId,
      text: textValue,
      t0,
      t1,
      lane,
      segId: segmentId,
      sentenceIdx: sentenceIdxValue,
      startGate: startGate,
      endGate: endGate,
      pauseBeforeMs: pauseBeforeMs,
      pauseAfterMs: pauseAfterMs,
      validation,
    });
    if (t0 < bucket.min) {
      bucket.min = t0;
    }
    if (t1 > bucket.max) {
      bucket.max = t1;
    }
    if (sentenceIdxValue !== undefined && bucket.sentenceIdx === undefined) {
      bucket.sentenceIdx = sentenceIdxValue;
    }
    if (startGate !== undefined && bucket.gateStart === undefined) {
      bucket.gateStart = startGate;
    }
    if (endGate !== undefined) {
      bucket.gateEnd = endGate;
    }
    if (pauseBeforeMs !== undefined && bucket.pauseBeforeMs === undefined) {
      bucket.pauseBeforeMs = pauseBeforeMs;
    }
    if (pauseAfterMs !== undefined && bucket.pauseAfterMs === undefined) {
      bucket.pauseAfterMs = pauseAfterMs;
    }
  });

  if (buckets.size === 0) {
    return null;
  }

  const segments: Segment[] = Array.from(buckets.values())
    .map<Segment | null>((bucket) => {
      const tokens = bucket.tokens.sort((left, right) => {
        if (left.t0 !== right.t0) {
          return left.t0 - right.t0;
        }
        if (left.t1 !== right.t1) {
          return left.t1 - right.t1;
        }
        return left.id.localeCompare(right.id);
      });
      const first = tokens[0];
      const last = tokens[tokens.length - 1] ?? first;
      if (!first || !last) {
        return null;
      }
      const resolvedT0 = Number.isFinite(bucket.min) ? bucket.min : first.t0;
      const resolvedT1 = Number.isFinite(bucket.max) ? bucket.max : last.t1;
      const segment: Segment = {
        id: bucket.id,
        t0: resolvedT0,
        t1: resolvedT1 >= resolvedT0 ? resolvedT1 : resolvedT0,
        tokens,
        sentenceIdx: bucket.sentenceIdx,
        gateStart: bucket.gateStart,
        gateEnd: bucket.gateEnd,
        pauseBeforeMs: bucket.pauseBeforeMs,
        pauseAfterMs: bucket.pauseAfterMs,
      };
      return segment;
    })
    .filter((segment): segment is Segment => segment !== null)
    .sort((left, right) => {
      if (left.t0 !== right.t0) {
        return left.t0 - right.t0;
      }
      if (left.t1 !== right.t1) {
        return left.t1 - right.t1;
      }
      return left.id.localeCompare(right.id);
    });

  if (segments.length === 0) {
    return null;
  }

  const playbackRateValue = Number(trackPayload.playback_rate);
  const payload: TimingPayload = {
    trackKind:
      trackName === 'mix'
        ? 'original_translation_combined'
        : trackName === 'original'
          ? 'original_only'
          : 'translation_only',
    segments,
  };
  if (Number.isFinite(playbackRateValue) && playbackRateValue > 0) {
    payload.playbackRate = Math.round(playbackRateValue * 1000) / 1000;
  }
  return payload;
}

export function computeTimingMetrics(
  payload: TimingPayload,
  playbackRate?: number | null,
): { avgTokenMs: number; uniformVsRealMeanDeltaMs: number; tempoRatio: number; totalDriftMs: number } {
  if (!payload || !Array.isArray(payload.segments) || payload.segments.length === 0) {
    return { avgTokenMs: 0, uniformVsRealMeanDeltaMs: 0, tempoRatio: 1, totalDriftMs: 0 };
  }

  let totalDuration = 0;
  let tokenCount = 0;
  let aggregateUniformDelta = 0;

  payload.segments.forEach((segment) => {
    if (!segment || !Array.isArray(segment.tokens) || segment.tokens.length === 0) {
      return;
    }
    const segmentDuration = Math.max(0, Number(segment.t1) - Number(segment.t0));
    const uniformDuration = segmentDuration > 0 ? segmentDuration / segment.tokens.length : 0;
    segment.tokens.forEach((token) => {
      if (!token) {
        return;
      }
      const tokenDuration = Math.max(0, Number(token.t1) - Number(token.t0));
      totalDuration += tokenDuration;
      tokenCount += 1;
      if (uniformDuration > 0) {
        aggregateUniformDelta += Math.abs(tokenDuration - uniformDuration);
      }
    });
  });

  const avgTokenMs = tokenCount > 0 ? (totalDuration * 1000) / tokenCount : 0;
  const uniformVsRealMeanDeltaMs = tokenCount > 0 ? (aggregateUniformDelta * 1000) / tokenCount : 0;
  const tempoRatio =
    typeof playbackRate === 'number' && Number.isFinite(playbackRate) && playbackRate > 0
      ? playbackRate
      : 1;
  const totalDriftMs = aggregateUniformDelta * 1000;

  return { avgTokenMs, uniformVsRealMeanDeltaMs, tempoRatio, totalDriftMs };
}

export function normaliseTokens(variant?: { tokens?: string[]; text?: string | null }): string[] {
  if (!variant) {
    return [];
  }
  if (Array.isArray(variant.tokens) && variant.tokens.length > 0) {
    return variant.tokens.filter((token) => typeof token === 'string' && token.length > 0);
  }
  if (variant.text && typeof variant.text === 'string') {
    const trimmed = variant.text.trim();
    if (!trimmed) {
      return [];
    }
    return trimmed.split(/\s+/);
  }
  return [];
}

export function buildUniformRevealTimes(count: number, startTime: number, duration: number): number[] {
  const tokenCount = Math.max(0, count);
  if (tokenCount === 0) {
    return [];
  }
  const safeDuration = duration > 0 ? duration : 0;
  if (safeDuration === 0) {
    return Array(tokenCount).fill(startTime);
  }
  const step = safeDuration / tokenCount;
  const reveals: number[] = [];
  for (let index = 1; index <= tokenCount; index += 1) {
    const offset = step > 0 ? step * (index - 1) : 0;
    const reveal = startTime + Math.max(0, Math.min(safeDuration, offset));
    reveals.push(reveal);
  }
  return reveals;
}

export function distributeRevealTimes(
  previousCount: number,
  nextCount: number,
  startTime: number,
  duration: number,
  collector: number[],
) {
  const clampedPrev = Math.max(previousCount, 0);
  const clampedNext = Math.max(nextCount, 0);
  const delta = clampedNext - clampedPrev;
  if (delta <= 0) {
    return;
  }
  const safeDuration = duration > 0 ? duration : 0;
  const step = delta > 0 ? safeDuration / delta : 0;
  for (let index = 1; index <= delta; index += 1) {
    const offset = step > 0 ? step * (index - 1) : 0;
    collector.push(startTime + Math.max(0, Math.min(safeDuration, offset)));
  }
}

export function fillRemainTimes(target: number[], totalTokens: number, fallbackTime: number) {
  const safeFallback = fallbackTime > 0 ? fallbackTime : 0;
  while (target.length < totalTokens) {
    target.push(safeFallback);
  }
  if (target.length > totalTokens) {
    target.length = totalTokens;
  }
}

type SegmenterInstance = {
  segment: (input: string) => Iterable<{ segment: string }>;
};

type SegmenterConstructor = new (
  locales?: Intl.LocalesArgument,
  options?: { granularity?: 'grapheme' | 'word' | 'sentence' },
) => SegmenterInstance;

const segmenterCtor =
  typeof Intl !== 'undefined'
    ? (Intl as typeof Intl & { Segmenter?: SegmenterConstructor }).Segmenter ?? null
    : null;
const hasIntlSegmenter = typeof segmenterCtor === 'function';

export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const match = hex.trim().match(/^#([0-9a-fA-F]{6})$/);
  if (!match) {
    return null;
  }
  const digits = match[1];
  const r = Number.parseInt(digits.slice(0, 2), 16);
  const g = Number.parseInt(digits.slice(2, 4), 16);
  const b = Number.parseInt(digits.slice(4, 6), 16);
  if (!Number.isFinite(r) || !Number.isFinite(g) || !Number.isFinite(b)) {
    return null;
  }
  return { r, g, b };
}

export function rgbaFromHex(hex: string, alpha: number): string | null {
  const rgb = hexToRgb(hex);
  if (!rgb) {
    return null;
  }
  const safeAlpha = Number.isFinite(alpha) ? Math.min(Math.max(alpha, 0), 1) : 1;
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${safeAlpha})`;
}

export function segmentParagraph(paragraph: string): string[] {
  if (!paragraph) {
    return [];
  }

  const trimmed = paragraph.trim();
  if (!trimmed) {
    return [];
  }

  if (hasIntlSegmenter && segmenterCtor) {
    try {
      const segmenter = new segmenterCtor(undefined, { granularity: 'sentence' });
      const segments: string[] = [];
      for (const entry of segmenter.segment(trimmed)) {
        const segment = entry.segment.trim();
        if (segment) {
          segments.push(segment);
        }
      }
      if (segments.length > 0) {
        return segments;
      }
    } catch (error) {
      // Ignore segmenter failures and fall back to regex splitting.
    }
  }

  const fallbackMatches = trimmed.match(/[^.!?。！？]+[.!?。！？]?/g);
  if (!fallbackMatches || fallbackMatches.length === 0) {
    return [trimmed];
  }

  return fallbackMatches.map((segment) => segment.trim()).filter(Boolean);
}

export function buildSentenceParts(value: string): Array<{ content: string; isWord: boolean }> {
  if (!value) {
    return [];
  }
  const segments = value.match(/(\S+|\s+)/g) ?? [value];
  return segments.map((segment) => ({
    content: segment,
    isWord: /\S/.test(segment) && !/^\s+$/.test(segment),
  }));
}

export function parseSentenceVariants(raw: string): {
  primary: string;
  translation: string | null;
  transliteration: string | null;
} {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { primary: '', translation: null, transliteration: null };
  }
  const segments = trimmed
    .split('||')
    .map((segment) => segment.trim())
    .filter((segment, index) => segment.length > 0 || index === 0);
  const primary = segments[0] ?? trimmed;
  const translation = segments[1] ?? null;
  const transliteration = segments[2] ?? null;
  return {
    primary,
    translation,
    transliteration,
  };
}

export function buildParagraphs(content: string): ParagraphFragment[] {
  const trimmed = content?.trim();
  if (!trimmed) {
    return [];
  }

  const rawParagraphs = trimmed.split(/\n{2,}/).map((paragraph) => paragraph.replace(/\s*\n\s*/g, ' ').trim());
  const paragraphs: ParagraphFragment[] = [];
  let nextIndex = 0;

  rawParagraphs.forEach((raw, paragraphIndex) => {
    if (!raw) {
      return;
    }

    const segments = segmentParagraph(raw);
    if (segments.length === 0) {
      const variants = parseSentenceVariants(raw);
      const parts = buildSentenceParts(variants.primary);
      const wordCount = parts.filter((part) => part.isWord).length;
      const weight = Math.max(wordCount, variants.primary.length, 1);
      paragraphs.push({
        id: `paragraph-${paragraphIndex}`,
        sentences: [
          {
            index: nextIndex,
            text: variants.primary,
            translation: variants.translation,
            transliteration: variants.transliteration,
            parts,
            wordCount,
            weight,
          },
        ],
      });
      nextIndex += 1;
      return;
    }

    const sentences: SentenceFragment[] = segments.map((segment) => {
      const variants = parseSentenceVariants(segment);
      const parts = buildSentenceParts(variants.primary);
      const wordCount = parts.filter((part) => part.isWord).length;
      const weight = Math.max(wordCount, variants.primary.length, 1);
      const fragment: SentenceFragment = {
        index: nextIndex,
        text: variants.primary,
        translation: variants.translation,
        transliteration: variants.transliteration,
        parts,
        wordCount,
        weight,
      };
      nextIndex += 1;
      return fragment;
    });

    paragraphs.push({
      id: `paragraph-${paragraphIndex}`,
      sentences,
    });
  });

  if (paragraphs.length === 0) {
    const variants = parseSentenceVariants(trimmed);
    const fallbackParts = buildSentenceParts(variants.primary);
    const fallbackWordCount = fallbackParts.filter((part) => part.isWord).length;
    const fallbackWeight = Math.max(fallbackWordCount, variants.primary.length, 1);
    return [
      {
        id: 'paragraph-0',
        sentences: [
          {
            index: 0,
            text: variants.primary,
            translation: variants.translation,
            transliteration: variants.transliteration,
            parts: fallbackParts,
            wordCount: fallbackWordCount,
            weight: fallbackWeight,
          },
        ],
      },
    ];
  }

  return paragraphs;
}
