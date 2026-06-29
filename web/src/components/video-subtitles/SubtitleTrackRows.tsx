import type { MutableRefObject } from 'react';
import type { AssSubtitleCue } from '../../lib/subtitles';
import type { SubtitleTokenSelection, TrackKind } from './subtitleTrackOverlayUtils';
import styles from './SubtitleTrackOverlay.module.css';

type SubtitleTrackRowsProps = {
  visibleTracks: TrackKind[];
  tracks: AssSubtitleCue['tracks'];
  isPlaying: boolean;
  selection: SubtitleTokenSelection | null;
  shadowTarget: SubtitleTokenSelection | null;
  trackRefs: MutableRefObject<Record<TrackKind, HTMLDivElement | null>>;
  onTokenClick: (track: TrackKind, index: number, element: HTMLElement) => void;
};

function tokenClassName({
  trackKey,
  isPast,
  isCurrent,
  isSelected,
  isShadow,
}: {
  trackKey: TrackKind;
  isPast: boolean;
  isCurrent: boolean;
  isSelected: boolean;
  isShadow: boolean;
}): string {
  const classNames = [styles.token];
  if (trackKey === 'original') {
    classNames.push(styles.tokenOriginal);
  } else if (trackKey === 'translation') {
    classNames.push(styles.tokenTranslation);
  } else {
    classNames.push(styles.tokenTransliteration);
  }
  if (isPast) {
    classNames.push(styles.tokenPast);
  }
  if (isCurrent) {
    classNames.push(styles.tokenCurrent);
  }
  if (isSelected) {
    classNames.push(styles.tokenSelected);
  }
  if (isShadow) {
    classNames.push(styles.tokenShadow);
  }
  return classNames.join(' ');
}

export function SubtitleTrackRows({
  visibleTracks,
  tracks,
  isPlaying,
  selection,
  shadowTarget,
  trackRefs,
  onTokenClick,
}: SubtitleTrackRowsProps) {
  return (
    <>
      {visibleTracks.map((trackKey) => {
        const entry = tracks[trackKey];
        const tokens = entry?.tokens ?? [];
        if (tokens.length === 0) {
          return null;
        }
        const playbackIndex = isPlaying ? entry?.currentIndex ?? null : null;
        return (
          <div
            key={trackKey}
            ref={(node) => {
              trackRefs.current[trackKey] = node;
            }}
            className={styles.trackRow}
            data-track={trackKey}
          >
            {tokens.map((token, index) => {
              const isPast = isPlaying && playbackIndex !== null && index < playbackIndex;
              const isCurrent = isPlaying && playbackIndex !== null && index === playbackIndex;
              const isSelected =
                !isPlaying && selection?.track === trackKey && selection.index === index;
              const isShadow = shadowTarget?.track === trackKey && shadowTarget.index === index;
              return (
                <button
                  type="button"
                  key={`${trackKey}-${index}`}
                  className={tokenClassName({
                    trackKey,
                    isPast,
                    isCurrent,
                    isSelected,
                    isShadow,
                  })}
                  data-subtitle-token-index={index}
                  data-track={trackKey}
                  aria-current={isCurrent ? 'true' : undefined}
                  aria-pressed={isSelected ? true : undefined}
                  onClick={(event) => {
                    event.stopPropagation();
                    onTokenClick(trackKey, index, event.currentTarget);
                  }}
                >
                  {token}
                </button>
              );
            })}
          </div>
        );
      })}
    </>
  );
}
