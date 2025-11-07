export type WordT = { w: string; s: number; e: number }; // seconds, track-local
export type SentT = {
  sid: number;
  text: string;
  start: number;
  end: number;
  words: WordT[];
  approx_quality?: any;
};

export type TrackTiming = {
  chunk_id: string;
  lang: string;
  policy: string;
  sample_rate: number;
  duration: number;
  sentences: SentT[];
  qa?: any;
};

export type Mode = 'orig+trans' | 'orig+trans+translit' | 'trans-only';

export type Slide = {
  idx: number;
  orig?: SentT;
  trans?: SentT;
  translit?: SentT;
  gate: { start: number; end: number }; // UI time window
};

// ---- legacy player timing contracts ---------------------------------------

export type TrackKind = 'translation_only' | 'original_translation_combined';

export type WordToken = {
  id: string;
  text: string;
  t0: number;
  t1: number;
  lane: 'orig' | 'tran' | 'mix' | 'translation' | 'xlit';
  segId: string;
  sentenceIdx?: number;
  startGate?: number;
  endGate?: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
  validation?: { drift?: number; count?: number };
};

export type Segment = {
  id: string;
  t0: number;
  t1: number;
  tokens: WordToken[];
  sentenceIdx?: number;
  gateStart?: number;
  gateEnd?: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
};

export type TimingPayload = {
  trackKind: TrackKind;
  playbackRate?: number;
  segments: Segment[];
};

export type Hit = {
  segIndex: number;
  tokIndex: number;
  lane?: 'mix' | 'translation';
};
