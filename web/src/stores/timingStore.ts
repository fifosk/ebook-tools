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

/**
 * Represents the current state of a playback transition.
 * Used to coordinate track switches and prevent flickering during transitions.
 */
export type PlaybackTransition = {
  /** Current transition state */
  type: 'idle' | 'loading' | 'seeking' | 'transitioning';
  /** Track we're transitioning from (if any) */
  fromTrack?: 'mix' | 'translation' | 'original';
  /** Track we're transitioning to (if any) */
  toTrack?: 'mix' | 'translation' | 'original';
  /** Target sentence index for the transition */
  targetSentenceIndex?: number;
  /** Target seek time for the transition */
  targetTime?: number;
  /** Whether to auto-play after transition completes */
  autoPlay?: boolean;
  /** Timestamp when transition started (for timeout detection) */
  startedAt?: number;
};

export interface TimingState {
  payload?: TimingPayload;
  last: Hit | null;
  rate: number;
  activeGate: Gate | null;
  audioEl: HTMLAudioElement | null;
  /** Current playback transition state */
  transition: PlaybackTransition;
}

const state: TimingState = {
  payload: undefined,
  last: null,
  rate: 1,
  activeGate: null,
  audioEl: null,
  transition: { type: 'idle' },
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

  /**
   * Update the payload while optionally preserving the current hit.
   * This prevents flickering when transitioning between tracks in sequence mode
   * where the same segment index remains valid in the new payload.
   *
   * Important: When the trackKind changes (e.g., from 'original_only' to 'translation_only'),
   * we must NOT preserve the hit because the segment indices refer to different content
   * with different time ranges.
   */
  setPayloadPreservingHit(payload: TimingPayload): void {
    const previousPayload = state.payload;
    const previousHit = state.last;
    state.payload = payload;
    state.activeGate = null;

    // Never preserve hit when trackKind changes - the segments are for a different audio track
    const trackKindChanged = previousPayload?.trackKind !== payload.trackKind;

    // Preserve hit only if:
    // 1. trackKind is the same (same audio track)
    // 2. segment index is still valid in new payload
    if (
      !trackKindChanged &&
      previousHit &&
      previousHit.segIndex >= 0 &&
      payload.segments &&
      previousHit.segIndex < payload.segments.length
    ) {
      // Keep the hit - AudioSyncController will update tokIndex as needed
    } else {
      state.last = null;
    }
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

  /**
   * Begin a playback transition. This is used to coordinate track switches
   * and prevent flickering during transitions.
   */
  beginTransition(transition: Omit<PlaybackTransition, 'type' | 'startedAt'> & { type?: PlaybackTransition['type'] }): void {
    state.transition = {
      ...transition,
      type: transition.type ?? 'transitioning',
      startedAt: Date.now(),
    };
    emit();
  },

  /**
   * Update the current transition state (e.g., from 'loading' to 'seeking').
   */
  updateTransition(updates: Partial<PlaybackTransition>): void {
    if (state.transition.type === 'idle' && !updates.type) {
      // Don't update if we're idle and not changing type
      return;
    }
    state.transition = {
      ...state.transition,
      ...updates,
    };
    emit();
  },

  /**
   * Complete the current transition and return to idle state.
   */
  completeTransition(): void {
    if (state.transition.type === 'idle') {
      return;
    }
    state.transition = { type: 'idle' };
    emit();
  },

  /**
   * Check if a transition is currently in progress.
   */
  isTransitioning(): boolean {
    return state.transition.type !== 'idle';
  },

  /**
   * Get the current transition state.
   */
  getTransition(): PlaybackTransition {
    return state.transition;
  },

  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    listener(state);
    return () => {
      listeners.delete(listener);
    };
  },
};
