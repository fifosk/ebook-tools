/**
 * Playback analytics API endpoints.
 */

import { apiFetch } from './base';

export interface PlaybackHeartbeatPayload {
  job_id: string;
  language: string;
  track_kind: 'original' | 'translation';
  delta_seconds: number;
}

/**
 * Send a playback heartbeat reporting listened seconds.
 * Fire-and-forget — errors are silently swallowed.
 */
export async function sendPlaybackHeartbeat(
  payload: PlaybackHeartbeatPayload,
): Promise<void> {
  try {
    await apiFetch('/api/playback/heartbeat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch {
    // Fire-and-forget — never block playback on analytics failures.
  }
}
