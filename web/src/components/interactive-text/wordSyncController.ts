import type { MutableRefObject } from 'react';
import type { TrackTimingPayload, WordTiming } from '../../api/dtos';
import type { MediaClock } from '../../hooks/useLiveMedia';
import { collectActiveWordIds, lowerBound, type WordIndex } from '../../lib/timing/wordSync';
import { WORD_SYNC } from '../player-panel/constants';
import type { WordSyncController } from './types';

type HighlightDebugWindow = Window & { __HL_DEBUG__?: { enabled?: boolean; overlay?: boolean } };

export function createNoopWordSyncController(): WordSyncController {
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

export function createWordSyncController(options: {
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
