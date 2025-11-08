import type { PlayerCoreHandle } from './PlayerCore';
import { timingStore } from '../stores/timingStore';
import type { Gate } from '../stores/timingStore';
import type { Hit, TimingPayload } from '../types/timing';
import { WORD_SYNC } from '../components/player-panel/constants';

type DebugToggleConfig = {
  enabled?: boolean;
  showGates?: boolean;
  showPauses?: boolean;
  showDrift?: boolean;
};

declare global {
  interface Window {
    __HL_DEBUG__?: DebugToggleConfig;
    __HL_DEBUG_KEYBOUND__?: boolean;
  }
}

if (typeof window !== 'undefined') {
  const globalWindow = window as Window & { __HL_DEBUG_KEYBOUND__?: boolean };
  if (!globalWindow.__HL_DEBUG_KEYBOUND__) {
    globalWindow.__HL_DEBUG_KEYBOUND__ = true;
    window.addEventListener('keydown', (event) => {
      const key = event.key?.toLowerCase();
      if (!key || !['g', 'p', 'd'].includes(key)) {
        return;
      }
      const debugState = (window.__HL_DEBUG__ = {
        ...(window.__HL_DEBUG__ ?? { enabled: false }),
      });
      debugState.enabled = true;
      if (key === 'g') {
        debugState.showGates = !debugState.showGates;
      } else if (key === 'p') {
        debugState.showPauses = !debugState.showPauses;
      } else if (key === 'd') {
        debugState.showDrift = !debugState.showDrift;
      }
      window.dispatchEvent(new Event('hl_debug_update'));
    });
  }
}

type Unsubscribe = () => void;

type TimelineEntry = {
  segIndex: number;
  tokIndex: number;
  start: number;
  end: number;
};

type TimelineBundle = {
  entries: TimelineEntry[];
  origin: number;
  duration: number;
};

let activeCore: PlayerCoreHandle | null = null;
let unsubscribes: Unsubscribe[] = [];
let rafId: number | null = null;
let fallbackInterval: ReturnType<typeof setInterval> | null = null;
let payloadCache: TimingPayload | undefined;
let timelineBundle: TimelineBundle | null = null;
let timelineCursor = -1;
let lastHit: Hit | null = null;
let detachRateListener: (() => void) | null = null;
const MAX_DRIFT_SECONDS = WORD_SYNC.MAX_LAG_MS / 1000;

type DebugWindow = Window & { __HL_DEBUG__?: { enabled?: boolean } };

function buildTimeline(payload?: TimingPayload): TimelineBundle | null {
  if (!payload || payload.segments.length === 0) {
    return null;
  }

  const raw: TimelineEntry[] = [];
  let earliestStart: number | null = null;

  payload.segments.forEach((segment, segIndex) => {
    if (!segment || !Array.isArray(segment.tokens)) {
      return;
    }
    segment.tokens.forEach((token, tokIndex) => {
      if (!token) {
        return;
      }
      const start = Number(token.t0);
      const end = Number(token.t1);
      if (!Number.isFinite(start) || !Number.isFinite(end)) {
        return;
      }
      const safeStart = Math.max(0, start);
      const safeEnd = Math.max(safeStart + 0.01, end);
      raw.push({
        segIndex,
        tokIndex,
        start: safeStart,
        end: safeEnd,
      });
      if (earliestStart === null || safeStart < earliestStart) {
        earliestStart = safeStart;
      }
    });
  });

  if (raw.length === 0 || earliestStart === null) {
    return null;
  }

  raw.sort((left, right) => {
    if (left.start !== right.start) {
      return left.start - right.start;
    }
    return left.end - right.end;
  });

  const origin = earliestStart ?? 0;
  let lastEnd = 0;
  const normalized = raw.map((entry, index) => {
    let start = entry.start - origin;
    let end = entry.end - origin;
    if (start < 0) {
      start = 0;
      end = Math.max(end, 0.01);
    }
    if (end <= start) {
      end = start + 0.01;
    }
    if (index === 0) {
      lastEnd = end;
      return { ...entry, start, end };
    }
    if (start < lastEnd) {
      const shift = lastEnd - start;
      start += shift;
      end += shift;
    }
    lastEnd = Math.max(lastEnd, end);
    return { ...entry, start, end };
  });

  const totalDuration = normalized.length ? normalized[normalized.length - 1].end : 0;
  return {
    entries: normalized,
    origin,
    duration: totalDuration,
  };
}

function ensureTimeline(payload?: TimingPayload): void {
  if (payloadCache === payload) {
    return;
  }
  payloadCache = payload;
  timelineBundle = buildTimeline(payload);
  timelineCursor = -1;
  lastHit = null;
  timingStore.setLast(null);
}

function clearLoop(): void {
  if (typeof window !== 'undefined' && rafId !== null) {
    window.cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (fallbackInterval !== null) {
    clearInterval(fallbackInterval);
    fallbackInterval = null;
  }
}

function attachRateListener(core: PlayerCoreHandle | null): void {
  if (detachRateListener) {
    detachRateListener();
    detachRateListener = null;
  }
  if (!core || typeof core.getElement !== 'function') {
    return;
  }
  const element = core.getElement();
  if (!element) {
    return;
  }
  const handleRateChange = () => {
    const rate = Number.isFinite(element.playbackRate) && element.playbackRate > 0 ? element.playbackRate : 1;
    timingStore.setRate(rate);
  };
  element.addEventListener('ratechange', handleRateChange);
  detachRateListener = () => {
    element.removeEventListener('ratechange', handleRateChange);
  };
}

function startLoop(): void {
  clearLoop();
  if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
    const step = () => {
      if (!activeCore) {
        rafId = null;
        return;
      }
      applyTime(activeCore.getCurrentTime());
      rafId = window.requestAnimationFrame(step);
    };
    rafId = window.requestAnimationFrame(step);
    return;
  }

  fallbackInterval = setInterval(() => {
    if (!activeCore) {
      if (fallbackInterval !== null) {
        clearInterval(fallbackInterval);
        fallbackInterval = null;
      }
      return;
    }
    applyTime(activeCore.getCurrentTime());
  }, 16) as ReturnType<typeof setInterval>;
}

function setActiveHit(hit: (Hit & { lane?: 'mix' | 'translation' }) | null): void {
  if (!hit) {
    if (lastHit) {
      lastHit = null;
      timingStore.setLast(null);
    }
    return;
  }
  if (!lastHit || lastHit.segIndex !== hit.segIndex || lastHit.tokIndex !== hit.tokIndex) {
    lastHit = hit;
    timingStore.setLast(hit);
  }
}

function clampHighlightToGateTail(
  gate: Gate,
  payload: TimingPayload | undefined,
  lane: 'mix' | 'translation',
): void {
  if (!payload || !payload.segments.length) {
    setActiveHit(null);
    return;
  }
  const segment = payload.segments[gate.segmentIndex];
  if (!segment || !Array.isArray(segment.tokens) || segment.tokens.length === 0) {
    setActiveHit(null);
    return;
  }
  const lastIndex = segment.tokens.length - 1;
  setActiveHit({ segIndex: gate.segmentIndex, tokIndex: lastIndex, lane });
}

function locateTimelineIndex(time: number): number {
  if (!timelineBundle || timelineBundle.entries.length === 0) {
    return -1;
  }

  const entries = timelineBundle.entries;
  let low = 0;
  let high = entries.length - 1;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const entry = entries[mid];
    if (time < entry.start) {
      high = mid - 1;
      continue;
    }
    if (time >= entry.end) {
      low = mid + 1;
      continue;
    }
    timelineCursor = mid;
    return mid;
  }

  timelineCursor = Math.max(0, Math.min(low, entries.length - 1));
  return -1;
}

function applyTime(time: number): void {
  if (!Number.isFinite(time)) {
    setActiveHit(null);
    return;
  }
  const state = timingStore.get();
  const { payload, activeGate } = state;
  ensureTimeline(payload);
  if (!timelineBundle || timelineBundle.entries.length === 0) {
    setActiveHit(null);
    return;
  }
  const trackLane: 'mix' | 'translation' =
    payload?.trackKind === 'translation_only' ? 'translation' : 'mix';
  const trackDuration = timelineBundle.duration + timelineBundle.origin;
  const audioDuration = activeCore ? activeCore.getDuration() : Number.NaN;
  const maxDuration = Number.isFinite(audioDuration) && audioDuration > 0
    ? Math.min(audioDuration, trackDuration)
    : trackDuration;
  const clampedTime = Math.min(Math.max(time, 0), maxDuration);
  if (activeGate) {
    if (trackLane === 'translation') {
      if (clampedTime < activeGate.start) {
        setActiveHit(null);
        return;
      }
      if (clampedTime >= activeGate.end) {
        clampHighlightToGateTail(activeGate, payload, trackLane);
        return;
      }
    } else {
      if (clampedTime < activeGate.start) {
        setActiveHit(null);
        return;
      }
      if (clampedTime >= activeGate.end) {
        clampHighlightToGateTail(activeGate, payload, trackLane);
        return;
      }
    }
  }
  const localTime = Math.max(0, clampedTime - timelineBundle.origin);
  const index = locateTimelineIndex(localTime);
  if (index === -1) {
    if (activeGate && trackLane === 'translation' && clampedTime >= (activeGate?.end ?? 0)) {
      clampHighlightToGateTail(activeGate, payload, trackLane);
      return;
    }
    setActiveHit(null);
    return;
  }
  const entry = timelineBundle.entries[index];
  const withinEntry = localTime >= entry.start && localTime < entry.end;
  if (!withinEntry) {
    const driftSeconds = Math.min(
      Math.abs(localTime - entry.start),
      Math.abs(localTime - entry.end),
    );
    if (driftSeconds > MAX_DRIFT_SECONDS) {
      timelineCursor = -1;
      const snapIndex = locateTimelineIndex(localTime);
      if (snapIndex !== -1) {
        const snapped = timelineBundle.entries[snapIndex];
        setActiveHit({ segIndex: snapped.segIndex, tokIndex: snapped.tokIndex });
        return;
      }
    }
    setActiveHit(null);
    return;
  }
  setActiveHit({ segIndex: entry.segIndex, tokIndex: entry.tokIndex, lane: trackLane });
}

function handleSeek(): void {
  if (!activeCore) {
    return;
  }
  timelineCursor = -1;
  setActiveHit(null);
  applyTime(activeCore.getCurrentTime());
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
  attachRateListener(core);
  timingStore.setRate(core.getRate());
  applyTime(core.getCurrentTime());
  startLoop();
  unsubscribes = [core.on('seeked', handleSeek), core.on('rate', handleRate)];
}

export function stop(): void {
  clearLoop();
  if (unsubscribes.length > 0) {
    unsubscribes.forEach((unsubscribe) => {
      try {
        unsubscribe();
      } catch {
        // ignore
      }
    });
  }
  unsubscribes = [];
  activeCore = null;
  attachRateListener(null);
  timelineBundle = null;
  payloadCache = undefined;
  timelineCursor = -1;
  setActiveHit(null);
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

export function enableHighlightDebugOverlay(): () => void {
  if (
    typeof window === 'undefined' ||
    typeof document === 'undefined' ||
    process.env.NODE_ENV === 'production'
  ) {
    return () => undefined;
  }
  const globalWindow = window as DebugWindow;
  if (!globalWindow.__HL_DEBUG__?.enabled) {
    return () => undefined;
  }

  let overlay: HTMLElement | null = document.getElementById('hl-debug-overlay');
  let created = false;
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'hl-debug-overlay';
    overlay.style.cssText =
      'position:fixed;bottom:10px;right:10px;background:#0008;color:#0f0;padding:6px 10px;font:12px monospace;z-index:9999;';
    document.body.appendChild(overlay);
    created = true;
  }

  let frame = 0;
  const unsubscribe = timingStore.subscribe((state) => {
    frame += 1;
    const segIndex = state.last?.segIndex ?? -1;
    const tokIndex = state.last?.tokIndex ?? -1;
    if (overlay) {
      overlay.textContent = `frame:${frame} seg:${segIndex} tok:${tokIndex}`;
    }
  });

  return () => {
    unsubscribe();
    if (overlay && created && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
  };
}

export const __TESTING__ = {
  applyTime,
};
