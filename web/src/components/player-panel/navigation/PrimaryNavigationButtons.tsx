import type { PrimaryButtonsProps, AudioTogglesProps, CueLayerTogglesProps } from './types';

interface PrimaryNavigationButtonsProps
  extends PrimaryButtonsProps,
    AudioTogglesProps,
    CueLayerTogglesProps {}

/**
 * Primary navigation buttons for playback control.
 * Includes first/prev/play/next/last, audio toggles, and cue layer toggles.
 */
export function PrimaryNavigationButtons({
  onNavigate,
  onToggleFullscreen,
  onTogglePlayback,
  disableFirst,
  disablePrevious,
  disableNext,
  disableLast,
  disablePlayback,
  disableFullscreen,
  isFullscreen,
  isPlaying,
  fullscreenLabel,
  fullscreenTestId,
  showOriginalAudioToggle = false,
  onToggleOriginalAudio,
  originalAudioEnabled = false,
  disableOriginalAudioToggle = false,
  showTranslationAudioToggle = false,
  onToggleTranslationAudio,
  translationAudioEnabled = false,
  disableTranslationAudioToggle = false,
  showSubtitleToggle = false,
  onToggleSubtitles,
  subtitlesEnabled = true,
  disableSubtitleToggle = false,
  showReadingBedToggle = false,
  readingBedEnabled = false,
  disableReadingBedToggle = false,
  onToggleReadingBed,
  showCueLayerToggles = false,
  cueVisibility,
  onToggleCueLayer,
  disableCueLayerToggles = false,
}: PrimaryNavigationButtonsProps) {
  const playbackLabel = isPlaying ? 'Pause playback' : 'Play playback';
  const playbackIcon = isPlaying ? '⏸' : '▶';

  const originalToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--audio',
    originalAudioEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off',
  ].join(' ');

  const originalToggleTitle = disableOriginalAudioToggle
    ? 'Original audio will appear after interactive assets regenerate'
    : 'Toggle Original Audio';

  const translationToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--audio',
    translationAudioEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off',
  ].join(' ');

  const translationToggleTitle = disableTranslationAudioToggle
    ? 'Translation audio will appear after interactive assets regenerate'
    : 'Toggle Translation Audio';

  const subtitleToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--audio',
    subtitlesEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off',
  ].join(' ');

  const subtitleToggleTitle = disableSubtitleToggle
    ? 'Subtitles will appear after media finalizes'
    : 'Toggle Subtitles';

  const readingBedToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--audio',
    readingBedEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off',
  ].join(' ');

  const readingBedToggleTitle = disableReadingBedToggle
    ? 'Reading music is not available'
    : 'Toggle Reading Music';

  const fullscreenButtonClassName = ['player-panel__nav-button'];
  if (isFullscreen) {
    fullscreenButtonClassName.push('player-panel__nav-button--fullscreen-active');
  }
  const fullscreenIcon = isFullscreen ? '🗗' : '⛶';

  const resolvedCueVisibility = cueVisibility ?? {
    original: true,
    transliteration: true,
    translation: true,
  };

  const handleToggleCueLayer = (key: 'original' | 'transliteration' | 'translation') => {
    onToggleCueLayer?.(key);
  };

  return (
    <>
      <button
        type="button"
        className="player-panel__nav-button"
        onClick={() => onNavigate('first')}
        disabled={disableFirst}
        aria-label="Go to first item"
        title="Go to first item"
      >
        <span aria-hidden="true">⏮</span>
      </button>
      <button
        type="button"
        className="player-panel__nav-button"
        onClick={() => onNavigate('previous')}
        disabled={disablePrevious}
        aria-label="Go to previous item"
        title="Go to previous item"
      >
        <span aria-hidden="true">⏪</span>
      </button>
      <button
        type="button"
        className="player-panel__nav-button"
        onClick={onTogglePlayback}
        disabled={disablePlayback}
        aria-label={playbackLabel}
        aria-pressed={isPlaying ? 'true' : 'false'}
        title={playbackLabel}
      >
        <span aria-hidden="true">{playbackIcon}</span>
      </button>
      <button
        type="button"
        className="player-panel__nav-button"
        onClick={() => onNavigate('next')}
        disabled={disableNext}
        aria-label="Go to next item"
        title="Go to next item"
      >
        <span aria-hidden="true">⏩</span>
      </button>
      <button
        type="button"
        className="player-panel__nav-button"
        onClick={() => onNavigate('last')}
        disabled={disableLast}
        aria-label="Go to last item"
        title="Go to last item"
      >
        <span aria-hidden="true">⏭</span>
      </button>

      {showOriginalAudioToggle ? (
        <button
          type="button"
          className={originalToggleClassName}
          onClick={onToggleOriginalAudio}
          disabled={disableOriginalAudioToggle}
          aria-label="Toggle Original Audio"
          aria-pressed={originalAudioEnabled}
          title={originalToggleTitle}
        >
          <span aria-hidden="true" className="player-panel__nav-button-icon">
            {originalAudioEnabled ? '🎧' : '🔇'}
          </span>
          <span aria-hidden="true" className="player-panel__nav-button-text">
            Orig
          </span>
        </button>
      ) : null}

      {showTranslationAudioToggle ? (
        <button
          type="button"
          className={translationToggleClassName}
          onClick={onToggleTranslationAudio}
          disabled={disableTranslationAudioToggle}
          aria-label="Toggle Translation Audio"
          aria-pressed={translationAudioEnabled}
          title={translationToggleTitle}
        >
          <span aria-hidden="true" className="player-panel__nav-button-icon">
            {translationAudioEnabled ? '🔊' : '🔈'}
          </span>
          <span aria-hidden="true" className="player-panel__nav-button-text">
            Trans
          </span>
        </button>
      ) : null}

      {showSubtitleToggle ? (
        <button
          type="button"
          className={subtitleToggleClassName}
          onClick={onToggleSubtitles}
          disabled={disableSubtitleToggle}
          aria-label="Toggle Subtitles"
          aria-pressed={subtitlesEnabled}
          title={subtitleToggleTitle}
        >
          <span aria-hidden="true" className="player-panel__nav-button-icon">
            {subtitlesEnabled ? '💬' : '🚫'}
          </span>
          <span aria-hidden="true" className="player-panel__nav-button-text">
            Subs
          </span>
        </button>
      ) : null}

      {showReadingBedToggle ? (
        <button
          type="button"
          className={readingBedToggleClassName}
          onClick={onToggleReadingBed}
          disabled={disableReadingBedToggle}
          aria-label="Toggle reading music"
          aria-pressed={readingBedEnabled}
          title={readingBedToggleTitle}
        >
          <span aria-hidden="true" className="player-panel__nav-button-icon">
            {readingBedEnabled ? '🎶' : '♪'}
          </span>
          <span aria-hidden="true" className="player-panel__nav-button-text">
            Music
          </span>
        </button>
      ) : null}

      {showCueLayerToggles ? (
        <div
          className="player-panel__subtitle-flags player-panel__subtitle-flags--controls"
          role="group"
          aria-label="Subtitle layers"
        >
          {[
            { key: 'original' as const, label: 'Orig', title: 'Original subtitles' },
            { key: 'transliteration' as const, label: 'Translit', title: 'Transliteration subtitles' },
            { key: 'translation' as const, label: 'Trans', title: 'Translation subtitles' },
          ].map((entry) => (
            <button
              key={entry.key}
              type="button"
              className="player-panel__subtitle-flag player-panel__subtitle-flag--compact"
              aria-pressed={resolvedCueVisibility[entry.key]}
              aria-label={`Toggle ${entry.title}`}
              title={`Toggle ${entry.title}`}
              onClick={() => handleToggleCueLayer(entry.key)}
              disabled={disableCueLayerToggles || disableSubtitleToggle}
            >
              {entry.label}
            </button>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        className={fullscreenButtonClassName.join(' ')}
        onClick={onToggleFullscreen}
        disabled={disableFullscreen}
        aria-pressed={isFullscreen}
        aria-label={fullscreenLabel}
        data-testid={fullscreenTestId}
        title={fullscreenLabel}
      >
        <span aria-hidden="true">{fullscreenIcon}</span>
      </button>
    </>
  );
}

export default PrimaryNavigationButtons;
