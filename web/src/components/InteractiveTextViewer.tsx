import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import type {
  CSSProperties,
  MutableRefObject,
  PointerEvent as ReactPointerEvent,
  MouseEvent as ReactMouseEvent,
  ReactNode,
  UIEvent,
} from 'react';
import { appendAccessToken, assistantLookup, fetchJobTiming } from '../api/client';
import type { AssistantLookupResponse, AudioTrackMetadata, JobTimingEntry, JobTimingResponse } from '../api/dtos';
import type { LiveMediaChunk, MediaClock } from '../hooks/useLiveMedia';
import { useMediaClock } from '../hooks/useLiveMedia';
import PlayerCore from '../player/PlayerCore';
import { usePlayerCore } from '../hooks/usePlayerCore';
import {
  start as startAudioSync,
  stop as stopAudioSync,
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
import { resolve as resolveStoragePath } from '../utils/storageResolver';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { useMyPainter } from '../context/MyPainterProvider';
import { speakText } from '../utils/ttsPlayback';
import { buildMyLinguistSystemPrompt } from '../utils/myLinguistPrompt';
import type { InteractiveTextTheme } from '../types/interactiveTextTheme';
import PlayerChannelBug from './PlayerChannelBug';

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

const DICTIONARY_LOOKUP_LONG_PRESS_MS = 450;
const MY_LINGUIST_BUBBLE_MAX_CHARS = 600;

function containsNonLatinLetters(text: string): boolean {
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
const MY_LINGUIST_EMPTY_SENTINEL = '__EMPTY__';
const MY_LINGUIST_STORAGE_KEYS = {
  inputLanguage: 'ebookTools.myLinguist.inputLanguage',
  lookupLanguage: 'ebookTools.myLinguist.lookupLanguage',
  llmModel: 'ebookTools.myLinguist.llmModel',
  systemPrompt: 'ebookTools.myLinguist.systemPrompt',
  bubblePinned: 'ebookTools.myLinguist.bubblePinned',
} as const;
const MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE = 'English';

const EMPTY_TIMING_PAYLOAD: TimingPayload = {
  trackKind: 'translation_only',
  segments: [],
};

function toTrackKind(track: TrackTimingPayload): TrackKind {
  return track.trackType === 'original_translated'
    ? 'original_translation_combined'
    : 'translation_only';
}

function renderWithNonLatinBoost(text: string, boostedClassName: string): React.ReactNode {
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

type LinguistBubbleTtsStatus = 'idle' | 'loading' | 'ready' | 'error';

type LinguistBubbleNavigation = {
  sentenceIndex: number;
  tokenIndex: number;
  variantKind: TextPlayerVariantKind;
};

type LinguistBubbleState = {
  query: string;
  fullQuery: string;
  status: 'loading' | 'ready' | 'error';
  answer: string;
  modelLabel: string;
  ttsLanguage: string;
  ttsStatus: LinguistBubbleTtsStatus;
  navigation: LinguistBubbleNavigation | null;
};

type LinguistBubbleFloatingPlacement = 'above' | 'below';

function normaliseTextPlayerVariant(value: unknown): TextPlayerVariantKind | null {
  if (typeof value !== 'string') {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (normalized === 'original' || normalized === 'translit' || normalized === 'translation') {
    return normalized;
  }
  return null;
}

function sanitizeLookupQuery(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return '';
  }
  const stripped = trimmed.replace(/^[\s"'“”‘’()[\]{}<>.,!?;:]+|[\s"'“”‘’()[\]{}<>.,!?;:]+$/g, '');
  return stripped.trim() || trimmed;
}

function tokenizeSentenceText(value: string | null | undefined): string[] {
  if (!value) {
    return [];
  }
  return value
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
}

function loadMyLinguistStored(key: string, { allowEmpty = false }: { allowEmpty?: boolean } = {}): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) {
      return null;
    }
    if (raw === MY_LINGUIST_EMPTY_SENTINEL) {
      return '';
    }
    if (!raw.trim()) {
      return allowEmpty ? '' : null;
    }
    return raw;
  } catch {
    return null;
  }
}

function loadMyLinguistStoredBool(key: string, fallback: boolean): boolean {
  if (typeof window === 'undefined') {
    return fallback;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) {
      return fallback;
    }
    const normalized = raw.trim().toLowerCase();
    if (normalized === 'false' || normalized === '0' || normalized === 'off' || normalized === 'no') {
      return false;
    }
    if (normalized === 'true' || normalized === '1' || normalized === 'on' || normalized === 'yes') {
      return true;
    }
    return fallback;
  } catch {
    return fallback;
  }
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
  bookTotalSentences?: number | null;
  jobStartSentence?: number | null;
  jobEndSentence?: number | null;
  jobOriginalLanguage?: string | null;
  jobTranslationLanguage?: string | null;
  cueVisibility?: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
  activeAudioUrl: string | null;
  noAudioAvailable: boolean;
  jobId?: string | null;
  onActiveSentenceChange?: (sentenceNumber: number | null) => void;
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
  theme?: InteractiveTextTheme | null;
  bookTitle?: string | null;
  bookAuthor?: string | null;
  bookYear?: string | null;
  bookGenre?: string | null;
  backgroundOpacityPercent?: number;
  sentenceCardOpacityPercent?: number;
  infoGlyph?: string | null;
  infoGlyphLabel?: string | null;
  infoTitle?: string | null;
  infoMeta?: string | null;
  infoCoverUrl?: string | null;
  infoCoverSecondaryUrl?: string | null;
  infoCoverAltText?: string | null;
  infoCoverVariant?: 'book' | 'subtitles' | 'video' | 'youtube' | 'nas' | 'dub' | 'job' | null;
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

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
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

function rgbaFromHex(hex: string, alpha: number): string | null {
  const rgb = hexToRgb(hex);
  if (!rgb) {
    return null;
  }
  const safeAlpha = Number.isFinite(alpha) ? Math.min(Math.max(alpha, 0), 1) : 1;
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${safeAlpha})`;
}

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
    theme = null,
    bookTitle = null,
    bookAuthor = null,
    bookYear = null,
    bookGenre = null,
    backgroundOpacityPercent = 65,
    sentenceCardOpacityPercent = 100,
    infoGlyph = null,
    infoGlyphLabel = null,
    infoTitle = null,
    infoMeta = null,
    infoCoverUrl = null,
    infoCoverSecondaryUrl = null,
    infoCoverAltText = null,
    infoCoverVariant = null,
    bookCoverUrl = null,
    bookCoverAltText = null,
    onActiveSentenceChange,
    bookTotalSentences = null,
    jobStartSentence = null,
    jobEndSentence = null,
    jobOriginalLanguage = null,
    jobTranslationLanguage = null,
    cueVisibility,
  },
  forwardedRef,
) {
  const { inputLanguage: globalInputLanguage } = useLanguagePreferences();
  const { setPlayerSentence, imageRefreshToken, open: openMyPainter } = useMyPainter();
  const resolvedJobOriginalLanguage = useMemo(() => {
    const trimmed = typeof jobOriginalLanguage === 'string' ? jobOriginalLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobOriginalLanguage]);
  const resolvedJobTranslationLanguage = useMemo(() => {
    const trimmed = typeof jobTranslationLanguage === 'string' ? jobTranslationLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobTranslationLanguage]);
  const resolvedCueVisibility = useMemo(() => {
    return (
      cueVisibility ?? {
        original: true,
        transliteration: true,
        translation: true,
      }
    );
  }, [cueVisibility]);
  const isVariantVisible = useCallback(
    (variant: TextPlayerVariantKind) => {
      if (variant === 'translit') {
        return resolvedCueVisibility.transliteration;
      }
      return resolvedCueVisibility[variant];
    },
    [resolvedCueVisibility],
  );
  const resolvedTranslationSpeed = useMemo(
    () => normaliseTranslationSpeed(translationSpeed),
    [translationSpeed],
  );
  const safeBookTitle = typeof bookTitle === 'string' ? bookTitle.trim() : '';
  const safeBookMeta = useMemo(() => {
    const parts: string[] = [];
    if (typeof bookAuthor === 'string' && bookAuthor.trim()) {
      parts.push(bookAuthor.trim());
    }
    if (typeof bookYear === 'string' && bookYear.trim()) {
      parts.push(bookYear.trim());
    }
    if (typeof bookGenre === 'string' && bookGenre.trim()) {
      parts.push(bookGenre.trim());
    }
    return parts.join(' · ');
  }, [bookAuthor, bookGenre, bookYear]);
  const safeInfoTitle = useMemo(() => {
    const trimmed = typeof infoTitle === 'string' ? infoTitle.trim() : '';
    if (trimmed) {
      return trimmed;
    }
    return safeBookTitle;
  }, [infoTitle, safeBookTitle]);
  const safeInfoMeta = useMemo(() => {
    const trimmed = typeof infoMeta === 'string' ? infoMeta.trim() : '';
    if (trimmed) {
      return trimmed;
    }
    return safeBookMeta;
  }, [infoMeta, safeBookMeta]);
  const safeFontScale = useMemo(() => {
    if (!Number.isFinite(fontScale) || fontScale <= 0) {
      return 1;
    }
    const clamped = Math.min(Math.max(fontScale, 0.5), 3);
    return Math.round(clamped * 100) / 100;
  }, [fontScale]);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const linguistBubbleRef = useRef<HTMLDivElement | null>(null);
  const linguistAnchorRectRef = useRef<DOMRect | null>(null);
  const linguistAnchorElementRef = useRef<HTMLElement | null>(null);
  const linguistNavigationPendingRef = useRef<LinguistBubbleNavigation | null>(null);
  const linguistChunkAdvancePendingRef = useRef<{ variantKind: TextPlayerVariantKind } | null>(null);
  const linguistSelectionArmedRef = useRef(false);
  const linguistSelectionLookupPendingRef = useRef(false);
  const linguistRequestCounterRef = useRef(0);
  const [linguistBubble, setLinguistBubble] = useState<LinguistBubbleState | null>(null);
  const [linguistBubblePinned, setLinguistBubblePinned] = useState<boolean>(() =>
    loadMyLinguistStoredBool(MY_LINGUIST_STORAGE_KEYS.bubblePinned, true),
  );
  const [linguistBubbleFloatingPlacement, setLinguistBubbleFloatingPlacement] =
    useState<LinguistBubbleFloatingPlacement>('above');
  const [linguistBubbleFloatingPosition, setLinguistBubbleFloatingPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const linguistBubblePositionRafRef = useRef<number | null>(null);
  const formatRem = useCallback((value: number) => `${Math.round(value * 1000) / 1000}rem`, []);
  const safeBackgroundOpacity = useMemo(() => {
    const raw = Number(backgroundOpacityPercent);
    if (!Number.isFinite(raw)) {
      return 100;
    }
    return Math.round(Math.min(Math.max(raw, 0), 100));
  }, [backgroundOpacityPercent]);
  const safeSentenceCardOpacity = useMemo(() => {
    const raw = Number(sentenceCardOpacityPercent);
    if (!Number.isFinite(raw)) {
      return 100;
    }
    return Math.round(Math.min(Math.max(raw, 0), 100));
  }, [sentenceCardOpacityPercent]);
  const bodyStyle = useMemo<CSSProperties>(() => {
    const baseSentenceFont = (isFullscreen ? 1.32 : 1.08) * safeFontScale;
    const activeSentenceFont = (isFullscreen ? 1.56 : 1.28) * safeFontScale;
    const style: Record<string, string | number> = {
      '--interactive-font-scale': safeFontScale,
      '--tp-sentence-font-size': formatRem(baseSentenceFont),
      '--tp-sentence-active-font-size': formatRem(activeSentenceFont),
    };

    if (theme) {
      const alpha = safeBackgroundOpacity / 100;
      const resolvedBackground = rgbaFromHex(theme.background, alpha) ?? theme.background;
      style['--interactive-bg'] = resolvedBackground;
      style['--interactive-color-original'] = theme.original;
      style['--interactive-color-original-active'] = theme.originalActive;
      style['--interactive-color-translation'] = theme.translation;
      style['--interactive-color-transliteration'] = theme.transliteration;

      const originalMuted = rgbaFromHex(theme.original, 0.75);
      if (originalMuted) {
        style['--interactive-color-original-muted'] = originalMuted;
      }

      const highlightStrong = rgbaFromHex(theme.highlight, 0.85);
      const highlightSoft = rgbaFromHex(theme.highlight, 0.3);
      const highlightVerySoft = rgbaFromHex(theme.highlight, 0.2);
      const highlightSentenceBg = rgbaFromHex(theme.highlight, 0.45);
      const highlightOutline = rgbaFromHex(theme.highlight, 0.35);

      if (highlightStrong) {
        style['--interactive-highlight-strong'] = highlightStrong;
      }
      if (highlightSoft) {
        style['--interactive-highlight-soft'] = highlightSoft;
      }
      if (highlightVerySoft) {
        style['--interactive-highlight-very-soft'] = highlightVerySoft;
      }
      if (highlightSentenceBg) {
        style['--interactive-highlight-sentence-bg'] = highlightSentenceBg;
      }
      if (highlightOutline) {
        style['--interactive-highlight-outline'] = highlightOutline;
      }

      style['--tp-bg'] = resolvedBackground;
      style['--tp-original'] = theme.original;
      style['--tp-translit'] = theme.transliteration;
      style['--tp-translation'] = theme.translation;
      style['--tp-progress'] = theme.highlight;

      const cardScale = safeSentenceCardOpacity / 100;
      const sentenceBg = rgbaFromHex(theme.highlight, 0.06 * cardScale);
      const sentenceActiveBg = rgbaFromHex(theme.highlight, 0.16 * cardScale);
      const sentenceShadowColor = rgbaFromHex(theme.highlight, 0.22 * cardScale);
      if (sentenceBg) {
        style['--tp-sentence-bg'] = sentenceBg;
      }
      if (sentenceActiveBg) {
        style['--tp-sentence-active-bg'] = sentenceActiveBg;
      }
      if (sentenceShadowColor) {
        style['--tp-sentence-active-shadow'] = `0 6px 26px ${sentenceShadowColor}`;
      } else if (cardScale <= 0.01) {
        style['--tp-sentence-active-shadow'] = 'none';
      }
    }

    return style as CSSProperties;
  }, [formatRem, isFullscreen, safeBackgroundOpacity, safeFontScale, safeSentenceCardOpacity, theme]);
  const safeInfoGlyph = useMemo(() => {
    if (typeof infoGlyph !== 'string') {
      return 'JOB';
    }
    const trimmed = infoGlyph.trim();
    return trimmed ? trimmed : 'JOB';
  }, [infoGlyph]);
  const hasChannelBug = typeof infoGlyph === 'string' && infoGlyph.trim().length > 0;
  const resolvedCoverUrlFromProps = useMemo(() => {
    const primary = typeof infoCoverUrl === 'string' ? infoCoverUrl.trim() : '';
    if (primary) {
      return primary;
    }
    const legacy = typeof bookCoverUrl === 'string' ? bookCoverUrl.trim() : '';
    return legacy || null;
  }, [bookCoverUrl, infoCoverUrl]);
  const resolvedSecondaryCoverUrlFromProps = useMemo(() => {
    const secondary = typeof infoCoverSecondaryUrl === 'string' ? infoCoverSecondaryUrl.trim() : '';
    return secondary || null;
  }, [infoCoverSecondaryUrl]);
  const [viewportCoverFailed, setViewportCoverFailed] = useState(false);
  const [viewportSecondaryCoverFailed, setViewportSecondaryCoverFailed] = useState(false);
  useEffect(() => {
    setViewportCoverFailed(false);
  }, [resolvedCoverUrlFromProps]);
  useEffect(() => {
    setViewportSecondaryCoverFailed(false);
  }, [resolvedSecondaryCoverUrlFromProps]);
  const resolvedCoverUrl = viewportCoverFailed ? null : resolvedCoverUrlFromProps;
  const resolvedSecondaryCoverUrl = viewportSecondaryCoverFailed ? null : resolvedSecondaryCoverUrlFromProps;
  const showSecondaryCover =
    Boolean(resolvedCoverUrl) && Boolean(resolvedSecondaryCoverUrl) && resolvedSecondaryCoverUrl !== resolvedCoverUrl;
  const showCoverArt = Boolean(resolvedCoverUrl);
  const showTextBadge = Boolean(safeInfoTitle || safeInfoMeta);
  const showInfoHeader = hasChannelBug || showCoverArt || showTextBadge;

  const resolvedInfoCoverVariant = useMemo(() => {
    const candidate = typeof infoCoverVariant === 'string' ? infoCoverVariant.trim().toLowerCase() : '';
    if (
      candidate === 'book' ||
      candidate === 'subtitles' ||
      candidate === 'video' ||
      candidate === 'youtube' ||
      candidate === 'nas' ||
      candidate === 'dub' ||
      candidate === 'job'
    ) {
      return candidate;
    }

    const glyph = safeInfoGlyph.trim().toLowerCase();
    if (glyph === 'bk' || glyph === 'book') {
      return 'book';
    }
    if (glyph === 'sub' || glyph === 'subtitle' || glyph === 'subtitles' || glyph === 'cc') {
      return 'subtitles';
    }
    if (glyph === 'yt' || glyph === 'youtube') {
      return 'youtube';
    }
    if (glyph === 'nas') {
      return 'nas';
    }
    if (glyph === 'dub') {
      return 'dub';
    }
    if (glyph === 'tv' || glyph === 'vid' || glyph === 'video') {
      return 'video';
    }
    return 'job';
  }, [infoCoverVariant, safeInfoGlyph]);

  const coverAltText =
    (typeof infoCoverAltText === 'string' && infoCoverAltText.trim() ? infoCoverAltText.trim() : null) ??
    (typeof bookCoverAltText === 'string' && bookCoverAltText.trim() ? bookCoverAltText.trim() : null) ??
    (safeInfoTitle ? `Cover for ${safeInfoTitle}` : 'Cover');
  const dictionaryPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dictionaryPointerIdRef = useRef<number | null>(null);
  const dictionaryAwaitingResumeRef = useRef(false);
  const dictionaryWasPlayingRef = useRef(false);
  const dictionarySuppressSeekRef = useRef(false);
  const {
    ref: attachPlayerCore,
    core: playerCore,
    elementRef: audioRef,
    mediaRef: rawAttachMediaElement,
  } = usePlayerCore();
  const progressTimerRef = useRef<number | null>(null);
  const revealMemoryRef = useRef<{
    sentenceIdx: number | null;
    counts: Record<TextPlayerVariantKind, number>;
  }>({
    sentenceIdx: null,
    counts: {
      original: 0,
      translit: 0,
      translation: 0,
    },
  });
  const lastChunkTimeRef = useRef(0);
  const lastChunkIdRef = useRef<string | null>(null);
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
  const inlineAudioPlayingRef = useRef(false);
  const [jobTimingResponse, setJobTimingResponse] = useState<JobTimingResponse | null>(null);
  const [timingDiagnostics, setTimingDiagnostics] = useState<{ policy: string | null; estimated: boolean; punctuation?: boolean } | null>(null);

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
  const clearDictionaryTimer = useCallback(() => {
    if (dictionaryPressTimerRef.current === null) {
      return;
    }
    clearTimeout(dictionaryPressTimerRef.current);
    dictionaryPressTimerRef.current = null;
  }, []);
  const resumeDictionaryInteraction = useCallback(() => {
    clearDictionaryTimer();
    if (!dictionaryAwaitingResumeRef.current) {
      dictionarySuppressSeekRef.current = false;
      return;
    }
    dictionaryAwaitingResumeRef.current = false;
    dictionaryPointerIdRef.current = null;
    dictionarySuppressSeekRef.current = false;
    const shouldResume = dictionaryWasPlayingRef.current;
    dictionaryWasPlayingRef.current = false;
    if (!shouldResume) {
      return;
    }
    const element = audioRef.current;
    if (!element) {
      return;
    }
    try {
      const attempt = element.play?.();
      if (attempt && typeof attempt.catch === 'function') {
        attempt.catch(() => undefined);
      }
    } catch {
      /* Ignore resume failures triggered by autoplay policies. */
    }
  }, []);
  const requestDictionaryPause = useCallback(() => {
    if (dictionaryAwaitingResumeRef.current) {
      return;
    }
    dictionarySuppressSeekRef.current = true;
    dictionaryAwaitingResumeRef.current = true;
    const element = audioRef.current;
    dictionaryWasPlayingRef.current = inlineAudioPlayingRef.current;
    if (!element) {
      return;
    }
    try {
      element.pause();
    } catch {
      /* Ignore pause failures triggered by autoplay policies. */
    }
  }, []);
  const isDictionaryTokenTarget = useCallback((target: EventTarget | null) => {
    if (!(target instanceof HTMLElement)) {
      return false;
    }
    return Boolean(target.closest('[data-text-player-token="true"]'));
  }, []);
  const handlePointerDownCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const bubbleEl = linguistBubbleRef.current;
      const pointerInsideBubble =
        bubbleEl !== null && event.target instanceof Node && bubbleEl.contains(event.target);
      if (
        event.pointerType === 'mouse' &&
        event.button === 0 &&
        event.isPrimary &&
        !pointerInsideBubble
      ) {
        linguistSelectionArmedRef.current = true;
      } else {
        linguistSelectionArmedRef.current = false;
      }
      if (dictionaryAwaitingResumeRef.current) {
        resumeDictionaryInteraction();
      }
      if (
        event.pointerType !== 'mouse' ||
        event.button !== 0 ||
        !event.isPrimary ||
        !isDictionaryTokenTarget(event.target)
      ) {
        clearDictionaryTimer();
        return;
      }
      dictionaryPointerIdRef.current = event.pointerId;
      clearDictionaryTimer();
      dictionaryPressTimerRef.current = setTimeout(() => {
        dictionaryPressTimerRef.current = null;
        requestDictionaryPause();
      }, DICTIONARY_LOOKUP_LONG_PRESS_MS);
    },
    [clearDictionaryTimer, isDictionaryTokenTarget, requestDictionaryPause, resumeDictionaryInteraction],
  );
  const handlePointerMoveCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (dictionaryPressTimerRef.current === null) {
        return;
      }
      if (event.pointerId !== dictionaryPointerIdRef.current) {
        return;
      }
      if (!isDictionaryTokenTarget(event.target)) {
        clearDictionaryTimer();
      }
    },
    [clearDictionaryTimer, isDictionaryTokenTarget],
  );
  const handlePointerUpCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.pointerId === dictionaryPointerIdRef.current) {
        clearDictionaryTimer();
      }
    },
    [clearDictionaryTimer],
  );
  const handlePointerCancelCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.pointerId === dictionaryPointerIdRef.current) {
        clearDictionaryTimer();
      }
      linguistSelectionArmedRef.current = false;
    },
    [clearDictionaryTimer],
  );

  const toggleInlinePlayback = useCallback(() => {
    const element = audioRef.current;
    if (!element || !(element.currentSrc || element.src)) {
      return;
    }
    try {
      if (element.paused) {
        inlineAudioPlayingRef.current = true;
        onInlineAudioPlaybackStateChange?.('playing');
        const attempt = element.play?.();
        if (attempt && typeof attempt.catch === 'function') {
          attempt.catch(() => {
            inlineAudioPlayingRef.current = false;
            onInlineAudioPlaybackStateChange?.('paused');
          });
        }
      } else {
        element.pause();
        inlineAudioPlayingRef.current = false;
        onInlineAudioPlaybackStateChange?.('paused');
      }
    } catch {
      // Ignore playback toggles blocked by autoplay policies.
    }
  }, [onInlineAudioPlaybackStateChange]);

  const isRenderedTextTarget = useCallback((target: EventTarget | null) => {
    if (!(target instanceof HTMLElement)) {
      return false;
    }
    return Boolean(
      target.closest(
        '[data-text-player-token="true"], .player-panel__document-text, .player-panel__document-status',
      ),
    );
  }, []);

  const closeLinguistBubble = useCallback(() => {
    linguistRequestCounterRef.current += 1;
    linguistAnchorRectRef.current = null;
    linguistAnchorElementRef.current = null;
    linguistNavigationPendingRef.current = null;
    linguistChunkAdvancePendingRef.current = null;
    setLinguistBubble(null);
    setLinguistBubbleFloatingPosition(null);
  }, []);

  const extractLinguistNavigation = useCallback(
    (anchorElement: HTMLElement | null, fallbackVariant: TextPlayerVariantKind | null): LinguistBubbleNavigation | null => {
      if (!anchorElement) {
        return null;
      }
      const variantKind =
        fallbackVariant ?? normaliseTextPlayerVariant(anchorElement.dataset.textPlayerVariant);
      if (!variantKind) {
        return null;
      }
      const rawTokenIndex = anchorElement.dataset.textPlayerTokenIndex;
      const rawSentenceIndex =
        anchorElement.dataset.textPlayerSentenceIndex ??
        anchorElement.closest('[data-sentence-index]')?.getAttribute('data-sentence-index') ??
        null;
      const tokenIndex = rawTokenIndex ? Number(rawTokenIndex) : Number.NaN;
      const sentenceIndex = rawSentenceIndex ? Number(rawSentenceIndex) : Number.NaN;
      if (!Number.isFinite(tokenIndex) || !Number.isFinite(sentenceIndex)) {
        return null;
      }
      return {
        sentenceIndex,
        tokenIndex,
        variantKind,
      };
    },
    [],
  );

  const openLinguistBubbleForRect = useCallback(
    (
      query: string,
      rect: DOMRect,
      trigger: 'click' | 'selection',
      variantKind: TextPlayerVariantKind | null,
      anchorElement: HTMLElement | null,
      navigationOverride: LinguistBubbleNavigation | null = null,
    ) => {
      const cleanedQuery = sanitizeLookupQuery(query);
      if (!cleanedQuery) {
        return;
      }
      linguistAnchorRectRef.current = rect;
      linguistAnchorElementRef.current = anchorElement;
      const inlineAudioEl = audioRef.current;
      if (inlineAudioEl && !inlineAudioEl.paused) {
        try {
          inlineAudioEl.pause();
        } catch {
          // Ignore pause failures triggered by autoplay policies.
        }
      }
      const slicedQuery =
        cleanedQuery.length > MY_LINGUIST_BUBBLE_MAX_CHARS
          ? `${cleanedQuery.slice(0, MY_LINGUIST_BUBBLE_MAX_CHARS)}…`
          : cleanedQuery;

      const storedInputLanguage =
        loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.inputLanguage) ?? globalInputLanguage;
      const storedLookupLanguage =
        loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.lookupLanguage) ?? MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE;
      const storedModel = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.llmModel, { allowEmpty: true });
      const storedPrompt = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.systemPrompt, { allowEmpty: true });

      const jobPreferredInputLanguage =
        variantKind === 'translation'
          ? resolvedJobTranslationLanguage
          : variantKind === 'original' || variantKind === 'translit'
            ? resolvedJobOriginalLanguage
            : null;
      const resolvedInputLanguage = (jobPreferredInputLanguage ?? storedInputLanguage).trim() || globalInputLanguage;
      const resolvedLookupLanguage = storedLookupLanguage.trim() || MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE;
      const resolvedModel = storedModel && storedModel.trim() ? storedModel.trim() : null;
      const modelLabel = resolvedModel ?? 'Auto';
      const resolvedPrompt =
        storedPrompt && storedPrompt.trim()
          ? storedPrompt.trim()
          : buildMyLinguistSystemPrompt(resolvedInputLanguage, resolvedLookupLanguage);

      const requestId = (linguistRequestCounterRef.current += 1);
      const navigation =
        navigationOverride ?? extractLinguistNavigation(anchorElement, variantKind);
      setLinguistBubble({
        query: slicedQuery,
        fullQuery: cleanedQuery,
        status: 'loading',
        answer: 'Lookup in progress…',
        modelLabel,
        ttsLanguage: resolvedInputLanguage,
        ttsStatus: 'idle',
        navigation,
      });

      const page = typeof window !== 'undefined' ? window.location.pathname : null;
      void assistantLookup({
        query: slicedQuery,
        input_language: resolvedInputLanguage,
        lookup_language: resolvedLookupLanguage,
        llm_model: resolvedModel,
        system_prompt: resolvedPrompt,
        context: {
          source: 'my_linguist',
          page,
          job_id: jobId,
          selection_text: trigger === 'selection' ? slicedQuery : null,
          metadata: {
            ui: 'interactive_bubble',
            trigger,
            chunk_id: chunk?.chunkId ?? null,
          },
        },
      })
        .then((response: AssistantLookupResponse) => {
          if (linguistRequestCounterRef.current !== requestId) {
            return;
          }
          setLinguistBubble((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              status: 'ready',
              answer: response.answer,
              ttsStatus: 'loading',
            };
          });
          void speakText({ text: cleanedQuery, language: resolvedInputLanguage })
            .then(() => {
              if (linguistRequestCounterRef.current !== requestId) {
                return;
              }
              setLinguistBubble((previous) => {
                if (!previous) {
                  return previous;
                }
                return { ...previous, ttsStatus: 'ready' };
              });
            })
            .catch(() => {
              if (linguistRequestCounterRef.current !== requestId) {
                return;
              }
              setLinguistBubble((previous) => {
                if (!previous) {
                  return previous;
                }
                return { ...previous, ttsStatus: 'error' };
              });
            });
        })
        .catch((error: unknown) => {
          if (linguistRequestCounterRef.current !== requestId) {
            return;
          }
          const message = error instanceof Error ? error.message : 'Unable to reach MyLinguist.';
          setLinguistBubble((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              status: 'error',
              answer: `Error: ${message}`,
              ttsStatus: 'idle',
            };
          });
        });
    },
    [
      chunk?.chunkId,
      extractLinguistNavigation,
      globalInputLanguage,
      jobId,
      resolvedJobOriginalLanguage,
      resolvedJobTranslationLanguage,
    ],
  );

  const handleLinguistSpeak = useCallback(() => {
    const bubble = linguistBubble;
    if (!bubble) {
      return;
    }
    const text = bubble.fullQuery.trim();
    if (!text || bubble.ttsStatus === 'loading') {
      return;
    }
    const requestId = linguistRequestCounterRef.current;
    setLinguistBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsStatus: 'loading' };
    });
    void speakText({ text, language: bubble.ttsLanguage })
      .then(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'ready' };
        });
      })
      .catch(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'error' };
        });
      });
  }, [linguistBubble]);

  const handleLinguistSpeakSlow = useCallback(() => {
    const bubble = linguistBubble;
    if (!bubble) {
      return;
    }
    const text = bubble.fullQuery.trim();
    if (!text || bubble.ttsStatus === 'loading') {
      return;
    }
    const requestId = linguistRequestCounterRef.current;
    setLinguistBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsStatus: 'loading' };
    });
    void speakText({ text, language: bubble.ttsLanguage, playbackRate: 0.5 })
      .then(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'ready' };
        });
      })
      .catch(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'error' };
        });
      });
  }, [linguistBubble]);

  const handleLinguistTokenClickCapture = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (event.button !== 0) {
        return;
      }
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const bubbleEl = linguistBubbleRef.current;
      if (bubbleEl && event.target instanceof Node && bubbleEl.contains(event.target)) {
        return;
      }

      const selection = typeof document !== 'undefined' ? document.getSelection() : null;
      if (selection && !selection.isCollapsed && selection.toString().trim()) {
        const anchorInside =
          selection.anchorNode instanceof Node ? container.contains(selection.anchorNode) : false;
        const focusInside =
          selection.focusNode instanceof Node ? container.contains(selection.focusNode) : false;
        if (anchorInside || focusInside) {
          event.stopPropagation();
          if (typeof (event.nativeEvent as MouseEvent | undefined)?.stopImmediatePropagation === 'function') {
            (event.nativeEvent as MouseEvent).stopImmediatePropagation();
          }
          if (linguistSelectionLookupPendingRef.current) {
            event.preventDefault();
          }
        }
        return;
      }

      if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
        return;
      }
      if (!(event.target instanceof HTMLElement)) {
        return;
      }
      const token = event.target.closest('[data-text-player-token="true"]');
      if (!token || !(token instanceof HTMLElement) || !container.contains(token)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (typeof (event.nativeEvent as MouseEvent | undefined)?.stopImmediatePropagation === 'function') {
        (event.nativeEvent as MouseEvent).stopImmediatePropagation();
      }
      const tokenText = token.textContent ?? '';
      const variantKind = normaliseTextPlayerVariant((token as HTMLElement).dataset.textPlayerVariant);
      const rect = token.getBoundingClientRect();
      openLinguistBubbleForRect(tokenText, rect, 'click', variantKind, token);
    },
    [openLinguistBubbleForRect],
  );

  const handleSelectionLookup = useCallback(() => {
    if (typeof document === 'undefined') {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const bubbleEl = linguistBubbleRef.current;
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) {
      return;
    }
    const anchorNode = selection.anchorNode;
    const focusNode = selection.focusNode;
    const anchorInside = anchorNode instanceof Node ? container.contains(anchorNode) : false;
    const focusInside = focusNode instanceof Node ? container.contains(focusNode) : false;
    if (!anchorInside && !focusInside) {
      return;
    }
    if (bubbleEl) {
      const anchorInBubble = anchorNode instanceof Node ? bubbleEl.contains(anchorNode) : false;
      const focusInBubble = focusNode instanceof Node ? bubbleEl.contains(focusNode) : false;
      if (anchorInBubble || focusInBubble) {
        return;
      }
    }
    const rawText = selection.toString();
    const trimmed = rawText.trim();
    if (!trimmed) {
      return;
    }
    const variantKind = (() => {
      const candidates: Array<Node | null> = [selection.anchorNode, selection.focusNode];
      for (const node of candidates) {
        const element =
          node instanceof HTMLElement
            ? node
            : node && node.parentElement instanceof HTMLElement
              ? node.parentElement
              : null;
        if (!element) {
          continue;
        }
        const variantEl = element.closest('[data-text-player-variant]');
        if (!(variantEl instanceof HTMLElement)) {
          continue;
        }
        const kind = normaliseTextPlayerVariant(variantEl.dataset.textPlayerVariant);
        if (kind) {
          return kind;
        }
      }
      return null;
    })();
    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    let rect: DOMRect | null = null;
    if (range) {
      rect = range.getBoundingClientRect();
    }
    if (!rect || (!rect.width && !rect.height)) {
      const node = (focusNode instanceof HTMLElement ? focusNode : focusNode?.parentElement) ?? null;
      rect = node ? node.getBoundingClientRect() : null;
    }
    if (!rect) {
      return;
    }
    const anchorCandidate = (focusNode instanceof HTMLElement ? focusNode : focusNode?.parentElement)?.closest?.(
      '[data-text-player-token="true"]',
    );
    const anchorEl = anchorCandidate instanceof HTMLElement ? anchorCandidate : null;
    openLinguistBubbleForRect(trimmed, rect, 'selection', variantKind, anchorEl);
  }, [openLinguistBubbleForRect]);

  const toggleLinguistBubblePinned = useCallback(() => {
    setLinguistBubblePinned((previous) => {
      const next = !previous;
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(MY_LINGUIST_STORAGE_KEYS.bubblePinned, String(next));
        } catch {
          // ignore
        }
      }
      return next;
    });
  }, []);

  const updateLinguistBubbleFloatingPosition = useCallback(() => {
    if (!linguistBubble || linguistBubblePinned) {
      setLinguistBubbleFloatingPosition(null);
      setLinguistBubbleFloatingPlacement('above');
      return;
    }
    const container = containerRef.current;
    const bubbleEl = linguistBubbleRef.current;
    if (!container || !bubbleEl) {
      return;
    }

    const anchorEl = linguistAnchorElementRef.current;
    const anchorRect = anchorEl?.getBoundingClientRect?.() ?? linguistAnchorRectRef.current;
    if (!anchorRect) {
      return;
    }

    const containerRect = container.getBoundingClientRect();
    const bubbleRect = bubbleEl.getBoundingClientRect();
    if (!Number.isFinite(bubbleRect.width) || !Number.isFinite(bubbleRect.height)) {
      return;
    }

    const margin = 12;
    const centerX = anchorRect.left + anchorRect.width / 2 - containerRect.left;
    const halfWidth = bubbleRect.width / 2;
    const minLeft = halfWidth + margin;
    const maxLeft = Math.max(minLeft, containerRect.width - halfWidth - margin);
    const clampedLeft = Math.min(Math.max(centerX, minLeft), maxLeft);

    let placement: LinguistBubbleFloatingPlacement = 'above';
    let top = anchorRect.top - containerRect.top - bubbleRect.height - margin;
    if (!Number.isFinite(top)) {
      return;
    }
    if (top < margin) {
      placement = 'below';
      top = anchorRect.bottom - containerRect.top + margin;
    }
    top = Math.max(margin, top);

    setLinguistBubbleFloatingPlacement(placement);
    setLinguistBubbleFloatingPosition((previous) => {
      const next = { top: Math.round(top), left: Math.round(clampedLeft) };
      if (!previous || previous.top !== next.top || previous.left !== next.left) {
        return next;
      }
      return previous;
    });
  }, [linguistBubble, linguistBubblePinned]);

  const requestLinguistBubblePositionUpdate = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (linguistBubblePositionRafRef.current !== null) {
      return;
    }
    linguistBubblePositionRafRef.current = window.requestAnimationFrame(() => {
      linguistBubblePositionRafRef.current = null;
      updateLinguistBubbleFloatingPosition();
    });
  }, [updateLinguistBubbleFloatingPosition]);

  const handlePointerUpCaptureWithSelection = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      handlePointerUpCapture(event);
      const shouldLookupSelection = linguistSelectionArmedRef.current;
      linguistSelectionArmedRef.current = false;
      if (event.pointerType !== 'mouse' || event.button !== 0 || !event.isPrimary) {
        return;
      }
      if (!shouldLookupSelection) {
        return;
      }
      if (typeof window === 'undefined') {
        return;
      }
      const bubbleEl = linguistBubbleRef.current;
      if (bubbleEl && event.target instanceof Node && bubbleEl.contains(event.target)) {
        return;
      }
      linguistSelectionLookupPendingRef.current = true;
      window.setTimeout(() => {
        handleSelectionLookup();
        linguistSelectionLookupPendingRef.current = false;
      }, 0);
    },
    [handlePointerUpCapture, handleSelectionLookup],
  );

  const handleInteractiveBackgroundClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (event.button !== 0) {
        return;
      }
      if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
        return;
      }
      const bubbleEl = linguistBubbleRef.current;
      if (bubbleEl && event.target instanceof Node && bubbleEl.contains(event.target)) {
        return;
      }
      const selection = typeof document !== 'undefined' ? document.getSelection() : null;
      if (selection && !selection.isCollapsed) {
        return;
      }
      if (isRenderedTextTarget(event.target)) {
        return;
      }
      toggleInlinePlayback();
    },
    [isRenderedTextTarget, toggleInlinePlayback],
  );

  useEffect(() => {
    if (!linguistBubble || linguistBubblePinned) {
      setLinguistBubbleFloatingPosition(null);
      setLinguistBubbleFloatingPlacement('above');
      return;
    }
    requestLinguistBubblePositionUpdate();
  }, [linguistBubble, linguistBubblePinned, requestLinguistBubblePositionUpdate]);

  useEffect(() => {
    if (!linguistBubble || linguistBubblePinned) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const handleResize = () => requestLinguistBubblePositionUpdate();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [linguistBubble, linguistBubblePinned, requestLinguistBubblePositionUpdate]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    return () => {
      if (linguistBubblePositionRafRef.current !== null) {
        window.cancelAnimationFrame(linguistBubblePositionRafRef.current);
        linguistBubblePositionRafRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!linguistBubble) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' || event.key === 'Esc') {
        closeLinguistBubble();
      }
    };
    const handlePointerDown = (event: PointerEvent) => {
      const bubbleEl = linguistBubbleRef.current;
      if (!bubbleEl) {
        closeLinguistBubble();
        return;
      }
      const target = event.target;
      if (target instanceof Node && bubbleEl.contains(target)) {
        return;
      }
      closeLinguistBubble();
    };
    window.addEventListener('keydown', handleKeyDown, true);
    window.addEventListener('pointerdown', handlePointerDown, true);
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      window.removeEventListener('pointerdown', handlePointerDown, true);
    };
  }, [closeLinguistBubble, linguistBubble]);
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handleGlobalPointerDown = (event: PointerEvent) => {
      if (!dictionaryAwaitingResumeRef.current) {
        return;
      }
      if (event.pointerId === dictionaryPointerIdRef.current) {
        return;
      }
      resumeDictionaryInteraction();
    };
    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if (!dictionaryAwaitingResumeRef.current) {
        return;
      }
      if (event.key === 'Escape' || event.key === 'Esc') {
        resumeDictionaryInteraction();
      }
    };
    window.addEventListener('pointerdown', handleGlobalPointerDown, true);
    window.addEventListener('keydown', handleGlobalKeyDown, true);
    return () => {
      window.removeEventListener('pointerdown', handleGlobalPointerDown, true);
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [resumeDictionaryInteraction]);
  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }
    const handleSelectionChange = () => {
      if (!dictionaryAwaitingResumeRef.current) {
        return;
      }
      const selection = document.getSelection();
      if (!selection || selection.isCollapsed) {
        resumeDictionaryInteraction();
        return;
      }
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const anchorNode = selection.anchorNode;
      const focusNode = selection.focusNode;
      const anchorInside =
        anchorNode instanceof Node ? container.contains(anchorNode) : false;
      const focusInside =
        focusNode instanceof Node ? container.contains(focusNode) : false;
      if (!anchorInside && !focusInside) {
        resumeDictionaryInteraction();
      }
    };
    document.addEventListener('selectionchange', handleSelectionChange);
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  }, [resumeDictionaryInteraction]);
  useEffect(() => {
    return () => {
      clearDictionaryTimer();
      dictionaryAwaitingResumeRef.current = false;
      dictionaryPointerIdRef.current = null;
      dictionarySuppressSeekRef.current = false;
      dictionaryWasPlayingRef.current = false;
    };
  }, [clearDictionaryTimer]);
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
        if (!isVariantVisible(baseClass)) {
          return;
        }
        if (!variantRuntime || variantRuntime.tokens.length === 0) {
          return;
        }

        const tokens = variantRuntime.tokens;
        const revealTimes = variantRuntime.revealTimes;
        const safeEffectiveTime = Math.min(Math.max(effectiveTime, startTime - 1e-3), endTime + 1e-3);
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
        if (safeEffectiveTime >= endTime - 1e-3) {
          revealedCount = tokens.length;
        }
        if (revealMemoryRef.current.sentenceIdx !== runtime.index) {
          revealMemoryRef.current = {
            sentenceIdx: runtime.index,
            counts: { original: 0, translit: 0, translation: 0 },
          };
        }
        const previousCount = revealMemoryRef.current.counts[baseClass] ?? 0;
        const stableCount = Math.max(previousCount, revealedCount);
        revealMemoryRef.current.counts[baseClass] = stableCount;
        revealedCount = stableCount;
        const zeroToOneEligible =
          revealTimes.length > 0 &&
          stabilisedState === 'active' &&
          safeEffectiveTime >= startTime - 1e-3 &&
          revealedCount === 0;
        if (zeroToOneEligible) {
          revealedCount = 1;
          revealMemoryRef.current.counts[baseClass] = 1;
        }

        let currentIndex: number | null = revealedCount > 0 ? revealedCount - 1 : null;
        if (tokens.length > 0 && (stabilisedState === 'past' || safeEffectiveTime >= endTime - 1e-3)) {
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

      if (variants.length === 0) {
        return;
      }

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
  }, [timelineSentences, chunkTime, audioDuration, activeSentenceIndex, isVariantVisible]);
  
  const rawSentences = useMemo(
    () =>
      paragraphs
        .map((paragraph) => paragraph.sentences)
        .flat()
        .sort((a, b) => a.index - b.index),
    [paragraphs],
  );
  const linguistSentenceOrder = useMemo(() => {
    if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
      return timelineDisplay.sentences.map((sentence) => sentence.index);
    }
    if (chunk?.sentences && chunk.sentences.length > 0) {
      return chunk.sentences.map((_sentence, index) => index);
    }
    return rawSentences.map((sentence) => sentence.index);
  }, [chunk?.sentences, rawSentences, timelineDisplay?.sentences]);
  const linguistSentencePositionByIndex = useMemo(() => {
    const map = new Map<number, number>();
    linguistSentenceOrder.forEach((sentenceIndex, position) => {
      map.set(sentenceIndex, position);
    });
    return map;
  }, [linguistSentenceOrder]);

  const tokensForSentence = useCallback(
    (sentenceIndex: number, variantKind: TextPlayerVariantKind): string[] => {
      if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
        const sentence = timelineDisplay.sentences.find((entry) => entry.index === sentenceIndex);
        const variant = sentence?.variants?.find((candidate) => candidate.baseClass === variantKind) ?? null;
        return variant?.tokens ?? [];
      }

      if (chunk?.sentences && chunk.sentences.length > 0) {
        const sentence = chunk.sentences[sentenceIndex];
        if (!sentence) {
          return [];
        }
        if (variantKind === 'translation') {
          return tokenizeSentenceText(sentence.translation?.text ?? null);
        }
        if (variantKind === 'translit') {
          return tokenizeSentenceText(sentence.transliteration?.text ?? null);
        }
        return tokenizeSentenceText(sentence.original?.text ?? null);
      }

      const position = linguistSentencePositionByIndex.get(sentenceIndex);
      if (position === undefined) {
        return [];
      }
      const sentence = rawSentences[position];
      if (variantKind === 'translation') {
        return tokenizeSentenceText(sentence.translation);
      }
      if (variantKind === 'translit') {
        return tokenizeSentenceText(sentence.transliteration);
      }
      return tokenizeSentenceText(sentence.text);
    },
    [chunk?.sentences, linguistSentencePositionByIndex, rawSentences, timelineDisplay?.sentences],
  );

  const seekTimeForNavigation = useCallback(
    (navigation: LinguistBubbleNavigation): number | null => {
      if (!timelineDisplay?.sentences || timelineDisplay.sentences.length === 0) {
        return null;
      }
      const sentence = timelineDisplay.sentences.find((entry) => entry.index === navigation.sentenceIndex);
      const variant = sentence?.variants?.find((candidate) => candidate.baseClass === navigation.variantKind) ?? null;
      const times = variant?.seekTimes ?? null;
      if (!times || navigation.tokenIndex < 0 || navigation.tokenIndex >= times.length) {
        return null;
      }
      const time = times[navigation.tokenIndex];
      return typeof time === 'number' && Number.isFinite(time) ? time : null;
    },
    [timelineDisplay?.sentences],
  );

  const seekInlineAudioToTime = useCallback((time: number) => {
    if (dictionarySuppressSeekRef.current) {
      return;
    }
    const element = audioRef.current;
    if (!element || !Number.isFinite(time)) {
      return;
    }
    try {
      wordSyncControllerRef.current?.handleSeeking();
      const target = Math.max(0, Math.min(time, Number.isFinite(element.duration) ? element.duration : time));
      element.currentTime = target;
      setChunkTime(target);
      // Keep playback paused while stepping between words.
      wordSyncControllerRef.current?.snap();
    } catch {
      // Ignore seek/play failures.
    }
  }, [setChunkTime]);

  const resolveRelativeLinguistNavigation = useCallback(
    (current: LinguistBubbleNavigation, delta: -1 | 1): LinguistBubbleNavigation | null => {
      const startPosition = linguistSentencePositionByIndex.get(current.sentenceIndex);
      if (startPosition === undefined) {
        return null;
      }
      const variantKind = current.variantKind;
      const currentTokens = tokensForSentence(current.sentenceIndex, variantKind);
      if (currentTokens.length === 0) {
        return null;
      }

      let sentencePosition = startPosition;
      let tokenIndex = current.tokenIndex + delta;

      if (tokenIndex < 0) {
        sentencePosition -= 1;
        while (sentencePosition >= 0) {
          const nextSentenceIndex = linguistSentenceOrder[sentencePosition];
          const tokens = tokensForSentence(nextSentenceIndex, variantKind);
          if (tokens.length > 0) {
            tokenIndex = tokens.length - 1;
            return { sentenceIndex: nextSentenceIndex, tokenIndex, variantKind };
          }
          sentencePosition -= 1;
        }
        return null;
      }

      if (tokenIndex >= currentTokens.length) {
        sentencePosition += 1;
        while (sentencePosition < linguistSentenceOrder.length) {
          const nextSentenceIndex = linguistSentenceOrder[sentencePosition];
          const tokens = tokensForSentence(nextSentenceIndex, variantKind);
          if (tokens.length > 0) {
            tokenIndex = 0;
            return { sentenceIndex: nextSentenceIndex, tokenIndex, variantKind };
          }
          sentencePosition += 1;
        }
        return null;
      }

      return {
        sentenceIndex: current.sentenceIndex,
        tokenIndex,
        variantKind,
      };
    },
    [linguistSentenceOrder, linguistSentencePositionByIndex, tokensForSentence],
  );

  const findTextPlayerTokenElement = useCallback((navigation: LinguistBubbleNavigation): HTMLElement | null => {
    const container = containerRef.current;
    if (!container) {
      return null;
    }
    const selector = [
      `[data-sentence-index="${navigation.sentenceIndex}"]`,
      `[data-text-player-token="true"][data-text-player-variant="${navigation.variantKind}"][data-text-player-token-index="${navigation.tokenIndex}"]`,
    ].join(' ');
    const match = container.querySelector(selector);
    return match instanceof HTMLElement ? match : null;
  }, []);

  const navigateLinguistWord = useCallback(
    (delta: -1 | 1) => {
      const current = linguistBubble?.navigation ?? null;
      if (!linguistBubble || !current) {
        return;
      }
      const target = resolveRelativeLinguistNavigation(current, delta);
      if (!target) {
        if (delta === 1 && onRequestAdvanceChunk) {
          linguistChunkAdvancePendingRef.current = { variantKind: current.variantKind };
          onRequestAdvanceChunk();
        }
        return;
      }

      const targetTokens = tokensForSentence(target.sentenceIndex, target.variantKind);
      const rawWord = targetTokens[target.tokenIndex] ?? '';
      if (!rawWord.trim()) {
        return;
      }

      const seekTime = seekTimeForNavigation(target);

      const tokenEl = findTextPlayerTokenElement(target);
      if (tokenEl) {
        openLinguistBubbleForRect(
          rawWord,
          tokenEl.getBoundingClientRect(),
          'click',
          target.variantKind,
          tokenEl,
        );
        if (seekTime !== null) {
          seekInlineAudioToTime(seekTime);
        }
        return;
      }

      const container = containerRef.current;
      const fallbackRect = linguistAnchorRectRef.current ?? container?.getBoundingClientRect();
      if (!fallbackRect) {
        return;
      }

      // Kick off the lookup now, then move the text player if needed. We'll re-anchor to the token once rendered.
      openLinguistBubbleForRect(rawWord, fallbackRect, 'click', target.variantKind, null, target);
      if (seekTime !== null) {
        seekInlineAudioToTime(seekTime);
      }
      if (target.sentenceIndex !== activeSentenceIndex) {
        linguistNavigationPendingRef.current = target;
        setActiveSentenceIndex(target.sentenceIndex);
      }
    },
    [
      activeSentenceIndex,
      findTextPlayerTokenElement,
      linguistBubble,
      openLinguistBubbleForRect,
      resolveRelativeLinguistNavigation,
      seekInlineAudioToTime,
      seekTimeForNavigation,
      tokensForSentence,
      onRequestAdvanceChunk,
    ],
  );

  const linguistCanNavigatePrev = useMemo(() => {
    const current = linguistBubble?.navigation ?? null;
    if (!current) {
      return false;
    }
    return resolveRelativeLinguistNavigation(current, -1) !== null;
  }, [linguistBubble?.navigation, resolveRelativeLinguistNavigation]);

  const linguistCanNavigateNext = useMemo(() => {
    const current = linguistBubble?.navigation ?? null;
    if (!current) {
      return false;
    }
    return resolveRelativeLinguistNavigation(current, 1) !== null;
  }, [linguistBubble?.navigation, resolveRelativeLinguistNavigation]);

  useEffect(() => {
    const pending = linguistNavigationPendingRef.current;
    if (!pending || !linguistBubble || linguistBubblePinned) {
      return;
    }
    const tokenEl = findTextPlayerTokenElement(pending);
    if (!tokenEl) {
      return;
    }
    linguistNavigationPendingRef.current = null;
    linguistAnchorElementRef.current = tokenEl;
    linguistAnchorRectRef.current = tokenEl.getBoundingClientRect();
    requestLinguistBubblePositionUpdate();
  }, [
    findTextPlayerTokenElement,
    linguistBubble,
    linguistBubblePinned,
    requestLinguistBubblePositionUpdate,
  ]);

  useEffect(() => {
    const pendingAdvance = linguistChunkAdvancePendingRef.current;
    if (!pendingAdvance || !linguistBubble) {
      return;
    }

    const variantKind = pendingAdvance.variantKind;
    let sentenceIndex: number | null = null;
    for (const candidate of linguistSentenceOrder) {
      const tokens = tokensForSentence(candidate, variantKind);
      if (tokens.length > 0) {
        sentenceIndex = candidate;
        break;
      }
    }

    linguistChunkAdvancePendingRef.current = null;
    if (sentenceIndex === null) {
      return;
    }

    const tokens = tokensForSentence(sentenceIndex, variantKind);
    const rawWord = tokens[0] ?? '';
    if (!rawWord.trim()) {
      return;
    }

    const navigation: LinguistBubbleNavigation = {
      sentenceIndex,
      tokenIndex: 0,
      variantKind,
    };

    const seekTime = seekTimeForNavigation(navigation);
    if (seekTime !== null) {
      seekInlineAudioToTime(seekTime);
    }

    const container = containerRef.current;
    const fallbackRect = container?.getBoundingClientRect() ?? linguistAnchorRectRef.current;
    if (!fallbackRect) {
      return;
    }

    openLinguistBubbleForRect(rawWord, fallbackRect, 'click', variantKind, null, navigation);
    if (sentenceIndex !== activeSentenceIndex) {
      setActiveSentenceIndex(sentenceIndex);
      if (!linguistBubblePinned) {
        linguistNavigationPendingRef.current = navigation;
      }
    }
  }, [
    activeSentenceIndex,
    linguistBubble,
    linguistBubblePinned,
    linguistSentenceOrder,
    openLinguistBubbleForRect,
    seekInlineAudioToTime,
    seekTimeForNavigation,
    tokensForSentence,
  ]);

  useEffect(() => {
    if (!linguistBubble) {
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
        event.metaKey ||
        event.ctrlKey ||
        !event.altKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        navigateLinguistWord(-1);
        return;
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        navigateLinguistWord(1);
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, [linguistBubble, navigateLinguistWord]);

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

    if (chunk?.sentences && chunk.sentences.length > 0) {
      const fallbackFromChunk: TextPlayerSentence[] = chunk.sentences.map((metadata, index) => {
        const originalTokens = tokenizeSentenceText(metadata.original?.text ?? null);
        const transliterationTokens = tokenizeSentenceText(metadata.transliteration?.text ?? null);
        const translationTokens = tokenizeSentenceText(metadata.translation?.text ?? null);

        const variants: TextPlayerVariantDisplay[] = [];
        if (resolvedCueVisibility.original && originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (resolvedCueVisibility.transliteration && transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (resolvedCueVisibility.translation && translationTokens.length > 0) {
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
        const originalTokens = tokenizeSentenceText(sentence.text);
        const translationTokens = tokenizeSentenceText(sentence.translation);
        const transliterationTokens = tokenizeSentenceText(sentence.transliteration);

        const variants: TextPlayerVariantDisplay[] = [];
        if (resolvedCueVisibility.original && originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (resolvedCueVisibility.transliteration && transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (resolvedCueVisibility.translation && translationTokens.length > 0) {
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
  }, [timelineDisplay, chunk?.sentences, rawSentences, activeSentenceIndex, resolvedCueVisibility]);
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
    if (!onActiveSentenceChange) {
      return;
    }
    if (!totalSentences || totalSentences <= 0) {
      onActiveSentenceChange(null);
      return;
    }
    const activeSentenceNumber = (() => {
      const rawSentenceNumber = chunk?.sentences?.[activeSentenceIndex]?.sentence_number ?? null;
      const chunkSentenceNumber =
        typeof rawSentenceNumber === 'number' && Number.isFinite(rawSentenceNumber)
          ? Math.trunc(rawSentenceNumber)
          : null;
      if (chunkSentenceNumber !== null) {
        return chunkSentenceNumber;
      }
      const start =
        typeof chunk?.startSentence === 'number' && Number.isFinite(chunk.startSentence)
          ? Math.trunc(chunk.startSentence)
          : null;
      if (start !== null) {
        return start + Math.max(0, Math.trunc(activeSentenceIndex));
      }
      return Math.max(1, Math.trunc(activeSentenceIndex) + 1);
    })();
    onActiveSentenceChange(activeSentenceNumber);
  }, [activeSentenceIndex, chunk?.sentences, chunk?.startSentence, onActiveSentenceChange, totalSentences]);

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
      setChunkTime(0);
      return;
    }
    pendingInitialSeek.current = null;
    lastReportedPosition.current = 0;
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    setAudioDuration(null);
    setChunkTime(0);
  }, [effectiveAudioUrl, getStoredAudioPosition]);

  const handleScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      onScroll?.(event);
      if (linguistBubble && !linguistBubblePinned) {
        requestLinguistBubblePositionUpdate();
      }
    },
    [linguistBubble, linguistBubblePinned, onScroll, requestLinguistBubblePositionUpdate],
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

      const ratio = time / duration;
      const progress =
        ratio >= 0.995 ? 1 : Math.max(0, Math.min(ratio, 1));
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
    inlineAudioPlayingRef.current = true;
    timingStore.setLast(null);
    const startPlayback = () => {
      wordSyncControllerRef.current?.handlePlay();
      onInlineAudioPlaybackStateChange?.('playing');
      const element = audioRef.current;
      if (element && element.ended) {
        element.currentTime = 0;
        setChunkTime(0);
        setActiveSentenceIndex(0);
        setActiveSentenceProgress(0);
        updateActiveGateFromTime(0);
      }
      if (progressTimerRef.current === null) {
        progressTimerRef.current = window.setInterval(() => {
          const mediaEl = audioRef.current;
          if (!mediaEl) {
            return;
          }
          const { currentTime, duration } = mediaEl;
          if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
            return;
          }
          setAudioDuration((existing) =>
            existing && Math.abs(existing - duration) < 0.01 ? existing : duration,
          );
          setChunkTime(currentTime);
          if (!hasTimeline) {
            updateSentenceForTime(currentTime, duration);
          }
          updateActiveGateFromTime(currentTime);
        }, 120);
      }
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
  }, [onInlineAudioPlaybackStateChange, updateActiveGateFromTime, updateSentenceForTime]);

  const handleInlineAudioPause = useCallback(() => {
    inlineAudioPlayingRef.current = false;
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
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
    const initialTime = (() => {
      const current = element.currentTime ?? 0;
      if (Number.isFinite(duration) && duration > 0 && current >= duration - 0.25) {
        return 0;
      }
      return current;
    })();
    if (initialTime !== (element.currentTime ?? 0)) {
      element.currentTime = initialTime;
    }
    setChunkTime(initialTime);
    const seek = pendingInitialSeek.current;
    if (typeof seek === 'number' && seek > 0 && Number.isFinite(duration) && duration > 0) {
      const nearEndThreshold = Math.max(duration * 0.9, duration - 3);
      let targetSeek = seek >= nearEndThreshold ? 0 : Math.min(seek, duration - 0.1);
      if (targetSeek < 0 || !Number.isFinite(targetSeek)) {
        targetSeek = 0;
      }
      element.currentTime = targetSeek;
      if (!hasTimeline) {
        updateSentenceForTime(targetSeek, duration);
      }
      updateActiveGateFromTime(targetSeek);
      emitAudioProgress(targetSeek);
      if (targetSeek > 0.1) {
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      }
      pendingInitialSeek.current = null;
      wordSyncControllerRef.current?.snap();
      return;
    }
    pendingInitialSeek.current = null;
    updateActiveGateFromTime(element.currentTime ?? 0);
    wordSyncControllerRef.current?.snap();
  }, [emitAudioProgress, hasTimeline, updateSentenceForTime, updateActiveGateFromTime]);

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
    inlineAudioPlayingRef.current = false;
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
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
      if (dictionarySuppressSeekRef.current) {
        return;
      }
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
        isTypingTarget(event.target)
      ) {
        return;
      }
      if (event.shiftKey && event.key?.toLowerCase() === 'h') {
        setFullscreenControlsCollapsed((value) => !value);
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, [isFullscreen]);

  useEffect(() => {
    return () => {
      if (progressTimerRef.current !== null) {
        window.clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const chunkId = chunk?.chunkId ?? chunk?.rangeFragment ?? null;
    if (lastChunkIdRef.current !== chunkId) {
      revealMemoryRef.current = {
        sentenceIdx: null,
        counts: { original: 0, translit: 0, translation: 0 },
      };
      lastChunkIdRef.current = chunkId;
      lastChunkTimeRef.current = 0;
      setChunkTime(0);
    }
  }, [chunk?.chunkId, chunk?.rangeFragment]);

  useEffect(() => {
    if (chunkTime + 0.05 < lastChunkTimeRef.current) {
      revealMemoryRef.current = {
        sentenceIdx: null,
        counts: { original: 0, translit: 0, translation: 0 },
      };
    }
    lastChunkTimeRef.current = chunkTime;
  }, [chunkTime]);

  const rootClassName = [
    'player-panel__interactive',
    isFullscreen ? 'player-panel__interactive--fullscreen' : null,
  ]
    .filter(Boolean)
    .join(' ');

  const activeSentenceNumber = useMemo(() => {
    const entries = chunk?.sentences ?? null;
    if (entries && entries.length > 0) {
      const entry = entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))];
      const rawSentenceNumber = entry?.sentence_number ?? null;
      if (typeof rawSentenceNumber === 'number' && Number.isFinite(rawSentenceNumber)) {
        return Math.max(1, Math.trunc(rawSentenceNumber));
      }
    }
    const start = chunk?.startSentence ?? null;
    if (typeof start === 'number' && Number.isFinite(start)) {
      return Math.max(1, Math.trunc(start) + Math.max(0, Math.trunc(activeSentenceIndex)));
    }
    return Math.max(1, Math.trunc(activeSentenceIndex) + 1);
  }, [activeSentenceIndex, chunk?.sentences, chunk?.startSentence]);

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
    const padded = String(activeSentenceNumber).padStart(5, '0');
    return `media/images/${rangeFragment}/sentence_${padded}.png`;
  }, [activeSentenceIndex, activeSentenceNumber, chunk?.rangeFragment, chunk?.sentences, jobId]);

  const activeSentenceImageUrl = useMemo(() => {
    const path = activeSentenceImagePath;
    if (!path) {
      return null;
    }
    if (path.includes('://')) {
      return path;
    }
    if (!jobId) {
      return null;
    }
    try {
      const token =
        imageRefreshToken > 0 ? `v=${encodeURIComponent(String(imageRefreshToken))}` : null;
      const decorated = token ? (path.includes('?') ? `${path}&${token}` : `${path}?${token}`) : path;
      return resolveStoragePath(jobId, decorated);
    } catch {
      return null;
    }
  }, [activeSentenceImagePath, imageRefreshToken, jobId]);

  const [activeSentenceImageFailed, setActiveSentenceImageFailed] = useState(false);
  useEffect(() => {
    setActiveSentenceImageFailed(false);
  }, [activeSentenceImageUrl]);

  const handleSentenceImageClick = useCallback(
    (event: ReactMouseEvent) => {
      event.preventDefault();
      event.stopPropagation();
      if (!jobId) {
        return;
      }
      const entries = chunk?.sentences ?? null;
      const entry =
        entries && entries.length > 0
          ? entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))]
          : null;
      const imagePayload = entry?.image ?? null;
      const prompt = typeof imagePayload?.prompt === 'string' ? imagePayload.prompt.trim() : null;
      const negative = typeof imagePayload?.negative_prompt === 'string' ? imagePayload.negative_prompt.trim() : null;
      const sentenceTextRaw = typeof entry?.original?.text === 'string' ? entry.original.text : null;
      const sentenceText =
        typeof sentenceTextRaw === 'string' && sentenceTextRaw.trim() ? sentenceTextRaw.trim() : null;

      openMyPainter({
        followPlayer: false,
        sentence: {
          jobId,
          rangeFragment: chunk?.rangeFragment ?? null,
          sentenceNumber: activeSentenceNumber,
          sentenceText,
          prompt,
          negativePrompt: negative,
          imagePath: activeSentenceImagePath,
        },
      });
    },
    [activeSentenceImagePath, activeSentenceIndex, activeSentenceNumber, chunk?.rangeFragment, chunk?.sentences, jobId, openMyPainter],
  );

  useEffect(() => {
    if (!setPlayerSentence) {
      return;
    }
    if (!jobId) {
      setPlayerSentence(null);
      return;
    }

    const entries = chunk?.sentences ?? null;
    const entry =
      entries && entries.length > 0
        ? entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))]
        : null;
    const imagePayload = entry?.image ?? null;
    const prompt = typeof imagePayload?.prompt === 'string' ? imagePayload.prompt.trim() : null;
    const negative = typeof imagePayload?.negative_prompt === 'string' ? imagePayload.negative_prompt.trim() : null;
    const sentenceTextRaw = typeof entry?.original?.text === 'string' ? entry.original.text : null;
    const sentenceText =
      typeof sentenceTextRaw === 'string' && sentenceTextRaw.trim() ? sentenceTextRaw.trim() : null;

    setPlayerSentence({
      jobId,
      rangeFragment: chunk?.rangeFragment ?? null,
      sentenceNumber: activeSentenceNumber,
      sentenceText,
      prompt,
      negativePrompt: negative,
      imagePath: activeSentenceImagePath,
    });
  }, [
    activeSentenceImagePath,
    activeSentenceIndex,
    activeSentenceNumber,
    chunk?.rangeFragment,
    chunk?.sentences,
    jobId,
    setPlayerSentence,
  ]);

  const overlayAudioEl = playerCore?.getElement() ?? audioRef.current ?? null;
  const showTextPlayer =
    !(legacyWordSyncEnabled && shouldUseWordSync && wordSyncSentences && wordSyncSentences.length > 0) &&
    Boolean(textPlayerSentences && textPlayerSentences.length > 0);
  const pinnedLinguistBubbleNode =
    linguistBubble && linguistBubblePinned ? (
      <div
        ref={linguistBubbleRef}
        className={[
          'player-panel__my-linguist-bubble',
          'player-panel__my-linguist-bubble--docked',
          linguistBubble.status === 'loading' ? 'player-panel__my-linguist-bubble--loading' : null,
          linguistBubble.status === 'error' ? 'player-panel__my-linguist-bubble--error' : null,
        ]
          .filter(Boolean)
          .join(' ')}
        role="dialog"
        aria-label="MyLinguist lookup"
      >
        <div className="player-panel__my-linguist-bubble-header">
          <div className="player-panel__my-linguist-bubble-header-left">
            <span className="player-panel__my-linguist-bubble-title">MyLinguist</span>
            <span className="player-panel__my-linguist-bubble-meta">Model: {linguistBubble.modelLabel}</span>
          </div>
          <div className="player-panel__my-linguist-bubble-actions">
            <button
              type="button"
              className="player-panel__my-linguist-bubble-pin"
              onClick={toggleLinguistBubblePinned}
              aria-label={linguistBubblePinned ? 'Unpin MyLinguist bubble' : 'Pin MyLinguist bubble'}
              aria-pressed={linguistBubblePinned}
              title={linguistBubblePinned ? 'Unpin bubble' : 'Pin bubble'}
            >
              <svg viewBox="0 0 24 24" role="img" focusable="false" aria-hidden="true">
                {linguistBubblePinned ? (
                  <>
                    <path d="M9 3h6l1 6 2 2v2H6v-2l2-2 1-6Z" />
                    <path d="M12 13v8" />
                  </>
                ) : (
                  <>
                    <path d="M9 3h6l1 6 2 2v2H6v-2l2-2 1-6Z" />
                    <path d="M12 13v8" />
                    <path d="M4 4l16 16" />
                  </>
                )}
              </svg>
            </button>
            <button
              type="button"
              className="player-panel__my-linguist-bubble-nav"
              onClick={() => navigateLinguistWord(-1)}
              aria-label="Previous word"
              title="Previous word (Alt+←)"
              disabled={!linguistCanNavigatePrev}
            >
              ←
            </button>
            <button
              type="button"
              className="player-panel__my-linguist-bubble-nav"
              onClick={() => navigateLinguistWord(1)}
              aria-label="Next word"
              title="Next word (Alt+→)"
              disabled={!linguistCanNavigateNext}
            >
              →
            </button>
            <button
              type="button"
              className="player-panel__my-linguist-bubble-speak"
              onClick={handleLinguistSpeak}
              aria-label="Speak selection aloud"
              title="Speak selection aloud"
              disabled={linguistBubble.ttsStatus === 'loading'}
            >
              {linguistBubble.ttsStatus === 'loading' ? '…' : '🔊'}
            </button>
            <button
              type="button"
              className="player-panel__my-linguist-bubble-speak"
              onClick={handleLinguistSpeakSlow}
              aria-label="Speak selection slowly"
              title="Speak slowly (0.5×)"
              disabled={linguistBubble.ttsStatus === 'loading'}
            >
              {linguistBubble.ttsStatus === 'loading' ? '…' : '🐢'}
            </button>
            <button
              type="button"
              className="player-panel__my-linguist-bubble-close"
              onClick={closeLinguistBubble}
              aria-label="Close MyLinguist lookup"
            >
              ✕
            </button>
          </div>
        </div>
        <div
          className={[
            'player-panel__my-linguist-bubble-query',
            containsNonLatinLetters(linguistBubble.fullQuery)
              ? 'player-panel__my-linguist-bubble-query--non-latin'
              : null,
          ]
            .filter(Boolean)
            .join(' ')}
        >
          {linguistBubble.query}
        </div>
        <div className="player-panel__my-linguist-bubble-body">
          {renderWithNonLatinBoost(
            linguistBubble.answer,
            'player-panel__my-linguist-bubble-non-latin',
          )}
        </div>
      </div>
    ) : null;
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
        ? Math.max(Math.trunc(chunk.startSentence), 1)
        : null;

    const currentFromMetadata = (() => {
      if (!Array.isArray(chunk.sentences) || chunk.sentences.length === 0) {
        return null;
      }
      const activeMeta = chunk.sentences[Math.max(0, Math.min(activeSentenceIndex, chunk.sentences.length - 1))];
      const candidate = activeMeta?.sentence_number;
      return typeof candidate === 'number' && Number.isFinite(candidate) ? Math.trunc(candidate) : null;
    })();

    const current =
      start !== null
        ? start + Math.max(activeSentenceIndex, 0)
        : currentFromMetadata;

    const sentenceCountFromChunk =
      typeof chunk.sentenceCount === 'number' && Number.isFinite(chunk.sentenceCount)
        ? Math.max(Math.trunc(chunk.sentenceCount), 0)
        : Array.isArray(chunk.sentences)
          ? chunk.sentences.length
          : null;

    const jobEndFromCount =
      start !== null && sentenceCountFromChunk !== null && sentenceCountFromChunk > 0
        ? start + sentenceCountFromChunk - 1
        : null;

    const jobEndFromMetadata = (() => {
      if (!Array.isArray(chunk.sentences) || chunk.sentences.length === 0) {
        return null;
      }
      const last = chunk.sentences[chunk.sentences.length - 1]?.sentence_number;
      return typeof last === 'number' && Number.isFinite(last) ? Math.trunc(last) : null;
    })();

    const explicitJobEnd =
      typeof jobEndSentence === 'number' && Number.isFinite(jobEndSentence)
        ? Math.max(Math.trunc(jobEndSentence), 1)
        : null;
    const jobEndFromChunk =
      typeof chunk.endSentence === 'number' && Number.isFinite(chunk.endSentence)
        ? Math.max(Math.trunc(chunk.endSentence), start ?? 1)
        : null;
    const jobEnd = explicitJobEnd ?? jobEndFromChunk ?? jobEndFromCount ?? jobEndFromMetadata;

    const resolvedJobStart =
      typeof jobStartSentence === 'number' && Number.isFinite(jobStartSentence)
        ? Math.max(Math.trunc(jobStartSentence), 1)
        : start ?? 1;

    const resolvedBookTotal =
      typeof bookTotalSentences === 'number' && Number.isFinite(bookTotalSentences)
        ? Math.max(Math.trunc(bookTotalSentences), 1)
        : typeof totalSentencesInBook === 'number' && Number.isFinite(totalSentencesInBook)
          ? Math.max(Math.trunc(totalSentencesInBook), 1)
          : null;

    if (current === null) {
      return null;
    }

    const displayCurrent = jobEnd !== null ? Math.min(current, jobEnd) : current;
    const base = jobEnd !== null ? `Playing sentence ${displayCurrent} of ${jobEnd}` : `Playing sentence ${displayCurrent}`;

    const jobPercent = (() => {
      if (jobEnd === null) {
        return null;
      }
      const span = Math.max(jobEnd - resolvedJobStart, 0);
      const ratio = span > 0 ? (displayCurrent - resolvedJobStart) / span : 1;
      if (!Number.isFinite(ratio)) {
        return null;
      }
      return Math.min(Math.max(Math.round(ratio * 100), 0), 100);
    })();

    const bookPercent = (() => {
      if (resolvedBookTotal === null) {
        return null;
      }
      const ratio = resolvedBookTotal > 0 ? displayCurrent / resolvedBookTotal : null;
      if (ratio === null || !Number.isFinite(ratio)) {
        return null;
      }
      return Math.min(Math.max(Math.round(ratio * 100), 0), 100);
    })();

    const suffixParts: string[] = [];
    if (jobPercent !== null) {
      suffixParts.push(`Job ${jobPercent}%`);
    }
    if (bookPercent !== null) {
      suffixParts.push(`Book ${bookPercent}%`);
    }
    const label = suffixParts.length > 0 ? `${base} · ${suffixParts.join(' · ')}` : base;

    return { label };
  }, [activeSentenceIndex, bookTotalSentences, chunk, jobEndSentence, jobStartSentence, totalSentencesInBook]);

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
        className="player-panel__document-body player-panel__interactive-frame"
        style={bodyStyle}
      >
        {showInfoHeader ? (
          <div className="player-panel__player-info-header" aria-hidden="true">
            {hasChannelBug ? <PlayerChannelBug glyph={safeInfoGlyph} label={infoGlyphLabel} /> : null}
            {showCoverArt ? (
              <div className="player-panel__player-info-art" data-variant={resolvedInfoCoverVariant}>
                <img
                  className="player-panel__player-info-art-main"
                  src={resolvedCoverUrl ?? undefined}
                  alt={coverAltText}
                  onError={() => setViewportCoverFailed(true)}
                  loading="lazy"
                />
                {showSecondaryCover ? (
                  <img
                    className="player-panel__player-info-art-secondary"
                    src={resolvedSecondaryCoverUrl ?? undefined}
                    alt=""
                    aria-hidden="true"
                    onError={() => setViewportSecondaryCoverFailed(true)}
                    loading="lazy"
                  />
                ) : null}
              </div>
            ) : null}
            {showTextBadge ? (
              <div className="player-panel__interactive-book-badge player-panel__player-info-badge">
                <div className="player-panel__interactive-book-badge-text">
                  {safeInfoTitle ? (
                    <span className="player-panel__interactive-book-badge-title">{safeInfoTitle}</span>
                  ) : null}
                  {safeInfoMeta ? (
                    <span className="player-panel__interactive-book-badge-meta">{safeInfoMeta}</span>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
        <div
          ref={containerRef}
          className="player-panel__interactive-body"
          data-has-badge={showInfoHeader ? 'true' : undefined}
          data-testid="player-panel-document"
          onScroll={handleScroll}
          onClickCapture={handleLinguistTokenClickCapture}
          onClick={handleInteractiveBackgroundClick}
          onPointerDownCapture={handlePointerDownCapture}
          onPointerMoveCapture={handlePointerMoveCapture}
          onPointerUpCapture={handlePointerUpCaptureWithSelection}
          onPointerCancelCapture={handlePointerCancelCapture}
        >
          {slideIndicator ? (
            <div className="player-panel__interactive-slide-indicator" title={slideIndicator.label}>
              {slideIndicator.label}
            </div>
          ) : null}
          {activeSentenceImageUrl && !activeSentenceImageFailed ? (
            <button
              type="button"
              className="player-panel__interactive-sentence-image"
              onClick={handleSentenceImageClick}
              aria-label="Edit sentence image"
              title="Edit image (MyPainter)"
            >
              <img
                src={activeSentenceImageUrl}
                alt="Sentence illustration"
                loading="lazy"
                decoding="async"
                onError={() => setActiveSentenceImageFailed(true)}
              />
            </button>
          ) : null}
          {legacyWordSyncEnabled && shouldUseWordSync && wordSyncSentences && wordSyncSentences.length > 0 ? null : showTextPlayer ? (
            <TextPlayer
              sentences={textPlayerSentences ?? []}
              onSeek={handleTokenSeek}
              footer={pinnedLinguistBubbleNode}
            />
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
          {linguistBubble && !linguistBubblePinned ? (
            <div
              ref={linguistBubbleRef}
              className={[
                'player-panel__my-linguist-bubble',
                'player-panel__my-linguist-bubble--floating',
                linguistBubble.status === 'loading' ? 'player-panel__my-linguist-bubble--loading' : null,
                linguistBubble.status === 'error' ? 'player-panel__my-linguist-bubble--error' : null,
              ]
                .filter(Boolean)
                .join(' ')}
              data-placement={linguistBubbleFloatingPlacement}
              style={
                linguistBubbleFloatingPosition
                  ? ({
                      top: `${linguistBubbleFloatingPosition.top}px`,
                      left: `${linguistBubbleFloatingPosition.left}px`,
                      bottom: 'auto',
                    } as CSSProperties)
                  : undefined
              }
              role="dialog"
              aria-label="MyLinguist lookup"
            >
              <div className="player-panel__my-linguist-bubble-header">
                <div className="player-panel__my-linguist-bubble-header-left">
                  <span className="player-panel__my-linguist-bubble-title">MyLinguist</span>
                  <span className="player-panel__my-linguist-bubble-meta">Model: {linguistBubble.modelLabel}</span>
                </div>
                <div className="player-panel__my-linguist-bubble-actions">
                  <button
                    type="button"
                    className="player-panel__my-linguist-bubble-pin"
                    onClick={toggleLinguistBubblePinned}
                    aria-label={linguistBubblePinned ? 'Unpin MyLinguist bubble' : 'Pin MyLinguist bubble'}
                    aria-pressed={linguistBubblePinned}
                    title={linguistBubblePinned ? 'Unpin bubble' : 'Pin bubble'}
                  >
                    <svg viewBox="0 0 24 24" role="img" focusable="false" aria-hidden="true">
                      <path d="M9 3h6l1 6 2 2v2H6v-2l2-2 1-6Z" />
                      <path d="M12 13v8" />
                      <path d="M4 4l16 16" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    className="player-panel__my-linguist-bubble-nav"
                    onClick={() => navigateLinguistWord(-1)}
                    aria-label="Previous word"
                    title="Previous word (Alt+←)"
                    disabled={!linguistCanNavigatePrev}
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    className="player-panel__my-linguist-bubble-nav"
                    onClick={() => navigateLinguistWord(1)}
                    aria-label="Next word"
                    title="Next word (Alt+→)"
                    disabled={!linguistCanNavigateNext}
                  >
                    →
                  </button>
                    <button
                      type="button"
                      className="player-panel__my-linguist-bubble-speak"
                      onClick={handleLinguistSpeak}
                      aria-label="Speak selection aloud"
                      title="Speak selection aloud"
                      disabled={linguistBubble.ttsStatus === 'loading'}
                    >
                      {linguistBubble.ttsStatus === 'loading' ? '…' : '🔊'}
                    </button>
                    <button
                      type="button"
                      className="player-panel__my-linguist-bubble-speak"
                      onClick={handleLinguistSpeakSlow}
                      aria-label="Speak selection slowly"
                      title="Speak slowly (0.5×)"
                      disabled={linguistBubble.ttsStatus === 'loading'}
                    >
                      {linguistBubble.ttsStatus === 'loading' ? '…' : '🐢'}
                    </button>
                    <button
                      type="button"
                      className="player-panel__my-linguist-bubble-close"
                      onClick={closeLinguistBubble}
                      aria-label="Close MyLinguist lookup"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div
                className={[
                  'player-panel__my-linguist-bubble-query',
                  containsNonLatinLetters(linguistBubble.fullQuery)
                    ? 'player-panel__my-linguist-bubble-query--non-latin'
                    : null,
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {linguistBubble.query}
              </div>
              <div className="player-panel__my-linguist-bubble-body">
                {renderWithNonLatinBoost(
                  linguistBubble.answer,
                  'player-panel__my-linguist-bubble-non-latin',
                )}
              </div>
            </div>
          ) : null}
        </div>
        {pinnedLinguistBubbleNode && !showTextPlayer ? (
          <div className="player-panel__my-linguist-dock" aria-label="MyLinguist lookup dock">
            {pinnedLinguistBubbleNode}
          </div>
        ) : null}
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
