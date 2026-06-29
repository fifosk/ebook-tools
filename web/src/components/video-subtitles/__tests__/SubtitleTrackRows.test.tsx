import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { MutableRefObject } from 'react';
import type { AssSubtitleCue } from '../../../lib/subtitles';
import { SubtitleTrackRows } from '../SubtitleTrackRows';
import type { TrackKind } from '../subtitleTrackOverlayUtils';
import styles from '../SubtitleTrackOverlay.module.css';

function trackRefs() {
  return {
    current: {
      original: null,
      transliteration: null,
      translation: null,
    },
  } as MutableRefObject<Record<TrackKind, HTMLDivElement | null>>;
}

function tracks(): AssSubtitleCue['tracks'] {
  return {
    original: { tokens: ['Source'], currentIndex: null },
    transliteration: { tokens: ['goedemorgen', 'wereld'], currentIndex: 0 },
    translation: { tokens: ['good', 'morning', 'world'], currentIndex: 1 },
  };
}

describe('SubtitleTrackRows', () => {
  it('renders visible rows with playback current and past token state', () => {
    const onTokenClick = vi.fn();
    render(
      <SubtitleTrackRows
        visibleTracks={['translation', 'transliteration']}
        tracks={tracks()}
        isPlaying
        selection={null}
        shadowTarget={null}
        trackRefs={trackRefs()}
        onTokenClick={onTokenClick}
      />,
    );

    expect(screen.queryByRole('button', { name: 'Source' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'good' })).toHaveClass(styles.tokenPast);
    expect(screen.getByRole('button', { name: 'morning' })).toHaveClass(styles.tokenCurrent);
    expect(screen.getByRole('button', { name: 'morning' })).toHaveAttribute(
      'aria-current',
      'true',
    );
    expect(screen.getByRole('button', { name: 'goedemorgen' })).toHaveClass(
      styles.tokenCurrent,
    );
  });

  it('renders paused selection and shadow state, then forwards token activation', () => {
    const onTokenClick = vi.fn();
    const refs = trackRefs();
    render(
      <div onClick={() => onTokenClick('bubble' as TrackKind, -1, document.body)}>
        <SubtitleTrackRows
          visibleTracks={['translation', 'transliteration']}
          tracks={tracks()}
          isPlaying={false}
          selection={{ track: 'translation', index: 1 }}
          shadowTarget={{ track: 'transliteration', index: 1 }}
          trackRefs={refs}
          onTokenClick={onTokenClick}
        />
      </div>,
    );

    const selected = screen.getByRole('button', { name: 'morning' });
    const shadow = screen.getByRole('button', { name: 'wereld' });

    expect(selected).toHaveClass(styles.tokenSelected);
    expect(selected).toHaveAttribute('aria-pressed', 'true');
    expect(shadow).toHaveClass(styles.tokenShadow);

    fireEvent.click(selected);

    expect(onTokenClick).toHaveBeenCalledTimes(1);
    expect(onTokenClick).toHaveBeenCalledWith('translation', 1, selected);
    expect(refs.current.translation).toHaveAttribute('data-track', 'translation');
    expect(refs.current.transliteration).toHaveAttribute('data-track', 'transliteration');
  });
});
