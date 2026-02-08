/**
 * Hook that sends periodic playback heartbeats to the backend.
 *
 * While `isPlaying` is true, accumulates elapsed seconds and sends a
 * heartbeat every HEARTBEAT_INTERVAL_MS.  Flushes remaining time on
 * `pagehide` or component unmount.
 */

import { useCallback, useEffect, useRef } from 'react';
import { sendPlaybackHeartbeat, type PlaybackHeartbeatPayload } from '../api/client/playback';

/** How often to send a heartbeat (ms). */
const HEARTBEAT_INTERVAL_MS = 30_000;

/** Minimum delta worth sending (avoid noise from tiny fractions). */
const MIN_DELTA_SECONDS = 1;

export interface UsePlaybackHeartbeatArgs {
  /** Current job ID. Null/undefined disables the heartbeat. */
  jobId: string | null | undefined;
  /** ISO language code of the active audio track. */
  language: string | null;
  /** Which track kind is currently playing. */
  trackKind: 'original' | 'translation' | null;
  /** Whether audio is currently playing. */
  isPlaying: boolean;
}

export function usePlaybackHeartbeat({
  jobId,
  language,
  trackKind,
  isPlaying,
}: UsePlaybackHeartbeatArgs): void {
  const accumulatedRef = useRef(0);
  const lastTickRef = useRef<number | null>(null);

  // Keep current values in refs so the flush callback doesn't need deps.
  const jobIdRef = useRef(jobId);
  const languageRef = useRef(language);
  const trackKindRef = useRef(trackKind);

  jobIdRef.current = jobId;
  languageRef.current = language;
  trackKindRef.current = trackKind;

  const flush = useCallback(() => {
    const delta = accumulatedRef.current;
    const jid = jobIdRef.current;
    const lang = languageRef.current;
    const tk = trackKindRef.current;

    if (delta < MIN_DELTA_SECONDS || !jid || !lang || !tk) return;

    accumulatedRef.current = 0;
    sendPlaybackHeartbeat({
      job_id: jid,
      language: lang,
      track_kind: tk,
      delta_seconds: Math.round(delta),
    });
  }, []);

  // Accumulate elapsed time while playing.
  useEffect(() => {
    if (!isPlaying || !jobId || !language || !trackKind) {
      lastTickRef.current = null;
      return;
    }

    lastTickRef.current = performance.now();

    const timer = setInterval(() => {
      const now = performance.now();
      if (lastTickRef.current !== null) {
        const elapsedSec = (now - lastTickRef.current) / 1000;
        accumulatedRef.current += elapsedSec;
      }
      lastTickRef.current = now;
    }, 1000);

    return () => clearInterval(timer);
  }, [isPlaying, jobId, language, trackKind]);

  // Periodic heartbeat sender.
  useEffect(() => {
    if (!isPlaying || !jobId) return;

    const timer = setInterval(flush, HEARTBEAT_INTERVAL_MS);
    return () => {
      clearInterval(timer);
      flush(); // flush remaining on cleanup
    };
  }, [isPlaying, jobId, flush]);

  // Flush on pagehide (tab close / navigation).
  useEffect(() => {
    const handler = () => flush();
    window.addEventListener('pagehide', handler);
    return () => window.removeEventListener('pagehide', handler);
  }, [flush]);
}
