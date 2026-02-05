import type { PauseTiming, TrackTimingPayload, WordTiming } from '../../api/dtos';
import { lowerBound as genericLowerBound } from './timeSearch';

export type TimelineEventKind = 'on' | 'off';

export interface TimelineEvent {
  kind: TimelineEventKind;
  id: string;
  t: number;
}

export interface WordIndex {
  byId: Map<string, WordTiming>;
  bySentence: Map<number, string[]>;
  events: TimelineEvent[];
  pauses: PauseTiming[];
  words: WordTiming[];
  trackType: TrackTimingPayload['trackType'];
  chunkId: string;
  trackOffset: number;
  tempoFactor: number;
  version: string;
}

const MIN_DURATION = 1e-4;

function sanitiseWord(word: WordTiming): WordTiming | null {
  if (!word || typeof word !== 'object' || typeof word.id !== 'string' || !word.id) {
    return null;
  }
  const t0 = Number(word.t0);
  const t1 = Number(word.t1);
  if (!Number.isFinite(t0) || !Number.isFinite(t1)) {
    return null;
  }
  const sentenceId = Number(word.sentenceId);
  const tokenIdx = Number(word.tokenIdx);
  if (!Number.isFinite(sentenceId) || !Number.isFinite(tokenIdx)) {
    return null;
  }
  const lang = word.lang === 'orig' || word.lang === 'trans' || word.lang === 'xlit'
    ? word.lang
    : null;
  if (!lang) {
    return null;
  }
  const boundedStart = t0 < 0 ? 0 : t0;
  let boundedEnd = t1 < boundedStart ? boundedStart : t1;
  if (boundedEnd - boundedStart < MIN_DURATION) {
    boundedEnd = boundedStart + MIN_DURATION;
  }
  return {
    id: word.id,
    sentenceId: Math.trunc(sentenceId),
    tokenIdx: Math.trunc(tokenIdx),
    text: typeof word.text === 'string' ? word.text : '',
    lang,
    t0: boundedStart,
    t1: boundedEnd,
  };
}

function sanitisePause(pause: PauseTiming): PauseTiming | null {
  if (!pause || typeof pause !== 'object') {
    return null;
  }
  const t0 = Number(pause.t0);
  const t1 = Number(pause.t1);
  if (!Number.isFinite(t0) || !Number.isFinite(t1)) {
    return null;
  }
  const start = t0 < 0 ? 0 : t0;
  const end = t1 < start ? start : t1;
  const reason =
    pause.reason === 'silence' || pause.reason === 'tempo' || pause.reason === 'gap'
      ? pause.reason
      : undefined;
  return {
    t0: start,
    t1: end,
    reason,
  };
}

export function buildWordIndex(payload: TrackTimingPayload): WordIndex {
  const byId = new Map<string, WordTiming>();
  const bySentence = new Map<number, string[]>();
  const events: TimelineEvent[] = [];

  payload.words.forEach((word) => {
    const normalised = sanitiseWord(word);
    if (!normalised) {
      return;
    }
    byId.set(normalised.id, normalised);
    const sentenceList = bySentence.get(normalised.sentenceId);
    if (sentenceList) {
      sentenceList.push(normalised.id);
    } else {
      bySentence.set(normalised.sentenceId, [normalised.id]);
    }
    events.push({ kind: 'on', id: normalised.id, t: normalised.t0 });
    events.push({ kind: 'off', id: normalised.id, t: normalised.t1 });
  });

  bySentence.forEach((ids, sentenceId) => {
    ids.sort((leftId, rightId) => {
      const left = byId.get(leftId);
      const right = byId.get(rightId);
      if (left && right) {
        if (left.tokenIdx !== right.tokenIdx) {
          return left.tokenIdx - right.tokenIdx;
        }
        if (left.t0 !== right.t0) {
          return left.t0 - right.t0;
        }
      }
      if (left && !right) {
        return -1;
      }
      if (!left && right) {
        return 1;
      }
      return leftId.localeCompare(rightId);
    });
    bySentence.set(sentenceId, ids);
  });

  events.sort((a, b) => {
    if (a.t !== b.t) {
      return a.t - b.t;
    }
    if (a.kind === b.kind) {
      return a.id.localeCompare(b.id);
    }
    return a.kind === 'off' ? -1 : 1;
  });

  const pauses =
    Array.isArray(payload.pauses) && payload.pauses.length > 0
      ? payload.pauses
          .map(sanitisePause)
          .filter((pause): pause is PauseTiming => pause !== null)
          .sort((left, right) => {
            if (left.t0 !== right.t0) {
              return left.t0 - right.t0;
            }
            return left.t1 - right.t1;
          })
      : [];

  const words = Array.from(byId.values()).sort((left, right) => {
    if (left.t0 !== right.t0) {
      return left.t0 - right.t0;
    }
    if (left.t1 !== right.t1) {
      return left.t1 - right.t1;
    }
    if (left.sentenceId !== right.sentenceId) {
      return left.sentenceId - right.sentenceId;
    }
    if (left.tokenIdx !== right.tokenIdx) {
      return left.tokenIdx - right.tokenIdx;
    }
    return left.id.localeCompare(right.id);
  });

  return {
    byId,
    bySentence,
    events,
    pauses,
    words,
    trackType: payload.trackType,
    chunkId: payload.chunkId,
    trackOffset: payload.trackOffset,
    tempoFactor: payload.tempoFactor,
    version: payload.version,
  };
}

export function lowerBound(events: TimelineEvent[], time: number): number {
  const target = Number.isFinite(time) ? time : 0;
  return genericLowerBound(events, target, (e) => e.t);
}

export function collectActiveWordIds(index: WordIndex, time: number): string[] {
  const target = Number.isFinite(time) ? time : 0;
  const active: string[] = [];
  index.words.forEach((word) => {
    if (word.t0 <= target && target < word.t1) {
      active.push(word.id);
    }
  });
  return active;
}
