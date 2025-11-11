import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { CSSProperties, MutableRefObject, ReactNode, UIEvent } from 'react';
import { appendAccessToken, fetchJobTiming } from '../api/client';
import type { AudioTrackMetadata, JobTimingEntry, JobTimingResponse } from '../api/dtos';
import type { LiveMediaChunk, MediaClock } from '../hooks/useLiveMedia';
import { useMediaClock } from '../hooks/useLiveMedia';
import PlayerCore from '../player/PlayerCore';
import { usePlayerCore } from '../hooks/usePlayerCore';
import {
  start as startAudioSync,
  stop as stopAudioSync,
  enableHighlightDebugOverlay,
} from '../player/AudioSyncController';
import { timingStore } from '../stores/timingStore';
import { DebugOverlay } from '../player/DebugOverlay';
import '../styles/debug-overlay.css';
import type { TimingPayload, Segment, TrackKind, WordToken } from '../types/timing';
import { groupBy } from '../utils/groupBy';
import TextPlayer, {
  type TextPlayerSentence,
  type TextPlayerVariantDisplay,
  type TextPlayerVariantKind,
} from '../text-player/TextPlayer';
import type { ChunkSentenceMetadata, TrackTimingPayload, WordTiming } from '../api/dtos';
import { buildWordIndex, collectActiveWordIds, lowerBound, type WordIndex } from '../lib/timing/wordSync';
import { WORD_SYNC, normaliseTranslationSpeed } from './player-panel/constants';

type HighlightDebugWindow = Window & { __HL_DEBUG__?: { enabled?: boolean; overlay?: boolean } };

type SentenceFragment = {
  index: number;
  text: string;
  wordCount: number;
  parts: Array<{ content: string; isWord: boolean }>;
  translation: string | null;
  transliteration: string | null;
  weight: number;
};

type ParagraphFragment = {
  id: string;
  sentences: SentenceFragment[];
};

type WordSyncLane = WordTiming['lang'];

type WordSyncRenderableToken = WordTiming & {
  displayText: string;
};

type WordSyncSentence = {
  id: string;
  sentenceId: number;
  tokens: Record<WordSyncLane, WordSyncRenderableToken[]>;
};

type WordSyncController = {
  setTrack: (track: TrackTimingPayload | null, index: WordIndex | null) => void;
  start: () => void;
  stop: () => void;
  destroy: () => void;
  snap: () => void;
  handleSeeking: () => void;
  handleSeeked: () => void;
  handleWaiting: () => void;
  handlePlaying: () => void;
  handleRateChange: () => void;
  handlePause: () => void;
  handlePlay: () => void;
  setFollowHighlight: (value: boolean) => void;
};

type SentenceGate = {
  start: number;
  end: number;
  sentenceIdx: number;
  segmentIndex: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
};

const WORD_SYNC_LANE_LABELS: Record<WordSyncLane, string> = {
  orig: 'Original',
  trans: 'Translation',
  xlit: 'Transliteration',
};

const EMPTY_TIMING_PAYLOAD: TimingPayload = {
  trackKind: 'translation_only',
  segments: [],
};

function toTrackKind(track: TrackTimingPayload): TrackKind {
  return track.trackType === 'original_translated'
    ? 'original_translation_combined'
    : 'translation_only';
}

function extractPlaybackRate(track: TrackTimingPayload): number | undefined {
  const raw = Number(track.tempoFactor);
  if (!Number.isFinite(raw) || raw <= 0) {
    return undefined;
  }
  return Math.round(raw * 1000) / 1000;
}

function buildTimingPayloadFromWordIndex(
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

function normalizeNumber(value: unknown): number | undefined {
  if (value === null || value === undefined) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function normalizeValidation(
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

function buildSentenceGateList(payload?: TimingPayload | null): SentenceGate[] {
  if (!payload || !Array.isArray(payload.segments) || payload.segments.length === 0) {
    return [];
  }
  const isTranslationTrack = payload.trackKind === 'translation_only';
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
    if (isTranslationTrack) {
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

function buildTimingPayloadFromJobTiming(
  response: JobTimingResponse,
  trackName: 'mix' | 'translation',
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
    const canonicalStartGate = normalizeNumber(entry.startGate ?? entry.start_gate);
    const canonicalEndGate = normalizeNumber(entry.endGate ?? entry.end_gate);
    let t0 = Math.max(0, rawStart);
    let t1 = Number.isFinite(rawEnd) ? Math.max(rawEnd, t0) : t0;
    const gateValue = Number(canonicalStartGate);
    const gateAvailable = Number.isFinite(gateValue);
    if (trackName === 'translation' && gateAvailable && rawStart >= gateValue - 1e-3) {
      t0 = Math.max(0, t0 - gateValue);
      t1 = Math.max(t1 - gateValue, t0);
    }
    const sentenceIdxCandidate =
      entry.sentenceIdx ?? entry.sentence_id ?? entry.sentenceId ?? entry.id ?? null;
    const sentenceIdxValue = normalizeNumber(sentenceIdxCandidate);
    const sentenceRef =
      entry.sentenceIdx ?? entry.sentence_id ?? entry.sentenceId ?? entry.id ?? `seg-${index}`;
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
    const pauseBeforeMs = normalizeNumber(entry.pauseBeforeMs ?? entry.pause_before_ms);
    const pauseAfterMs = normalizeNumber(entry.pauseAfterMs ?? entry.pause_after_ms);
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
    trackKind: trackName === 'mix' ? 'original_translation_combined' : 'translation_only',
    segments,
  };
  if (Number.isFinite(playbackRateValue) && playbackRateValue > 0) {
    payload.playbackRate = Math.round(playbackRateValue * 1000) / 1000;
  }
  return payload;
}

function computeTimingMetrics(
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

type TimelineVariantRuntime = {
  tokens: string[];
  revealTimes: number[];
};

type TimelineSentenceRuntime = {
  index: number;
  sentenceNumber?: number | null;
  startTime: number;
  endTime: number;
  variants: {
    original: TimelineVariantRuntime;
    translation?: TimelineVariantRuntime;
    transliteration?: TimelineVariantRuntime;
  };
};

function normaliseTokens(variant?: { tokens?: string[]; text?: string | null }): string[] {
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

function buildUniformRevealTimes(count: number, startTime: number, duration: number): number[] {
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

function distributeRevealTimes(
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

function fillRemainTimes(target: number[], totalTokens: number, fallbackTime: number) {
  const safeFallback = fallbackTime > 0 ? fallbackTime : 0;
  while (target.length < totalTokens) {
    target.push(safeFallback);
  }
  if (target.length > totalTokens) {
    target.length = totalTokens;
  }
}

type InlineAudioControls = {
  pause: () => void;
  play: () => void;
};

interface InteractiveTextViewerProps {
  content: string;
  rawContent?: string | null;
  chunk: LiveMediaChunk | null;
  totalSentencesInBook?: number | null;
  activeAudioUrl: string | null;
  noAudioAvailable: boolean;
  jobId?: string | null;
  onScroll?: (event: UIEvent<HTMLDivElement>) => void;
  onAudioProgress?: (audioUrl: string, position: number) => void;
  getStoredAudioPosition?: (audioUrl: string) => number;
  onRegisterInlineAudioControls?: (controls: InlineAudioControls | null) => void;
  onInlineAudioPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  onRequestAdvanceChunk?: () => void;
  isFullscreen?: boolean;
  onRequestExitFullscreen?: () => void;
  fullscreenControls?: ReactNode;
  audioTracks?: Record<string, AudioTrackMetadata> | null;
  activeTimingTrack?: 'mix' | 'translation';
  originalAudioEnabled?: boolean;
  translationSpeed?: number;
  fontScale?: number;
  bookTitle?: string | null;
  bookCoverUrl?: string | null;
  bookCoverAltText?: string | null;
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

function segmentParagraph(paragraph: string): string[] {
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

function buildSentenceParts(value: string): Array<{ content: string; isWord: boolean }> {
  if (!value) {
    return [];
  }
  const segments = value.match(/(\S+|\s+)/g) ?? [value];
  return segments.map((segment) => ({
    content: segment,
    isWord: /\S/.test(segment) && !/^\s+$/.test(segment),
  }));
}

function parseSentenceVariants(raw: string): {
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

function buildParagraphs(content: string): ParagraphFragment[] {
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

const InteractiveTextViewer = forwardRef<HTMLDivElement | null, InteractiveTextViewerProps>(function InteractiveTextViewer(
  {
    content,
    rawContent = null,
    chunk,
    totalSentencesInBook = null,
    activeAudioUrl,
    noAudioAvailable,
    jobId = null,
    onScroll,
    onAudioProgress,
    getStoredAudioPosition,
    onRegisterInlineAudioControls,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    isFullscreen = false,
    onRequestExitFullscreen,
    fullscreenControls,
    audioTracks = null,
    activeTimingTrack = 'translation',
    originalAudioEnabled = false,
    translationSpeed = 1,
    fontScale = 1,
    bookTitle = null,
    bookCoverUrl = null,
    bookCoverAltText = null,
  },
  forwardedRef,
) {
  const resolvedTranslationSpeed = useMemo(
    () => normaliseTranslationSpeed(translationSpeed),
    [translationSpeed],
  );
  const safeBookTitle = typeof bookTitle === 'string' ? bookTitle.trim() : '';
  const safeFontScale = useMemo(() => {
    if (!Number.isFinite(fontScale) || fontScale <= 0) {
      return 1;
    }
    const clamped = Math.min(Math.max(fontScale, 0.5), 3);
    return Math.round(clamped * 100) / 100;
  }, [fontScale]);
  const formatRem = useCallback((value: number) => `${Math.round(value * 1000) / 1000}rem`, []);
  const bodyStyle = useMemo<CSSProperties>(() => {
    const baseSentenceFont = (isFullscreen ? 1.32 : 1.08) * safeFontScale;
    const activeSentenceFont = (isFullscreen ? 1.56 : 1.28) * safeFontScale;
    return {
      '--interactive-font-scale': safeFontScale,
      '--tp-sentence-font-size': formatRem(baseSentenceFont),
      '--tp-sentence-active-font-size': formatRem(activeSentenceFont),
    } as CSSProperties;
  }, [formatRem, isFullscreen, safeFontScale]);
  const [viewportCoverFailed, setViewportCoverFailed] = useState(false);
  useEffect(() => {
    setViewportCoverFailed(false);
  }, [bookCoverUrl]);
  const resolvedBookCoverUrl = viewportCoverFailed ? null : bookCoverUrl;
  const showBookBadge = Boolean(safeBookTitle || resolvedBookCoverUrl);
  const bookBadgeAltText =
    bookCoverAltText ?? (safeBookTitle ? `Cover of ${safeBookTitle}` : 'Book cover preview');
  const rootRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const {
    ref: attachPlayerCore,
    core: playerCore,
    elementRef: audioRef,
    mediaRef: rawAttachMediaElement,
  } = usePlayerCore();
  const attachMediaElement = useCallback(
    (element: HTMLAudioElement | null) => {
      rawAttachMediaElement(element);
      timingStore.setAudioEl(element);
    },
    [rawAttachMediaElement],
  );
  const tokenElementsRef = useRef<Map<string, HTMLElement>>(new Map());
  const sentenceElementsRef = useRef<Map<number, HTMLElement>>(new Map());
  const wordSyncControllerRef = useRef<WordSyncController | null>(null);
  const gateListRef = useRef<SentenceGate[]>([]);
  const clock = useMediaClock(audioRef);
  const clockRef = useRef<MediaClock>(clock);
  const diagnosticsSignatureRef = useRef<string | null>(null);
  const highlightPolicyRef = useRef<string | null>(null);
  const [jobTimingResponse, setJobTimingResponse] = useState<JobTimingResponse | null>(null);
  const [timingDiagnostics, setTimingDiagnostics] = useState<{ policy: string | null; estimated: boolean; punctuation?: boolean } | null>(null);
  useEffect(() => {
    if (process.env.NODE_ENV === 'production') {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const globalWindow = window as HighlightDebugWindow;
    if (!globalWindow.__HL_DEBUG__?.enabled) {
      return;
    }
    const cleanup = enableHighlightDebugOverlay();
    return () => {
      cleanup();
    };
  }, []);

  useEffect(() => {
    clockRef.current = clock;
  }, [clock]);
  useEffect(() => {
    highlightPolicyRef.current = timingDiagnostics?.policy ?? null;
  }, [timingDiagnostics]);
  useEffect(() => {
    const element = playerCore?.getElement() ?? audioRef.current ?? null;
    timingStore.setAudioEl(element);
    return () => {
      if (timingStore.get().audioEl === element) {
        timingStore.setAudioEl(null);
      }
    };
  }, [playerCore]);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return false;
    }
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch {
      return false;
    }
  });
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    let mounted = true;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      if (!mounted) {
        return;
      }
      setPrefersReducedMotion(media.matches);
    };
    update();
    try {
      if (typeof media.addEventListener === 'function') {
        media.addEventListener('change', update);
        return () => {
          mounted = false;
          media.removeEventListener('change', update);
        };
      }
      if (typeof media.addListener === 'function') {
        media.addListener(update);
        return () => {
          mounted = false;
          media.removeListener(update);
        };
      }
    } catch {
      // Ignore listener registration errors.
    }
    return () => {
      mounted = false;
    };
  }, []);
  const fullscreenRequestedRef = useRef(false);
  const fullscreenResyncPendingRef = useRef(false);
  const fullscreenResyncToken = useMemo(() => {
    const parts: (string | number)[] = [];
    if (chunk) {
      parts.push(
        chunk.chunkId ?? '',
        chunk.rangeFragment ?? '',
        chunk.metadataPath ?? '',
        chunk.metadataUrl ?? '',
        chunk.startSentence ?? '',
        chunk.endSentence ?? '',
      );
    } else {
      parts.push('no-chunk');
    }
    parts.push(content.length, (rawContent ?? '').length, activeAudioUrl ?? 'none');
    return parts.join('|');
  }, [activeAudioUrl, chunk, content, rawContent]);
  const isFullscreenRef = useRef(isFullscreen);
  useEffect(() => {
    isFullscreenRef.current = isFullscreen;
  }, [isFullscreen]);

  const requestFullscreenIfNeeded = useCallback(() => {
    if (!isFullscreenRef.current || typeof document === 'undefined') {
      return;
    }
    const element = rootRef.current;
    if (!element) {
      return;
    }
    if (document.fullscreenElement === element || fullscreenRequestedRef.current) {
      return;
    }
    if (typeof element.requestFullscreen !== 'function') {
      fullscreenResyncPendingRef.current = false;
      onRequestExitFullscreen?.();
      return;
    }
    try {
      const requestResult = element.requestFullscreen();
      fullscreenRequestedRef.current = true;
      if (requestResult && typeof requestResult.catch === 'function') {
        requestResult.catch(() => {
          fullscreenRequestedRef.current = false;
          fullscreenResyncPendingRef.current = false;
          onRequestExitFullscreen?.();
        });
      }
    } catch {
      fullscreenRequestedRef.current = false;
      fullscreenResyncPendingRef.current = false;
      onRequestExitFullscreen?.();
    }
  }, [onRequestExitFullscreen]);
  useImperativeHandle<HTMLDivElement | null, HTMLDivElement | null>(forwardedRef, () => containerRef.current);
  const [chunkTime, setChunkTime] = useState(0);
  const hasTimeline = Boolean(chunk?.sentences && chunk.sentences.length > 0);
  const useCombinedPhases = Boolean(
    originalAudioEnabled &&
      (audioTracks?.orig_trans?.url || audioTracks?.orig_trans?.path),
  );
  const [audioDuration, setAudioDuration] = useState<number | null>(null);
  const [activeSentenceIndex, setActiveSentenceIndex] = useState(0);
  const [activeSentenceProgress, setActiveSentenceProgress] = useState(0);
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
  const followHighlightEnabled = !prefersReducedMotion;
  useEffect(() => {
    if (!jobId || !wordSyncAllowed) {
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
  }, [jobId, wordSyncAllowed]);

  const paragraphs = useMemo(() => buildParagraphs(content), [content]);
  const timelineSentences = useMemo(() => {
    if (!hasTimeline || !chunk?.sentences?.length) {
      return null;
    }

    let offset = 0;
    const result: TimelineSentenceRuntime[] = [];

    chunk.sentences.forEach((metadata, index) => {
      const originalTokens = normaliseTokens(metadata.original ?? undefined);
      const translationTokens = normaliseTokens(metadata.translation ?? undefined);
      const transliterationTokens = normaliseTokens(metadata.transliteration ?? undefined);

      const events = Array.isArray(metadata.timeline) ? metadata.timeline : [];

      const originalReveal: number[] = [];

      const phaseDurations = useCombinedPhases ? metadata.phase_durations ?? null : null;
      const originalPhaseDuration = phaseDurations && typeof phaseDurations.original === 'number' ? Math.max(phaseDurations.original, 0) : 0;
      const gapBeforeTranslation = phaseDurations && typeof phaseDurations.gap === 'number' ? Math.max(phaseDurations.gap, 0) : 0;
      const tailPhaseDuration = phaseDurations && typeof phaseDurations.tail === 'number' ? Math.max(phaseDurations.tail, 0) : 0;
      const translationPhaseDurationOverride = phaseDurations && typeof phaseDurations.translation === 'number'
        ? Math.max(phaseDurations.translation, 0)
        : null;
      const highlightOriginal = useCombinedPhases && originalTokens.length > 0 && originalPhaseDuration > 0;

      const eventDurationTotal = events.reduce((total, event) => {
        const duration = typeof event.duration === 'number' && event.duration > 0 ? event.duration : 0;
        return total + duration;
      }, 0);

      const declaredDuration = (() => {
        if (typeof metadata.total_duration === 'number' && metadata.total_duration > 0) {
          return metadata.total_duration;
        }
        if (eventDurationTotal > 0) {
          return eventDurationTotal;
        }
        const fallbackTokens = Math.max(
          originalTokens.length,
          translationTokens.length,
          transliterationTokens.length,
        );
        if (fallbackTokens > 0) {
          return fallbackTokens * 0.35;
        }
        return 0.5;
      })();

      const sentenceStart = offset;

      const translationPhaseDuration = (() => {
        if (translationPhaseDurationOverride !== null && translationPhaseDurationOverride > 0) {
          return translationPhaseDurationOverride;
        }
        if (declaredDuration > 0) {
          return declaredDuration;
        }
        if (translationTokens.length > 0 || transliterationTokens.length > 0) {
          return Math.max(translationTokens.length, transliterationTokens.length) * 0.35;
        }
        return 0.5;
      })();

      const translationTrackStart = sentenceStart + (useCombinedPhases ? originalPhaseDuration + gapBeforeTranslation : 0);

      const translationDurationsRaw: number[] = [];
      let prevTranslationCount = 0;

      events.forEach((event) => {
        const baseDuration = typeof event.duration === 'number' && event.duration > 0 ? event.duration : 0;
        if (!(baseDuration > 0)) {
          return;
        }
        const targetTranslationIndex = typeof event.translation_index === 'number' ? Math.max(0, event.translation_index) : prevTranslationCount;
        const nextTranslationCount = Math.min(
          translationTokens.length,
          Math.max(prevTranslationCount, targetTranslationIndex),
        );
        const delta = nextTranslationCount - prevTranslationCount;
        if (delta <= 0) {
          return;
        }
        const perToken = baseDuration / delta;
        for (let idx = 0; idx < delta; idx += 1) {
          translationDurationsRaw.push(perToken);
        }
        prevTranslationCount = nextTranslationCount;
      });

      const totalTranslationDurationRaw = translationDurationsRaw.reduce((sum, value) => sum + value, 0);
      const translationSpeechDuration = totalTranslationDurationRaw > 0 ? totalTranslationDurationRaw : translationPhaseDuration;
      const translationTotalDuration = translationSpeechDuration + tailPhaseDuration;
      const translationPhaseEndAbsolute = translationTrackStart + translationTotalDuration;

      let translationRevealTimes: number[] = [];
      if (translationDurationsRaw.length > 0) {
        let cumulativeTranslation = 0;
        translationDurationsRaw.forEach((rawDuration) => {
          translationRevealTimes.push(translationTrackStart + cumulativeTranslation);
          cumulativeTranslation += rawDuration;
        });
      }

      if (translationRevealTimes.length !== translationTokens.length && translationTokens.length > 0) {
        translationRevealTimes = buildUniformRevealTimes(
          translationTokens.length,
          translationTrackStart,
          translationSpeechDuration,
        );
      }

      const transliterationRevealTimes = transliterationTokens.length > 0
        ? transliterationTokens.map((_, idx) => {
            if (translationRevealTimes.length === 0) {
              return translationTrackStart;
            }
            if (translationRevealTimes.length === 1) {
              return translationRevealTimes[0];
            }
            const ratio = transliterationTokens.length > 1 ? idx / (transliterationTokens.length - 1) : 0;
            const mappedIndex = Math.min(
              translationRevealTimes.length - 1,
              Math.round(ratio * (translationRevealTimes.length - 1)),
            );
            return translationRevealTimes[mappedIndex];
          })
        : [];

      if (translationRevealTimes.length > 0) {
        translationRevealTimes[0] = translationTrackStart;
        translationRevealTimes[translationRevealTimes.length - 1] = translationPhaseEndAbsolute;
      }
      if (transliterationRevealTimes.length > 0) {
        transliterationRevealTimes[0] = translationTrackStart;
        transliterationRevealTimes[transliterationRevealTimes.length - 1] = translationPhaseEndAbsolute;
      }

      if (translationRevealTimes.length > 0) {
        translationRevealTimes[translationRevealTimes.length - 1] = translationPhaseEndAbsolute;
      }
      if (transliterationRevealTimes.length > 0) {
        transliterationRevealTimes[transliterationRevealTimes.length - 1] = translationPhaseEndAbsolute;
      }

      if (highlightOriginal) {
        const reveals = buildUniformRevealTimes(originalTokens.length, sentenceStart, originalPhaseDuration);
        originalReveal.splice(0, originalReveal.length, ...reveals);
      }

      const sentenceDuration = useCombinedPhases
        ? originalPhaseDuration + gapBeforeTranslation + translationTotalDuration
        : translationTotalDuration;
      const endTime = sentenceStart + sentenceDuration;

      result.push({
        index,
        sentenceNumber: metadata.sentence_number ?? null,
        startTime: sentenceStart,
        endTime,
        variants: {
          original: {
            tokens: originalTokens,
            revealTimes: originalReveal,
          },
          translation: translationTokens.length
            ? {
                tokens: translationTokens,
                revealTimes: translationRevealTimes,
              }
            : undefined,
          transliteration: transliterationTokens.length
            ? {
                tokens: transliterationTokens,
                revealTimes: transliterationRevealTimes,
              }
            : undefined,
        },
      });

      offset = endTime;
    });

    if (!useCombinedPhases && audioDuration && audioDuration > 0 && result.length > 0) {
      const totalTimelineDuration = result[result.length - 1].endTime;
      if (totalTimelineDuration > 0) {
        const scale = audioDuration / totalTimelineDuration;
        const scaled = result.map((sentence) => {
          const originalVariant = {
            ...sentence.variants.original,
            revealTimes: sentence.variants.original.revealTimes.map((time) => time * scale),
          };

          const translationVariant = sentence.variants.translation
            ? {
                ...sentence.variants.translation,
                revealTimes: sentence.variants.translation.revealTimes.map((time) => time * scale),
              }
            : undefined;

          const transliterationVariant = sentence.variants.transliteration
            ? {
                ...sentence.variants.transliteration,
                revealTimes: sentence.variants.transliteration.revealTimes.map((time) => time * scale),
              }
            : undefined;

          return {
            ...sentence,
            startTime: sentence.startTime * scale,
            endTime: sentence.endTime * scale,
            variants: {
              original: originalVariant,
              translation: translationVariant,
              transliteration: transliterationVariant,
            },
          };
        });
        return scaled;
      }
    }

    return result;
  }, [audioDuration, chunk?.sentences, hasTimeline, useCombinedPhases]);
  const timelineDisplay = useMemo(() => {
    if (!timelineSentences) {
      return null;
    }

    const displaySentences: TextPlayerSentence[] = [];
    let activeIndex: number | null = null;

    const timelineTotalDuration = timelineSentences.length > 0 ? timelineSentences[timelineSentences.length - 1].endTime : null;
    const effectiveTime = (() => {
      if (!timelineTotalDuration || !audioDuration || audioDuration <= 0 || timelineTotalDuration <= 0) {
        return Math.max(chunkTime, 0);
      }
      const ratio = timelineTotalDuration / audioDuration;
      if (ratio > 0.98 && ratio < 1.02) {
        return Math.min(chunkTime, timelineTotalDuration);
      }
      const scaled = (chunkTime / audioDuration) * timelineTotalDuration;
      if (!Number.isFinite(scaled) || scaled < 0) {
        return 0;
      }
      return Math.min(scaled, timelineTotalDuration);
    })();

    timelineSentences.forEach((runtime) => {
      const { startTime, endTime } = runtime;
      let timeState: 'past' | 'active' | 'future';
      if (effectiveTime < startTime - 1e-3) {
        timeState = 'future';
      } else if (effectiveTime > endTime + 1e-3) {
        timeState = 'past';
      } else {
        timeState = 'active';
        if (activeIndex === null) {
          activeIndex = runtime.index;
        }
      }

      const stabilisedState: 'past' | 'active' | 'future' = (() => {
        if (runtime.index === activeSentenceIndex) {
          return 'active';
        }
        if (runtime.index < activeSentenceIndex) {
          return 'past';
        }
        if (runtime.index > activeSentenceIndex) {
          return 'future';
        }
        return timeState;
      })();

      const variants: TextPlayerVariantDisplay[] = [];

      const buildVariant = (
        label: string,
        baseClass: TextPlayerVariantKind,
        variantRuntime?: TimelineVariantRuntime,
      ) => {
        if (!variantRuntime || variantRuntime.tokens.length === 0) {
          return;
        }

        const tokens = variantRuntime.tokens;
        const revealTimes = variantRuntime.revealTimes;
        const safeEffectiveTime = Math.max(effectiveTime, 0);
        const revealCutoff = Math.min(safeEffectiveTime, endTime);
        const progressCount = revealTimes.filter((time) => time <= revealCutoff + 1e-3).length;

        let revealedCount: number;
        if (stabilisedState === 'past') {
          revealedCount = tokens.length;
        } else if (stabilisedState === 'future') {
          revealedCount = progressCount;
        } else {
          revealedCount = progressCount;
        }

        revealedCount = Math.max(0, Math.min(revealedCount, tokens.length));
        if (stabilisedState === 'active' && revealedCount === 0 && revealTimes.length > 0) {
          if (safeEffectiveTime >= startTime - 1e-3) {
            revealedCount = 1;
          }
        }

        let currentIndex: number | null = revealedCount > 0 ? revealedCount - 1 : null;
        if (stabilisedState === 'past' && tokens.length > 0) {
          currentIndex = tokens.length - 1;
        }

        variants.push({
          label,
          tokens,
          revealedCount,
          currentIndex,
          baseClass,
          seekTimes: variantRuntime.revealTimes,
        });
      };

      buildVariant('Original', 'original', runtime.variants.original);
      buildVariant('Transliteration', 'translit', runtime.variants.transliteration);
      buildVariant('Translation', 'translation', runtime.variants.translation);

      displaySentences.push({
        id: `sentence-${runtime.index}`,
        index: runtime.index,
        sentenceNumber: runtime.sentenceNumber ?? runtime.index + 1,
        state: stabilisedState,
        variants,
      });
    });

    if (activeIndex === null && displaySentences.length > 0) {
      for (let i = displaySentences.length - 1; i >= 0; i -= 1) {
        if (displaySentences[i].state === 'past') {
          activeIndex = displaySentences[i].index;
          break;
        }
      }
      if (activeIndex === null) {
        activeIndex = 0;
      }
    }

    return {
      sentences: displaySentences,
      activeIndex: activeIndex ?? 0,
      effectiveTime,
    };
  }, [timelineSentences, chunkTime, audioDuration, activeSentenceIndex]);
  
  const rawSentences = useMemo(
    () =>
      paragraphs
        .map((paragraph) => paragraph.sentences)
        .flat()
        .sort((a, b) => a.index - b.index),
    [paragraphs],
  );

  const textPlayerSentences = useMemo(() => {
    const forceActive = (sentence: TextPlayerSentence | undefined | null): TextPlayerSentence[] | null => {
      if (!sentence) {
        return null;
      }
      return [
        {
          ...sentence,
          state: 'active',
        },
      ];
    };

    if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
      const active =
        timelineDisplay.sentences.find((entry) => entry.index === activeSentenceIndex) ??
        timelineDisplay.sentences.find((entry) => entry.state === 'active') ??
        timelineDisplay.sentences[0];
      return forceActive(active);
    }

    const buildTokens = (value: string | null | undefined): string[] => {
      if (!value) {
        return [];
      }
      return value
        .split(/\s+/)
        .map((token) => token.trim())
        .filter((token) => token.length > 0);
    };

    if (chunk?.sentences && chunk.sentences.length > 0) {
      const fallbackFromChunk: TextPlayerSentence[] = chunk.sentences.map((metadata, index) => {
        const originalTokens = buildTokens(metadata.original?.text ?? null);
        const transliterationTokens = buildTokens(metadata.transliteration?.text ?? null);
        const translationTokens = buildTokens(metadata.translation?.text ?? null);

        const variants: TextPlayerVariantDisplay[] = [];
        if (originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (translationTokens.length > 0) {
          variants.push({
            label: 'Translation',
            tokens: translationTokens,
            revealedCount: translationTokens.length,
            currentIndex: translationTokens.length - 1,
            baseClass: 'translation',
          });
        }

        return {
          id: `chunk-sentence-${index}`,
          index: index,
          sentenceNumber: metadata.sentence_number ?? index + 1,
          state: index === 0 ? 'active' : 'future',
          variants,
        };
      });

      const filtered = fallbackFromChunk.filter((sentence) => sentence.variants.length > 0);
      if (filtered.length > 0) {
        const active =
          filtered.find((sentence) => sentence.index === activeSentenceIndex) ?? filtered[0];
        return forceActive(active);
      }
    }

    if (rawSentences.length === 0) {
      return null;
    }

    const fallbackFromContent: TextPlayerSentence[] = rawSentences
      .map((sentence, position) => {
        const originalTokens = buildTokens(sentence.text);
        const translationTokens = buildTokens(sentence.translation);
        const transliterationTokens = buildTokens(sentence.transliteration);

        const variants: TextPlayerVariantDisplay[] = [];
        if (originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (translationTokens.length > 0) {
          variants.push({
            label: 'Translation',
            tokens: translationTokens,
            revealedCount: translationTokens.length,
            currentIndex: translationTokens.length - 1,
            baseClass: 'translation',
          });
        }

        if (variants.length === 0) {
          return null;
        }

        return {
          id: `sentence-${sentence.index}`,
          index: sentence.index,
          sentenceNumber: sentence.index + 1,
          state: position === 0 ? 'active' : 'future',
          variants,
        } as TextPlayerSentence;
      })
      .filter((value): value is TextPlayerSentence => value !== null);

    if (fallbackFromContent.length === 0) {
      return null;
    }
    const active =
      fallbackFromContent.find((sentence) => sentence.index === activeSentenceIndex) ??
      fallbackFromContent[0];
    return forceActive(active);
  }, [timelineDisplay, chunk?.sentences, rawSentences, activeSentenceIndex]);
  const sentenceWeightSummary = useMemo(() => {
    let cumulativeTotal = 0;
    const cumulative: number[] = [];
    rawSentences.forEach((sentence) => {
      cumulativeTotal += sentence.weight;
      cumulative.push(cumulativeTotal);
    });
    return {
      cumulative,
      total: cumulativeTotal,
    };
  }, [rawSentences]);
  const totalSentences = useMemo(
    () => paragraphs.reduce((count, paragraph) => count + paragraph.sentences.length, 0),
    [paragraphs],
  );

  const effectiveAudioUrl = useMemo(() => {
    const combinedUrl = audioTracks?.orig_trans?.url ?? null;
    const translationUrl = audioTracks?.translation?.url ?? audioTracks?.trans?.url ?? null;
    if (originalAudioEnabled && combinedUrl) {
      return combinedUrl;
    }
    if (activeAudioUrl) {
      return activeAudioUrl;
    }
    if (translationUrl) {
      return translationUrl;
    }
    if (combinedUrl) {
      return combinedUrl;
    }
    return null;
  }, [activeAudioUrl, audioTracks, originalAudioEnabled]);

  const resolvedAudioUrl = useMemo(
    () => (effectiveAudioUrl ? appendAccessToken(effectiveAudioUrl) : null),
    [effectiveAudioUrl],
  );
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
      (track): track is TrackTimingPayload => Boolean(track && track.chunkId === chunkId)
    );
    return matches.length > 0 ? matches : wordSyncTracks.filter((track): track is TrackTimingPayload => Boolean(track));
  }, [chunk?.chunkId, wordSyncTracks]);
  const wordSyncPreferredTypes = useMemo(() => {
    const preferences: TrackTimingPayload['trackType'][] = [];
    const combinedUrl = audioTracks?.orig_trans?.url ?? null;
    const preferred =
      originalAudioEnabled && combinedUrl && effectiveAudioUrl === combinedUrl
        ? 'original_translated'
        : 'translated';
    preferences.push(preferred);
    if (!preferences.includes('translated')) {
      preferences.push('translated');
    }
    if (!preferences.includes('original_translated')) {
      preferences.push('original_translated');
    }
    return preferences;
  }, [audioTracks, effectiveAudioUrl, originalAudioEnabled]);
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
    return buildTimingPayloadFromJobTiming(jobTimingResponse, activeTimingTrack);
  }, [activeTimingTrack, hasRemoteTiming, jobTimingResponse]);

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

  useEffect(() => {
    gateListRef.current = buildSentenceGateList(timingPayload);
    timingStore.setActiveGate(null);
  }, [timingPayload]);

  useEffect(() => {
    if (!jobId || !timingPayload) {
      diagnosticsSignatureRef.current = null;
      return;
    }
    const signature = [
      jobId,
      timingPayload.trackKind,
      String(timingPayload.segments.length),
      activeTimingTrack,
      jobTimingResponse?.highlighting_policy ?? 'unknown',
    ].join('|');
    if (diagnosticsSignatureRef.current === signature) {
      return;
    }
    diagnosticsSignatureRef.current = signature;
    if (!timingPayload.segments.length) {
      return;
    }
    const policy =
      typeof jobTimingResponse?.highlighting_policy === 'string' &&
      jobTimingResponse.highlighting_policy.trim()
        ? jobTimingResponse.highlighting_policy.trim()
        : null;
    const metrics = computeTimingMetrics(timingPayload, timingPayload.playbackRate);
    if (import.meta.env.DEV) {
      console.info('[Highlight diagnostics]', {
        jobId,
        trackKind: timingPayload.trackKind,
        policy: policy ?? 'unknown',
        avgTokenMs: Number(metrics.avgTokenMs.toFixed(2)),
        tempoRatio: Number(metrics.tempoRatio.toFixed(3)),
        uniformVsRealMeanDeltaMs: Number(metrics.uniformVsRealMeanDeltaMs.toFixed(2)),
        totalDriftMs: Number(metrics.totalDriftMs.toFixed(2)),
        track: activeTimingTrack,
      });
    }
  }, [jobId, timingPayload, activeTimingTrack, jobTimingResponse]);
  const registerTokenElement = useCallback((id: string, element: HTMLSpanElement | null) => {
    const map = tokenElementsRef.current;
    if (!element) {
      map.delete(id);
      return;
    }
    map.set(id, element);
  }, []);
  const registerSentenceElement = useCallback((sentenceId: number, element: HTMLDivElement | null) => {
    const map = sentenceElementsRef.current;
    if (!element) {
      map.delete(sentenceId);
      return;
    }
    map.set(sentenceId, element);
  }, []);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      wordSyncControllerRef.current = null;
      return;
    }
    const controller = createWordSyncController({
      containerRef,
      tokenElementsRef,
      sentenceElementsRef,
      clockRef,
      config: WORD_SYNC,
      followHighlight: followHighlightEnabled,
      isPaused: () => {
        const element = audioRef.current;
        return !element || element.paused;
      },
      debugOverlay: { policyRef: highlightPolicyRef },
    });
    wordSyncControllerRef.current = controller;
    return () => {
      controller.destroy();
      wordSyncControllerRef.current = null;
    };
  }, [clockRef, containerRef, followHighlightEnabled, legacyWordSyncEnabled]);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      return;
    }
    wordSyncControllerRef.current?.setFollowHighlight(followHighlightEnabled);
  }, [followHighlightEnabled, legacyWordSyncEnabled]);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      return;
    }
    const controller = wordSyncControllerRef.current;
    if (!controller) {
      return;
    }
    if (!shouldUseWordSync || !activeWordSyncTrack || !activeWordIndex) {
      controller.stop();
      controller.setTrack(null, null);
      return;
    }
    controller.setTrack(activeWordSyncTrack, activeWordIndex);
    controller.snap();
    const element = audioRef.current;
    if (element && !element.paused) {
      controller.start();
    }
    return () => {
      controller.stop();
    };
  }, [activeWordIndex, activeWordSyncTrack, shouldUseWordSync, legacyWordSyncEnabled]);
  useEffect(() => {
    const clearTiming = () => {
      timingStore.setPayload(EMPTY_TIMING_PAYLOAD);
      timingStore.setLast(null);
    };
    if (!shouldUseWordSync || !timingPayload) {
      clearTiming();
      return clearTiming;
    }
    timingStore.setPayload(timingPayload);
    timingStore.setLast(null);
    return clearTiming;
  }, [shouldUseWordSync, timingPayload]);
  useEffect(() => {
    if (!shouldUseWordSync || !timingPayload) {
      return;
    }
    timingStore.setRate(effectivePlaybackRate);
  }, [effectivePlaybackRate, shouldUseWordSync, timingPayload]);
  useEffect(() => {
    if (!playerCore || !shouldUseWordSync || !timingPayload) {
      stopAudioSync();
      return () => {
        stopAudioSync();
      };
    }
    startAudioSync(playerCore);
    return () => {
      stopAudioSync();
    };
  }, [playerCore, shouldUseWordSync, timingPayload]);
  useEffect(() => {
    if (!playerCore) {
      return;
    }
    playerCore.setRate(effectivePlaybackRate);
  }, [effectivePlaybackRate, playerCore]);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      tokenElementsRef.current.clear();
      sentenceElementsRef.current.clear();
      return;
    }
    if (shouldUseWordSync) {
      return;
    }
    tokenElementsRef.current.forEach((element) => {
      element.classList.remove('is-active');
      element.classList.remove('is-visited');
    });
    tokenElementsRef.current.clear();
    sentenceElementsRef.current.clear();
  }, [legacyWordSyncEnabled, shouldUseWordSync]);
  useEffect(() => {
    if (!legacyWordSyncEnabled || !shouldUseWordSync) {
      return;
    }
    const controller = wordSyncControllerRef.current;
    if (!controller) {
      return;
    }
    if (typeof window === 'undefined') {
      controller.snap();
      return;
    }
    const handle = window.requestAnimationFrame(() => {
      controller.snap();
    });
    return () => {
      window.cancelAnimationFrame(handle);
    };
  }, [legacyWordSyncEnabled, shouldUseWordSync, wordSyncSentences]);

  useEffect(() => {
    if (!onRegisterInlineAudioControls) {
      if (!effectiveAudioUrl) {
        onInlineAudioPlaybackStateChange?.('paused');
      }
      return;
    }
    if (!effectiveAudioUrl) {
      onRegisterInlineAudioControls(null);
      onInlineAudioPlaybackStateChange?.('paused');
      return () => {
        onRegisterInlineAudioControls(null);
      };
    }
    const pauseHandler = () => {
      const element = audioRef.current;
      if (!element) {
        return;
      }
      try {
        element.pause();
      } catch (error) {
        // Ignore pause failures triggered by browsers blocking programmatic control.
      }
      onInlineAudioPlaybackStateChange?.('paused');
    };
    const playHandler = () => {
      const element = audioRef.current;
      if (!element) {
        return;
      }
      try {
        const result = element.play();
        onInlineAudioPlaybackStateChange?.('playing');
        if (result && typeof result.catch === 'function') {
          result.catch(() => {
            onInlineAudioPlaybackStateChange?.('paused');
          });
        }
      } catch (error) {
        // Swallow play failures caused by autoplay restrictions.
        onInlineAudioPlaybackStateChange?.('paused');
      }
    };
    onRegisterInlineAudioControls({ pause: pauseHandler, play: playHandler });
    return () => {
      onRegisterInlineAudioControls(null);
    };
  }, [effectiveAudioUrl, onInlineAudioPlaybackStateChange, onRegisterInlineAudioControls]);
  const pendingInitialSeek = useRef<number | null>(null);
  const lastReportedPosition = useRef(0);

  useEffect(() => {
    if (!hasTimeline) {
      return;
    }
    setChunkTime(0);
    setActiveSentenceIndex(0);
  }, [hasTimeline, chunk?.chunkId, chunk?.rangeFragment, chunk?.startSentence, chunk?.endSentence]);

  useEffect(() => {
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
  }, [content, totalSentences]);

  useEffect(() => {
    if (!timelineDisplay) {
      return;
    }
    const { activeIndex: candidateIndex, effectiveTime } = timelineDisplay;
    if (candidateIndex === activeSentenceIndex) {
      return;
    }
    if (!timelineSentences || timelineSentences.length === 0) {
      setActiveSentenceIndex(candidateIndex);
      return;
    }
    const epsilon = 0.05;
    const clampedIndex = Math.max(0, Math.min(candidateIndex, timelineSentences.length - 1));
    const candidateRuntime = timelineSentences[clampedIndex];
    if (!candidateRuntime) {
      setActiveSentenceIndex(clampedIndex);
      return;
    }
    if (clampedIndex > activeSentenceIndex) {
      if (effectiveTime < candidateRuntime.startTime + epsilon) {
        return;
      }
    } else if (clampedIndex < activeSentenceIndex) {
      if (effectiveTime > candidateRuntime.endTime - epsilon) {
        return;
      }
    }
    setActiveSentenceIndex(clampedIndex);
  }, [timelineDisplay, activeSentenceIndex, timelineSentences]);

  useEffect(() => {
    if (!effectiveAudioUrl) {
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      setActiveSentenceIndex(0);
      setActiveSentenceProgress(0);
      setAudioDuration(null);
      return;
    }
    const stored = getStoredAudioPosition?.(effectiveAudioUrl);
    if (typeof stored === 'number' && stored > 0) {
      pendingInitialSeek.current = stored;
    } else {
      pendingInitialSeek.current = null;
    }
    lastReportedPosition.current = typeof stored === 'number' ? stored : 0;
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    setAudioDuration(null);
  }, [effectiveAudioUrl, getStoredAudioPosition]);

  const handleScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      onScroll?.(event);
    },
    [onScroll],
  );

  const exitFullscreen = useCallback(() => {
    if (typeof document === 'undefined') {
      return;
    }
    if (typeof document.exitFullscreen === 'function') {
      const exitResult = document.exitFullscreen();
      if (exitResult && typeof exitResult.catch === 'function') {
        exitResult.catch(() => undefined);
      }
    }
    fullscreenRequestedRef.current = false;
    fullscreenResyncPendingRef.current = false;
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }
    const element = rootRef.current;
    if (!element) {
      return;
    }

    if (isFullscreen) {
      requestFullscreenIfNeeded();
      return () => {
        exitFullscreen();
      };
    }

    if (document.fullscreenElement === element || fullscreenRequestedRef.current) {
      exitFullscreen();
    } else {
      fullscreenRequestedRef.current = false;
    }
    return;
  }, [exitFullscreen, isFullscreen, requestFullscreenIfNeeded]);

  useEffect(() => {
    if (!isFullscreen) {
      return;
    }
    fullscreenResyncPendingRef.current = true;
    requestFullscreenIfNeeded();
  }, [fullscreenResyncToken, isFullscreen, requestFullscreenIfNeeded]);

  useEffect(() => {
    if (!isFullscreen || typeof document === 'undefined') {
      return;
    }
    const element = rootRef.current;
    if (!element) {
      return;
    }
    const handleFullscreenChange = () => {
      if (document.fullscreenElement === element) {
        fullscreenRequestedRef.current = false;
        fullscreenResyncPendingRef.current = false;
        return;
      }
      fullscreenRequestedRef.current = false;
      if (isFullscreen && fullscreenResyncPendingRef.current) {
        fullscreenResyncPendingRef.current = false;
        requestFullscreenIfNeeded();
        return;
      }
      fullscreenResyncPendingRef.current = false;
      onRequestExitFullscreen?.();
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [isFullscreen, onRequestExitFullscreen, requestFullscreenIfNeeded]);

  useEffect(() => {
    if (!resolvedAudioUrl) {
      return;
    }
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const attempt = element.play();
    if (attempt && typeof attempt.catch === 'function') {
      attempt.catch(() => {
        /* Ignore autoplay restrictions */
      });
    }
  }, [resolvedAudioUrl]);

  const emitAudioProgress = useCallback(
    (position: number) => {
      if (!effectiveAudioUrl || !onAudioProgress) {
        return;
      }
      if (Math.abs(position - lastReportedPosition.current) < 0.25) {
        return;
      }
      lastReportedPosition.current = position;
      onAudioProgress(effectiveAudioUrl, position);
    },
    [effectiveAudioUrl, onAudioProgress],
  );

  const updateSentenceForTime = useCallback(
    (time: number, duration: number) => {
      const totalWeight = sentenceWeightSummary.total;
      if (totalWeight <= 0 || duration <= 0 || rawSentences.length === 0) {
        setActiveSentenceIndex(0);
        setActiveSentenceProgress(0);
        return;
      }

      const progress = Math.max(0, Math.min(time / duration, 0.9999));
      const targetUnits = progress * totalWeight;
      const cumulative = sentenceWeightSummary.cumulative;

      let sentencePosition = cumulative.findIndex((value) => targetUnits < value);
      if (sentencePosition === -1) {
        sentencePosition = rawSentences.length - 1;
      }

      const sentence = rawSentences[sentencePosition];
      const sentenceStartUnits = sentencePosition === 0 ? 0 : cumulative[sentencePosition - 1];
      const sentenceWeight = Math.max(sentence.weight, 1);
      const intraUnits = targetUnits - sentenceStartUnits;
      const intra = Math.max(0, Math.min(intraUnits / sentenceWeight, 1));

      setActiveSentenceIndex(sentence.index);
      setActiveSentenceProgress(intra);
    },
    [rawSentences, sentenceWeightSummary],
  );

  const updateActiveGateFromTime = useCallback((mediaTime: number) => {
    const gates = gateListRef.current;
    if (!gates.length) {
      timingStore.setActiveGate(null);
      return;
    }
    let candidate: SentenceGate | null = null;
    for (const gate of gates) {
      if (mediaTime >= gate.start && mediaTime <= gate.end) {
        candidate = gate;
        break;
      }
      if (mediaTime < gate.start) {
        candidate = gate;
        break;
      }
    }
    timingStore.setActiveGate(candidate);
  }, []);

  const handleInlineAudioPlay = useCallback(() => {
    timingStore.setLast(null);
    const startPlayback = () => {
      wordSyncControllerRef.current?.handlePlay();
      onInlineAudioPlaybackStateChange?.('playing');
    };
    const element = audioRef.current;
    if (!element) {
      startPlayback();
      return;
    }
    const scheduleStart = () => {
      if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
        window.requestAnimationFrame(startPlayback);
      } else {
        startPlayback();
      }
    };
    if (element.readyState >= element.HAVE_CURRENT_DATA) {
      scheduleStart();
      return;
    }
    const handleCanPlay = () => {
      element.removeEventListener('canplay', handleCanPlay);
      scheduleStart();
    };
    element.addEventListener('canplay', handleCanPlay, { once: true });
  }, [onInlineAudioPlaybackStateChange]);

  const handleInlineAudioPause = useCallback(() => {
    wordSyncControllerRef.current?.handlePause();
    onInlineAudioPlaybackStateChange?.('paused');
  }, [onInlineAudioPlaybackStateChange]);

  const handleAudioSeeking = useCallback(() => {
    wordSyncControllerRef.current?.handleSeeking();
  }, []);

  const handleAudioWaiting = useCallback(() => {
    wordSyncControllerRef.current?.handleWaiting();
  }, []);

  const handleAudioStalled = useCallback(() => {
    wordSyncControllerRef.current?.handleWaiting();
  }, []);

  const handleAudioPlaying = useCallback(() => {
    wordSyncControllerRef.current?.handlePlaying();
  }, []);

  const handleAudioRateChange = useCallback(() => {
    wordSyncControllerRef.current?.handleRateChange();
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const duration = element.duration;
    if (Number.isFinite(duration) && duration > 0) {
      setAudioDuration(duration);
    } else {
      setAudioDuration(null);
    }
    setChunkTime(element.currentTime ?? 0);
    const seek = pendingInitialSeek.current;
    if (typeof seek === 'number' && seek > 0 && Number.isFinite(duration) && duration > 0) {
      const clamped = Math.min(seek, duration - 0.1);
      element.currentTime = clamped;
      updateSentenceForTime(clamped, duration);
      updateActiveGateFromTime(clamped);
      emitAudioProgress(clamped);
      const maybePlay = element.play?.();
      if (maybePlay && typeof maybePlay.catch === 'function') {
        maybePlay.catch(() => undefined);
      }
      pendingInitialSeek.current = null;
      wordSyncControllerRef.current?.snap();
      return;
    }
    pendingInitialSeek.current = null;
    updateActiveGateFromTime(element.currentTime ?? 0);
    wordSyncControllerRef.current?.snap();
  }, [emitAudioProgress, updateSentenceForTime, updateActiveGateFromTime]);

  const handleTimeUpdate = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const { currentTime, duration } = element;
    if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
      return;
    }
    setAudioDuration((existing) => (existing && Math.abs(existing - duration) < 0.01 ? existing : duration));
    setChunkTime(currentTime);
    if (!hasTimeline) {
      updateSentenceForTime(currentTime, duration);
    }
    emitAudioProgress(currentTime);
    updateActiveGateFromTime(currentTime);
    if (element.paused) {
      wordSyncControllerRef.current?.snap();
    }
  }, [emitAudioProgress, hasTimeline, updateSentenceForTime, updateActiveGateFromTime]);

  const handleAudioEnded = useCallback(() => {
    wordSyncControllerRef.current?.stop();
    onInlineAudioPlaybackStateChange?.('paused');
    if (hasTimeline && timelineDisplay) {
      setChunkTime((prev) => (audioDuration ? audioDuration : prev));
      setActiveSentenceIndex(timelineDisplay.activeIndex);
    } else {
      if (totalSentences > 0) {
        setActiveSentenceIndex(totalSentences - 1);
        setActiveSentenceProgress(1);
      }
    }
    emitAudioProgress(0);
    onRequestAdvanceChunk?.();
  }, [
    audioDuration,
    emitAudioProgress,
    hasTimeline,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    timelineDisplay,
    totalSentences,
  ]);

  const handleAudioSeeked = useCallback(() => {
    wordSyncControllerRef.current?.handleSeeked();
    const element = audioRef.current;
    if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
      return;
    }
    setChunkTime(element.currentTime ?? 0);
    if (!hasTimeline) {
      updateSentenceForTime(element.currentTime, element.duration);
    }
    emitAudioProgress(element.currentTime);
  }, [emitAudioProgress, hasTimeline, updateSentenceForTime]);
  const handleTokenSeek = useCallback(
    (time: number) => {
      const element = audioRef.current;
      if (!element || !Number.isFinite(time)) {
        return;
      }
      try {
        wordSyncControllerRef.current?.handleSeeking();
        const target = Math.max(0, Math.min(time, Number.isFinite(element.duration) ? element.duration : time));
        element.currentTime = target;
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      } catch (error) {
        // Ignore seek failures in restricted environments.
      }
    },
    [],
  );

  const [fullscreenControlsCollapsed, setFullscreenControlsCollapsed] = useState(false);
  const wasFullscreenRef = useRef<boolean>(false);
  useEffect(() => {
    if (!isFullscreen) {
      setFullscreenControlsCollapsed(false);
      wasFullscreenRef.current = false;
      return;
    }
    if (!wasFullscreenRef.current) {
      setFullscreenControlsCollapsed(true);
      wasFullscreenRef.current = true;
    }
  }, [isFullscreen]);
  useEffect(() => {
    if (!isFullscreen) {
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
        !event.shiftKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      if (event.key?.toLowerCase() === 'h') {
        setFullscreenControlsCollapsed((value) => !value);
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, [isFullscreen]);

  const rootClassName = [
    'player-panel__interactive',
    isFullscreen ? 'player-panel__interactive--fullscreen' : null,
  ]
    .filter(Boolean)
    .join(' ');

  const overlayAudioEl = playerCore?.getElement() ?? audioRef.current ?? null;
  const renderInlineAudioSection = (collapsed: boolean): ReactNode => {
    if (resolvedAudioUrl) {
      return (
        <div
          className={[
            'player-panel__interactive-audio',
            collapsed ? 'player-panel__interactive-audio--collapsed' : null,
          ]
            .filter(Boolean)
            .join(' ')}
          aria-hidden={collapsed ? 'true' : undefined}
        >
          <span className="player-panel__interactive-label">Synchronized audio</span>
          <div className="player-panel__interactive-audio-controls">
            <PlayerCore
              key={resolvedAudioUrl ?? 'inline-audio'}
              ref={attachPlayerCore}
              mediaRef={attachMediaElement}
              src={resolvedAudioUrl ?? undefined}
              id="main-audio"
              controls
              preload="metadata"
              autoPlay
              onPlay={handleInlineAudioPlay}
              onPause={handleInlineAudioPause}
              onLoadedMetadata={handleLoadedMetadata}
              onTimeUpdate={handleTimeUpdate}
              onEnded={handleAudioEnded}
              onSeeked={handleAudioSeeked}
              onSeeking={handleAudioSeeking}
              onWaiting={handleAudioWaiting}
              onStalled={handleAudioStalled}
              onPlaying={handleAudioPlaying}
              onRateChange={handleAudioRateChange}
            />
          </div>
        </div>
      );
    }
    if (noAudioAvailable) {
      return (
        <div className="player-panel__interactive-no-audio" role="status">
          Matching audio has not been generated for this selection yet.
        </div>
      );
    }
    return null;
  };
  const inlineAudioAvailable = Boolean(resolvedAudioUrl || noAudioAvailable);

  const hasFullscreenPanelContent = Boolean(fullscreenControls) || inlineAudioAvailable;
  const slideIndicator = useMemo(() => {
    if (!chunk) {
      return null;
    }
    const start =
      typeof chunk.startSentence === 'number' && Number.isFinite(chunk.startSentence)
        ? Math.max(chunk.startSentence, 1)
        : null;
    const current =
      start !== null ? start + Math.max(activeSentenceIndex, 0) : null;
    const totalFromProp =
      typeof totalSentencesInBook === 'number' && Number.isFinite(totalSentencesInBook)
        ? Math.max(totalSentencesInBook, 1)
        : null;
    const chunkEnd =
      typeof chunk.endSentence === 'number' && Number.isFinite(chunk.endSentence)
        ? Math.max(chunk.endSentence, start ?? 1)
        : null;
    const total = totalFromProp ?? chunkEnd;
    if (current === null || total === null) {
      return null;
    }
    return {
      current: Math.min(current, total),
      total,
    };
  }, [activeSentenceIndex, chunk, totalSentencesInBook]);

  return (
    <>
      <div
        ref={rootRef}
        className={rootClassName}
        data-fullscreen={isFullscreen ? 'true' : 'false'}
        data-original-enabled={originalAudioEnabled ? 'true' : 'false'}
      >
      {isFullscreen && hasFullscreenPanelContent ? (
        <div
          className={[
            'player-panel__interactive-fullscreen-controls',
            fullscreenControlsCollapsed ? 'player-panel__interactive-fullscreen-controls--collapsed' : null,
          ]
            .filter(Boolean)
            .join(' ')}
        >
          <div className="player-panel__interactive-fullscreen-controls-bar">
            <span className="player-panel__interactive-label">
              {fullscreenControlsCollapsed ? 'Controls hidden' : 'Controls'}
            </span>
            <div className="player-panel__interactive-fullscreen-controls-actions">
              {inlineAudioAvailable && fullscreenControlsCollapsed ? (
                <button
                  type="button"
                  className="player-panel__interactive-fullscreen-toggle-btn player-panel__interactive-fullscreen-toggle-btn--audio"
                  onClick={() => setFullscreenControlsCollapsed(false)}
                >
                  Show audio player
                </button>
              ) : null}
              <button
                type="button"
                className="player-panel__interactive-fullscreen-toggle-btn"
                onClick={() => setFullscreenControlsCollapsed((value) => !value)}
                aria-expanded={!fullscreenControlsCollapsed}
              >
                {fullscreenControlsCollapsed ? 'Show controls' : 'Hide controls'}
              </button>
            </div>
          </div>
          {!fullscreenControlsCollapsed ? (
            <>
              {fullscreenControls ? (
                <div className="player-panel__interactive-fullscreen-controls-body">{fullscreenControls}</div>
              ) : null}
              {renderInlineAudioSection(false)}
            </>
          ) : (
            renderInlineAudioSection(true)
          )}
        </div>
      ) : (
        renderInlineAudioSection(false)
      )}
      <div
        ref={containerRef}
        className="player-panel__document-body player-panel__interactive-body"
        data-testid="player-panel-document"
        onScroll={handleScroll}
        style={bodyStyle}
      >
        {showBookBadge ? (
          <div className="player-panel__interactive-book-badge">
            {resolvedBookCoverUrl ? (
              <img
                src={resolvedBookCoverUrl}
                alt={bookBadgeAltText}
                onError={() => setViewportCoverFailed(true)}
                loading="lazy"
              />
            ) : null}
            {safeBookTitle ? (
              <span className="player-panel__interactive-book-badge-title">{safeBookTitle}</span>
            ) : null}
          </div>
        ) : null}
        {slideIndicator ? (
          <div className="player-panel__interactive-slide-indicator">
            {slideIndicator.current}/{slideIndicator.total}
          </div>
        ) : null}
        {legacyWordSyncEnabled && shouldUseWordSync && wordSyncSentences && wordSyncSentences.length > 0 ? null : textPlayerSentences && textPlayerSentences.length > 0 ? (
          <TextPlayer sentences={textPlayerSentences} onSeek={handleTokenSeek} />
        ) : paragraphs.length > 0 ? (
          <pre className="player-panel__document-text">{content}</pre>
        ) : chunk ? (
          <div className="player-panel__document-status" role="status">
            Loading interactive chunk…
          </div>
        ) : (
          <div className="player-panel__document-status" role="status">
            Text preview will appear once generated.
          </div>
        )}
      </div>
    </div>
    <DebugOverlay audioEl={overlayAudioEl} />
    </>
  );
});

function createNoopWordSyncController(): WordSyncController {
  const noop = () => {
    /* no-op */
  };
  return {
    setTrack: noop,
    start: noop,
    stop: noop,
    destroy: noop,
    snap: noop,
    handleSeeking: noop,
    handleSeeked: noop,
    handleWaiting: noop,
    handlePlaying: noop,
    handleRateChange: noop,
    handlePause: noop,
    handlePlay: noop,
    setFollowHighlight: noop,
  };
}

function createWordSyncController(options: {
  containerRef: MutableRefObject<HTMLDivElement | null>;
  tokenElementsRef: MutableRefObject<Map<string, HTMLElement>>;
  sentenceElementsRef: MutableRefObject<Map<number, HTMLElement>>;
  clockRef: MutableRefObject<MediaClock>;
  config: typeof WORD_SYNC;
  followHighlight: boolean;
  isPaused: () => boolean;
  debugOverlay?: {
    policyRef: MutableRefObject<string | null>;
  };
}): WordSyncController {
  if (typeof window === 'undefined') {
    return createNoopWordSyncController();
  }

  const {
    containerRef,
    tokenElementsRef,
    sentenceElementsRef,
    clockRef,
    config,
  } = options;
  const overlayPolicyRef = options.debugOverlay?.policyRef;
  let overlayActiveId: string | null = null;

  const isOverlayEnabled = () => {
    if (typeof window === 'undefined') {
      return false;
    }
    const dbgWindow = window as HighlightDebugWindow;
    return Boolean(dbgWindow.__HL_DEBUG__?.overlay);
  };

  const overlayPalette: Record<string, { bg: string; fg: string }> = {
    forced: { bg: 'rgba(20,90,50,0.92)', fg: '#e8ffec' },
    estimated_punct: { bg: 'rgba(219,165,23,0.95)', fg: '#221a00' },
    inferred: { bg: 'rgba(185,60,50,0.95)', fg: '#fff' },
    retry_failed_align: { bg: 'rgba(133,20,75,0.95)', fg: '#fff' },
    default: { bg: 'rgba(45,45,45,0.92)', fg: '#f4f4f4' },
  };

  const overlayController = (() => {
    if (typeof document === 'undefined') {
      return null;
    }
    let element: HTMLDivElement | null = null;
    const ensure = () => {
      if (!element) {
        element = document.createElement('div');
        element.id = 'hl-token-overlay';
        element.style.cssText =
          'position:absolute;pointer-events:none;padding:4px 8px;border-radius:4px;font:12px/1.3 monospace;' +
          'background:rgba(0,0,0,0.85);color:#fff;z-index:99999;opacity:0;transition:opacity 0.12s ease;';
        document.body.appendChild(element);
      }
      return element;
    };
    const hide = () => {
      if (element) {
        element.style.opacity = '0';
      }
    };
    const destroy = () => {
      if (element && element.parentNode) {
        element.parentNode.removeChild(element);
      }
      element = null;
    };
    return { ensure, hide, destroy };
  })();

  const hideOverlay = () => {
    overlayActiveId = null;
    overlayController?.hide();
  };

  const showOverlayForWord = (word: WordTiming, anchor: HTMLElement) => {
    if (!overlayController || !overlayPolicyRef || !track || !isOverlayEnabled()) {
      hideOverlay();
      return;
    }
    const policy = overlayPolicyRef.current;
    const now = clockRef.current.effectiveTime(track);
    if (!Number.isFinite(now)) {
      hideOverlay();
      return;
    }
    const driftMs = ((now - (word.t0 ?? 0)) * 1000);
    if (!Number.isFinite(driftMs)) {
      hideOverlay();
      return;
    }
    const element = overlayController.ensure();
    const palette = overlayPalette[policy?.toLowerCase() ?? ''] ?? overlayPalette.default;
    element.style.background = palette.bg;
    element.style.color = palette.fg;
    element.textContent = `${word.text} | ${policy ?? 'unknown'} | drift ${driftMs.toFixed(1)}ms`;
    const rect = anchor.getBoundingClientRect();
    const scrollX = typeof window !== 'undefined' ? window.scrollX ?? window.pageXOffset ?? 0 : 0;
    const scrollY = typeof window !== 'undefined' ? window.scrollY ?? window.pageYOffset ?? 0 : 0;
    element.style.left = `${rect.left + scrollX}px`;
    const top = rect.top + scrollY - element.offsetHeight - 8;
    element.style.top = `${top < scrollY ? scrollY : top}px`;
    element.style.opacity = '1';
    overlayActiveId = word.id;
  };

  let followHighlights = options.followHighlight;
  let track: TrackTimingPayload | null = null;
  let index: WordIndex | null = null;
  const activeIds = new Set<string>();
  let cursor = 0;
  let rafId: number | null = null;
  let seekTimeoutId: number | null = null;
  let seeking = false;
  let stalled = false;
  let lastApplied = Number.NaN;
  let lastFollowedSentence: number | null = null;

  const clearSeekTimeout = () => {
    if (seekTimeoutId !== null) {
      window.clearTimeout(seekTimeoutId);
      seekTimeoutId = null;
    }
  };

  const clearFrame = () => {
    if (rafId !== null) {
      window.cancelAnimationFrame(rafId);
      rafId = null;
    }
  };

  const deactivateToken = (id: string, markVisited: boolean) => {
    const element = tokenElementsRef.current.get(id);
    if (!element) {
      return;
    }
    element.classList.remove('is-active');
    if (markVisited) {
      element.classList.add('is-visited');
    }
    if (overlayActiveId === id) {
      hideOverlay();
    }
  };

  const activateToken = (id: string) => {
    const element = tokenElementsRef.current.get(id);
    if (!element) {
      return;
    }
    element.classList.add('is-active');
    element.classList.remove('is-visited');
    if (overlayPolicyRef && track && index) {
      const word = index.byId.get(id);
      if (word) {
        showOverlayForWord(word, element);
      }
    }
  };

  const clearActive = () => {
    hideOverlay();
    activeIds.forEach((activeId) => {
      const element = tokenElementsRef.current.get(activeId);
      if (element) {
        element.classList.remove('is-active');
      }
    });
    tokenElementsRef.current.forEach((element) => {
      element.classList.remove('is-active');
      element.classList.remove('is-visited');
    });
    activeIds.clear();
    lastFollowedSentence = null;
  };

  const followSentence = (word: WordTiming) => {
    if (!followHighlights || !index) {
      return;
    }
    const ids = index.bySentence.get(word.sentenceId);
    if (!ids || ids[0] !== word.id) {
      return;
    }
    if (lastFollowedSentence === word.sentenceId) {
      return;
    }
    lastFollowedSentence = word.sentenceId;
    const sentenceElement = sentenceElementsRef.current.get(word.sentenceId);
    const container = containerRef.current;
    if (!sentenceElement || !container) {
      return;
    }
    const containerRect = container.getBoundingClientRect();
    const sentenceRect = sentenceElement.getBoundingClientRect();
    if (
      sentenceRect.top >= containerRect.top &&
      sentenceRect.bottom <= containerRect.bottom
    ) {
      return;
    }
    try {
      sentenceElement.scrollIntoView({
        block: 'center',
        inline: 'nearest',
        behavior: followHighlights ? 'smooth' : 'auto',
      });
    } catch {
      // Ignore scroll failures; container may be detached.
    }
  };

  const snapToTime = (time: number) => {
    if (!index || !track) {
      clearActive();
      cursor = 0;
      lastApplied = Number.NaN;
      return;
    }
    const currentIndex = index;
    const activeNow = collectActiveWordIds(currentIndex, time);
    const targetSet = new Set(activeNow);
    activeIds.forEach((id) => {
      if (!targetSet.has(id)) {
        activeIds.delete(id);
        deactivateToken(id, false);
      }
    });
    activeNow.forEach((id) => {
      if (!activeIds.has(id)) {
        activeIds.add(id);
        activateToken(id);
        const word = currentIndex.byId.get(id);
        if (word) {
          followSentence(word);
        }
      }
    });
    cursor = lowerBound(currentIndex.events, time);
    lastApplied = time;
  };

  const applyEvent = (event: { kind: 'on' | 'off'; id: string; t: number }) => {
    const currentIndex = index;
    if (!currentIndex) {
      return;
    }
    if (event.kind === 'on') {
      if (activeIds.has(event.id)) {
        return;
      }
      activeIds.add(event.id);
      activateToken(event.id);
      const word = currentIndex.byId.get(event.id);
      if (word) {
        followSentence(word);
      }
    } else {
      if (!activeIds.has(event.id)) {
        deactivateToken(event.id, false);
        return;
      }
      activeIds.delete(event.id);
      deactivateToken(event.id, true);
    }
  };

  const processDueEvents = (time: number) => {
    if (!index) {
      return;
    }
    const { events } = index;
    let localCursor = cursor;
    const budgetOrigin = typeof performance !== 'undefined' ? performance.now() : null;
    while (localCursor < events.length) {
      const event = events[localCursor];
      const delta = (event.t - time) * 1000;
      if (delta > config.HYSTERESIS_MS) {
        break;
      }
      applyEvent(event);
      localCursor += 1;
      lastApplied = event.t;
      if (
        budgetOrigin !== null &&
        typeof performance !== 'undefined' &&
        performance.now() - budgetOrigin >= config.RA_FRAME_BUDGET_MS
      ) {
        break;
      }
    }
    cursor = localCursor;
  };

  const step = () => {
    rafId = null;
    if (!track || !index) {
      return;
    }
    if (seeking || stalled) {
      rafId = window.requestAnimationFrame(step);
      return;
    }
    const effective = clockRef.current.effectiveTime(track);
    if (!Number.isFinite(lastApplied)) {
      snapToTime(effective);
    } else if (Math.abs((effective - lastApplied) * 1000) > config.MAX_LAG_MS) {
      snapToTime(effective);
    } else {
      processDueEvents(effective);
    }
    rafId = window.requestAnimationFrame(step);
  };

  const start = () => {
    if (!track || !index) {
      return;
    }
    if (rafId === null) {
      rafId = window.requestAnimationFrame(step);
    }
  };

  const stop = () => {
    clearFrame();
  };

  const destroy = () => {
    clearFrame();
    clearSeekTimeout();
    clearActive();
    track = null;
    index = null;
    overlayController?.destroy();
    overlayActiveId = null;
  };

  const setTrack = (nextTrack: TrackTimingPayload | null, nextIndex: WordIndex | null) => {
    clearFrame();
    clearSeekTimeout();
    track = nextTrack;
    index = nextIndex;
    cursor = 0;
    lastApplied = Number.NaN;
    lastFollowedSentence = null;
    clearActive();
    if (track && index) {
      cursor = lowerBound(index.events, 0);
      snapToTime(clockRef.current.effectiveTime(track));
      if (!options.isPaused()) {
        start();
      }
    }
  };

  const snap = () => {
    if (!track || !index) {
      clearActive();
      lastApplied = Number.NaN;
      cursor = 0;
      return;
    }
    lastFollowedSentence = null;
    snapToTime(clockRef.current.effectiveTime(track));
  };

  const handleSeeking = () => {
    seeking = true;
    clearSeekTimeout();
    stop();
  };

  const handleSeeked = () => {
    if (!track || !index) {
      seeking = false;
      return;
    }
    clearSeekTimeout();
    seekTimeoutId = window.setTimeout(() => {
      seeking = false;
      snap();
      if (!options.isPaused()) {
        start();
      }
    }, config.SEEK_DEBOUNCE_MS);
  };

  const handleWaiting = () => {
    stalled = true;
    stop();
  };

  const handlePlaying = () => {
    stalled = false;
    seeking = false;
    clearSeekTimeout();
    snap();
    if (!options.isPaused()) {
      start();
    }
  };

  const handleRateChange = () => {
    lastApplied = Number.NaN;
    snap();
  };

  const handlePause = () => {
    stop();
  };

  const handlePlay = () => {
    snap();
    if (!options.isPaused()) {
      start();
    }
  };

  const setFollowHighlight = (value: boolean) => {
    followHighlights = value;
  };

  return {
    setTrack,
    start,
    stop,
    destroy,
    snap,
    handleSeeking,
    handleSeeked,
    handleWaiting,
    handlePlaying,
    handleRateChange,
    handlePause,
    handlePlay,
    setFollowHighlight,
  };
}

export default InteractiveTextViewer;
