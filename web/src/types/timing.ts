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

export type Mode = "orig+trans" | "trans-only";

export type Slide = {
  idx: number;
  orig?: SentT;
  trans?: SentT;
  gate: { start: number; end: number }; // UI time window
};
