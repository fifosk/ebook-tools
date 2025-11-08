import type { Hit, TimingPayload } from '../types/timing';

type Listener = (state: TimingState) => void;

export type Gate = {
  start: number;
  end: number;
  sentenceIdx: number;
  segmentIndex: number;
  pauseBeforeMs?: number;
  pauseAfterMs?: number;
};

export interface TimingState {
  payload?: TimingPayload;
  last: Hit | null;
  rate: number;
  activeGate: Gate | null;
  audioEl: HTMLAudioElement | null;
}

const state: TimingState = {
  payload: undefined,
  last: null,
  rate: 1,
  activeGate: null,
  audioEl: null,
};

const listeners = new Set<Listener>();

function emit(): void {
  for (const listener of listeners) {
    listener(state);
  }
}

export const timingStore = {
  setPayload(payload: TimingPayload): void {
    state.payload = payload;
    state.last = null;
    state.activeGate = null;
    emit();
  },

  get(): TimingState {
    return state;
  },

  setLast(hit: Hit | null): void {
    if (state.last === hit) {
      return;
    }
    state.last = hit;
    emit();
  },

  setRate(rate: number): void {
    if (!Number.isFinite(rate) || rate <= 0) {
      return;
    }
    if (state.rate === rate) {
      return;
    }
    state.rate = rate;
    emit();
  },

  setActiveGate(gate: Gate | null): void {
    const current = state.activeGate;
    const unchanged =
      current === gate ||
      (current &&
        gate &&
        current.segmentIndex === gate.segmentIndex &&
        Math.abs(current.start - gate.start) < 0.0005 &&
        Math.abs(current.end - gate.end) < 0.0005);
    if (unchanged) {
      return;
    }
    state.activeGate = gate;
    emit();
  },

  setAudioEl(element: HTMLAudioElement | null): void {
    if (state.audioEl === element) {
      return;
    }
    state.audioEl = element;
    emit();
  },

  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    listener(state);
    return () => {
      listeners.delete(listener);
    };
  },
};
