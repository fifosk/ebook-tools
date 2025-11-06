import type { Hit, TimingPayload } from '../types/timing';

type Listener = (state: TimingState) => void;

export interface TimingState {
  payload?: TimingPayload;
  last: Hit | null;
  rate: number;
}

const state: TimingState = {
  payload: undefined,
  last: null,
  rate: 1,
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

  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    listener(state);
    return () => {
      listeners.delete(listener);
    };
  },
};
