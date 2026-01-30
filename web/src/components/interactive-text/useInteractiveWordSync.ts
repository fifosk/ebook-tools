import { useCallback, useEffect, useRef } from 'react';
import type { JobTimingResponse, TrackTimingPayload } from '../../api/dtos';
import type { WordIndex } from '../../lib/timing/wordSync';
import type { MediaClock } from '../../hooks/useLiveMedia';
import type { PlayerCoreHandle } from '../../player/PlayerCore';
import { start as startAudioSync, stop as stopAudioSync } from '../../player/AudioSyncController';
import { timingStore } from '../../stores/timingStore';
import type { TimingPayload } from '../../types/timing';
import { WORD_SYNC } from '../player-panel/constants';
import { EMPTY_TIMING_PAYLOAD } from './constants';
import type { SentenceGate, WordSyncController, WordSyncSentence } from './types';
import { buildSentenceGateList, computeTimingMetrics } from './utils';
import { createWordSyncController } from './wordSyncController';

type UseInteractiveWordSyncArgs = {
  audioRef: React.MutableRefObject<HTMLAudioElement | null>;
  playerCore: PlayerCoreHandle | null;
  containerRef: React.MutableRefObject<HTMLDivElement | null>;
  clockRef: React.MutableRefObject<MediaClock>;
  followHighlightEnabled: boolean;
  timingPayload: TimingPayload | null;
  timingDiagnostics: { policy: string | null } | null;
  effectivePlaybackRate: number;
  shouldUseWordSync: boolean;
  legacyWordSyncEnabled: boolean;
  activeWordSyncTrack: TrackTimingPayload | null;
  activeWordIndex: WordIndex | null;
  jobId: string | null;
  resolvedTimingTrack: 'mix' | 'translation' | 'original';
  jobTimingResponse: JobTimingResponse | null;
  wordSyncSentences: WordSyncSentence[] | null;
};

type UseInteractiveWordSyncResult = {
  wordSyncControllerRef: React.MutableRefObject<WordSyncController | null>;
  updateActiveGateFromTime: (mediaTime: number) => void;
};

export function useInteractiveWordSync({
  audioRef,
  playerCore,
  containerRef,
  clockRef,
  followHighlightEnabled,
  timingPayload,
  timingDiagnostics,
  effectivePlaybackRate,
  shouldUseWordSync,
  legacyWordSyncEnabled,
  activeWordSyncTrack,
  activeWordIndex,
  jobId,
  resolvedTimingTrack,
  jobTimingResponse,
  wordSyncSentences,
}: UseInteractiveWordSyncArgs): UseInteractiveWordSyncResult {
  const tokenElementsRef = useRef<Map<string, HTMLElement>>(new Map());
  const sentenceElementsRef = useRef<Map<number, HTMLElement>>(new Map());
  const wordSyncControllerRef = useRef<WordSyncController | null>(null);
  const gateListRef = useRef<SentenceGate[]>([]);
  const diagnosticsSignatureRef = useRef<string | null>(null);
  const highlightPolicyRef = useRef<string | null>(null);

  useEffect(() => {
    highlightPolicyRef.current = timingDiagnostics?.policy ?? null;
  }, [timingDiagnostics]);

  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      wordSyncControllerRef.current = null;
      return;
    }
    const controller = createWordSyncController({
      containerRef,
      tokenElementsRef,
      sentenceElementsRef,
      clockRef,
      config: WORD_SYNC,
      followHighlight: followHighlightEnabled,
      isPaused: () => {
        const element = audioRef.current;
        return !element || element.paused;
      },
      debugOverlay: { policyRef: highlightPolicyRef },
    });
    wordSyncControllerRef.current = controller;
    return () => {
      controller.destroy();
      wordSyncControllerRef.current = null;
    };
  }, [audioRef, clockRef, containerRef, followHighlightEnabled, legacyWordSyncEnabled]);

  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      return;
    }
    wordSyncControllerRef.current?.setFollowHighlight(followHighlightEnabled);
  }, [followHighlightEnabled, legacyWordSyncEnabled]);

  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      return;
    }
    const controller = wordSyncControllerRef.current;
    if (!controller) {
      return;
    }
    if (!shouldUseWordSync || !activeWordSyncTrack || !activeWordIndex) {
      controller.stop();
      controller.setTrack(null, null);
      return;
    }
    controller.setTrack(activeWordSyncTrack, activeWordIndex);
    controller.snap();
    const element = audioRef.current;
    if (element && !element.paused) {
      controller.start();
    }
    return () => {
      controller.stop();
    };
  }, [activeWordIndex, activeWordSyncTrack, audioRef, shouldUseWordSync, legacyWordSyncEnabled]);

  useEffect(() => {
    const clearTiming = () => {
      timingStore.setPayload(EMPTY_TIMING_PAYLOAD);
      timingStore.setLast(null);
    };
    if (!shouldUseWordSync || !timingPayload) {
      clearTiming();
      return clearTiming;
    }
    // Use setPayloadPreservingHit to avoid flickering during track transitions
    // This emits only once with the hit preserved (if segment index is valid)
    timingStore.setPayloadPreservingHit(timingPayload);
    return clearTiming;
  }, [shouldUseWordSync, timingPayload]);

  useEffect(() => {
    if (!shouldUseWordSync || !timingPayload) {
      return;
    }
    timingStore.setRate(effectivePlaybackRate);
  }, [effectivePlaybackRate, shouldUseWordSync, timingPayload]);

  useEffect(() => {
    if (!playerCore || !shouldUseWordSync || !timingPayload) {
      stopAudioSync();
      return () => {
        stopAudioSync();
      };
    }
    startAudioSync(playerCore);
    return () => {
      stopAudioSync();
    };
  }, [playerCore, shouldUseWordSync, timingPayload]);

  useEffect(() => {
    if (!playerCore) {
      return;
    }
    playerCore.setRate(effectivePlaybackRate);
  }, [effectivePlaybackRate, playerCore]);

  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      tokenElementsRef.current.clear();
      sentenceElementsRef.current.clear();
      return;
    }
    if (shouldUseWordSync) {
      return;
    }
    tokenElementsRef.current.forEach((element) => {
      element.classList.remove('is-active');
      element.classList.remove('is-visited');
    });
    tokenElementsRef.current.clear();
    sentenceElementsRef.current.clear();
  }, [legacyWordSyncEnabled, shouldUseWordSync]);

  useEffect(() => {
    if (!legacyWordSyncEnabled || !shouldUseWordSync) {
      return;
    }
    const controller = wordSyncControllerRef.current;
    if (!controller) {
      return;
    }
    if (typeof window === 'undefined') {
      controller.snap();
      return;
    }
    const handle = window.requestAnimationFrame(() => {
      controller.snap();
    });
    return () => {
      window.cancelAnimationFrame(handle);
    };
  }, [legacyWordSyncEnabled, shouldUseWordSync, wordSyncSentences]);

  useEffect(() => {
    gateListRef.current = buildSentenceGateList(timingPayload);
    timingStore.setActiveGate(null);
  }, [timingPayload]);

  useEffect(() => {
    if (!jobId || !timingPayload) {
      diagnosticsSignatureRef.current = null;
      return;
    }
    const signature = [
      jobId,
      timingPayload.trackKind,
      String(timingPayload.segments.length),
      resolvedTimingTrack,
      jobTimingResponse?.highlighting_policy ?? 'unknown',
    ].join('|');
    if (diagnosticsSignatureRef.current === signature) {
      return;
    }
    diagnosticsSignatureRef.current = signature;
    if (!timingPayload.segments.length) {
      return;
    }
    const policy =
      typeof jobTimingResponse?.highlighting_policy === 'string' &&
      jobTimingResponse.highlighting_policy.trim()
        ? jobTimingResponse.highlighting_policy.trim()
        : null;
    const metrics = computeTimingMetrics(timingPayload, timingPayload.playbackRate);
    if (import.meta.env.DEV) {
      console.info('[Highlight diagnostics]', {
        jobId,
        trackKind: timingPayload.trackKind,
        policy: policy ?? 'unknown',
        avgTokenMs: Number(metrics.avgTokenMs.toFixed(2)),
        tempoRatio: Number(metrics.tempoRatio.toFixed(3)),
        uniformVsRealMeanDeltaMs: Number(metrics.uniformVsRealMeanDeltaMs.toFixed(2)),
        totalDriftMs: Number(metrics.totalDriftMs.toFixed(2)),
        track: resolvedTimingTrack,
      });
    }
  }, [jobId, timingPayload, resolvedTimingTrack, jobTimingResponse]);

  const updateActiveGateFromTime = useCallback((mediaTime: number) => {
    const gates = gateListRef.current;
    if (!gates.length) {
      timingStore.setActiveGate(null);
      return;
    }
    let candidate: SentenceGate | null = null;
    for (const gate of gates) {
      if (mediaTime >= gate.start && mediaTime <= gate.end) {
        candidate = gate;
        break;
      }
      if (mediaTime < gate.start) {
        candidate = gate;
        break;
      }
    }
    timingStore.setActiveGate(candidate);
  }, []);

  return {
    wordSyncControllerRef,
    updateActiveGateFromTime,
  };
}
