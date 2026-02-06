/**
 * Canonical playback control interface.
 *
 * Shared across text player (inline audio), video player, and YouTube player
 * to provide a consistent control surface. Each context adapts this interface
 * to its specific player backend.
 */

/**
 * Minimal playback controls that all player types must support.
 */
export interface PlaybackControls {
  pause: () => void;
  play: () => void;
  /** Seek to an absolute time in seconds. */
  seek?: (time: number) => void;
}

/**
 * Extended playback controls for players that support rate changes
 * and fullscreen.
 */
export interface ExtendedPlaybackControls extends PlaybackControls {
  /** Enter fullscreen playback mode (video-specific). */
  ensureFullscreen?: () => void;
  /** Set playback rate (1.0 = normal). */
  setRate?: (rate: number) => void;
}
