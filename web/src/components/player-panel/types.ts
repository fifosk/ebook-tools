export type PlaybackControls = {
  pause: () => void;
  play: () => void;
  seek?: (time: number) => void;
};
