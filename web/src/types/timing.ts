export type TrackKind = 'translation_only' | 'original_translation_combined';

export interface WordToken {
  id: string; // stable token id
  text: string; // token text (word or punctuation)
  t0: number; // start time (s)
  t1: number; // end time (s)
  lane: 'orig' | 'tran'; // for combined interleaving
  segId: string; // sentence/segment id
  sentenceIdx?: number;
  startGate?: number;
  endGate?: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
  validation?: {
    drift?: number;
    count?: number;
  };
}

export interface Segment {
  id: string;
  t0: number;
  t1: number;
  tokens: WordToken[];
  sentenceIdx?: number;
  gateStart?: number;
  gateEnd?: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
}

export interface TimingPayload {
  trackKind: TrackKind;
  playbackRate?: number; // optional runtime override
  segments: Segment[]; // already loaded for a view/chunk
}

export interface Hit {
  segIndex: number;
  tokIndex: number;
  lane?: 'mix' | 'translation';
}
