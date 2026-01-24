export const REEL_SCALE_STORAGE_KEY = 'player.sentenceImageReelScale';
export const REEL_SCALE_DEFAULT = 1;
export const REEL_SCALE_STEP = 0.1;
export const REEL_SCALE_MIN = 0.7;
export const REEL_SCALE_MAX = 1.6;

export const REEL_WINDOW_SIZE = 7;
export const REEL_PREFETCH_BUFFER = 2;
export const REEL_EAGER_PRELOAD_BUFFER = 2;

export const clampReelScale = (value: number) =>
  Math.min(REEL_SCALE_MAX, Math.max(REEL_SCALE_MIN, value));
