/**
 * VideoPlayer module - contains hooks and utilities for the video player component.
 */

// Utility functions and types
export {
  type CueVisibility,
  type SubtitleTrack,
  DEFAULT_PLAYBACK_RATE,
  EMPTY_VTT_DATA_URL,
  SUMMARY_MARQUEE_GAP,
  SUMMARY_MARQUEE_SPEED,
  decodeDataUrl,
  filterCueTextByVisibility,
  injectVttCueStyle,
  isAssSubtitleTrack,
  isNativeWebkitFullscreen,
  isSafariBrowser,
  isVttSubtitleTrack,
  resolveSubtitleFormat,
  sanitiseOpacity,
  sanitiseOpacityPercent,
  sanitiseRate,
  selectAssSubtitleTrack,
  selectPrimarySubtitleTrack,
} from './utils';

// Subtitle processing hook
export {
  type SubtitleProcessorState,
  type UseSubtitleProcessorOptions,
  useCueVisibilityFilter,
  useSubtitleProcessor,
} from './useSubtitleProcessor';

// Fullscreen management hook
export {
  type UseVideoFullscreenOptions,
  type VideoFullscreenState,
  useVideoFullscreen,
} from './useVideoFullscreen';

// Playback controls hook
export {
  type PlaybackClock,
  type PlaybackControls,
  type UseVideoPlaybackOptions,
  type VideoPlaybackState,
  createPlaybackControls,
  useVideoPlayback,
} from './useVideoPlayback';

// Scrubbing gestures hook
export {
  type UseVideoScrubbingOptions,
  type VideoScrubbingHandlers,
  useVideoScrubbing,
} from './useVideoScrubbing';
