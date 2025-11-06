import type { PlayerCoreHandle } from './PlayerCore';
import { timingStore } from '../stores/timingStore';
import { findNearestToken, isLargeSeek } from '../utils/timingSearch';
import type { Hit } from '../types/timing';

type Unsubscribe = () => void;

let activeCore: PlayerCoreHandle | null = null;
let unsubscribes: Unsubscribe[] = [];
let lastHit: Hit | null = null;
let lastTime = 0;
let lastWallClock = 0;

type DebugCounterKey = 'driftCorrections' | 'largeSeeks' | 'frameDrops';

type DebugCounters = {
  driftCorrections: number;
  largeSeeks: number;
  frameDrops: number;
  enabled: boolean;
  lastLog: number;
};

type DebugWindow = Window & { __HL_DEBUG__?: DebugCounters };

const debugCounters = initDebugCounters();

function initDebugCounters(): DebugCounters | null {
  if (typeof window === 'undefined' || process.env.NODE_ENV === 'production') {
    return null;
  }
  const globalWindow = window as DebugWindow;
  if (!globalWindow.__HL_DEBUG__) {
    globalWindow.__HL_DEBUG__ = {
      driftCorrections: 0,
      largeSeeks: 0,
      frameDrops: 0,
      enabled: false,
      lastLog: 0,
    };
  }
  return globalWindow.__HL_DEBUG__;
}

function incrementCounter(key: DebugCounterKey): void {
  if (!debugCounters) {
    return;
  }
  debugCounters[key] += 1;
  maybeLogCounters();
}

function maybeLogCounters(): void {
  if (!debugCounters || !debugCounters.enabled) {
    return;
  }
  const now =
    typeof performance !== 'undefined' && typeof performance.now === 'function'
      ? performance.now()
      : Date.now();
  if (now - debugCounters.lastLog < 5000) {
    return;
  }
  debugCounters.lastLog = now;
  // eslint-disable-next-line no-console
  console.debug('[HL_DEBUG]', {
    driftCorrections: debugCounters.driftCorrections,
    largeSeeks: debugCounters.largeSeeks,
    frameDrops: debugCounters.frameDrops,
  });
}

function compareHits(next: Hit, prev: Hit): number {
  if (next.segIndex !== prev.segIndex) {
    return next.segIndex - prev.segIndex;
  }
  return next.tokIndex - prev.tokIndex;
}

function applyTime(time: number): void {
  if (debugCounters) {
    const now =
      typeof performance !== 'undefined' && typeof performance.now === 'function'
        ? performance.now()
        : Date.now();
    if (lastWallClock !== 0 && now - lastWallClock > 120) {
      incrementCounter('frameDrops');
    }
    lastWallClock = now;
  }

  if (!Number.isFinite(time)) {
    return;
  }
  const state = timingStore.get();
  const payload = state.payload;
  if (!payload || payload.segments.length === 0) {
    if (state.last) {
      incrementCounter('frameDrops');
    }
    return;
  }
  const hit = findNearestToken(payload, time, lastHit ?? undefined);
  if (hit.segIndex < 0 || hit.tokIndex < 0) {
    if (state.last !== null) {
      incrementCounter('frameDrops');
      timingStore.setLast(null);
    }
    lastHit = null;
    return;
  }

  if (lastHit && compareHits(hit, lastHit) < 0) {
    incrementCounter('driftCorrections');
    return;
  }

  if (!state.last || state.last.segIndex !== hit.segIndex || state.last.tokIndex !== hit.tokIndex) {
    timingStore.setLast(hit);
  }
  lastHit = hit;
}

function handleTime(time: number): void {
  if (isLargeSeek(lastTime, time)) {
    if (timingStore.get().last !== null) {
      timingStore.setLast(null);
    }
    lastHit = null;
    incrementCounter('largeSeeks');
  }
  applyTime(time);
  lastTime = time;
}

function handleSeek(time: number): void {
  timingStore.setLast(null);
  lastHit = null;
  lastTime = time;
  applyTime(time);
}

function handleRate(rate: number): void {
  if (!Number.isFinite(rate) || rate <= 0) {
    return;
  }
  timingStore.setRate(rate);
}

export function start(core: PlayerCoreHandle): void {
  if (activeCore === core) {
    return;
  }
  stop();
  activeCore = core;
  lastTime = core.getCurrentTime();
  const state = timingStore.get();
  lastHit = state.last;
  timingStore.setRate(core.getRate());
  unsubscribes = [
    core.on('time', handleTime),
    core.on('seeked', handleSeek),
    core.on('rate', handleRate),
  ];
}

export function stop(): void {
  if (unsubscribes.length > 0) {
    unsubscribes.forEach((unsubscribe) => {
      try {
        unsubscribe();
      } catch {
        // Ignore teardown errors.
      }
    });
  }
  unsubscribes = [];
  activeCore = null;
  lastHit = null;
  lastTime = 0;
  lastWallClock = 0;
}

export function enableDebugOverlay(elementId = 'debug-drift'): () => void {
  if (typeof document === 'undefined') {
    return () => undefined;
  }
  const element = document.getElementById(elementId);
  if (!element) {
    return () => undefined;
  }
  let frame = 0;
  const unsubscribe = timingStore.subscribe((state) => {
    frame += 1;
    const segIndex = state.last?.segIndex ?? -1;
    const tokIndex = state.last?.tokIndex ?? -1;
    element.innerText = `frame:${frame} seg:${segIndex} tok:${tokIndex}`;
  });
  return () => {
    unsubscribe();
    element.innerText = '';
  };
}

declare global {
  interface Window {
    __HL_DEBUG__?: DebugCounters;
  }
}
