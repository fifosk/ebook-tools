import { useId, useRef } from 'react';
import type { ChangeEvent, KeyboardEvent as ReactKeyboardEvent } from 'react';
import type { InteractiveTextTheme } from '../../types/interactiveTextTheme';
import {
  DEFAULT_INTERACTIVE_TEXT_BG_OPACITY_PERCENT,
  DEFAULT_INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_PERCENT,
  DEFAULT_READING_BED_VOLUME_PERCENT,
  FONT_SCALE_MAX,
  FONT_SCALE_MIN,
  FONT_SCALE_STEP,
  formatTranslationSpeedLabel,
  MY_LINGUIST_FONT_SCALE_MAX,
  MY_LINGUIST_FONT_SCALE_MIN,
  MY_LINGUIST_FONT_SCALE_STEP,
  type NavigationIntent,
  type TranslationSpeed,
} from './constants';
import {
  DEFAULT_INTERACTIVE_TEXT_THEME,
  normalizeHexColor,
} from '../../types/interactiveTextTheme';

export interface NavigationControlsProps {
  context: 'panel' | 'fullscreen';
  onNavigate: (intent: NavigationIntent) => void;
  onToggleFullscreen: () => void;
  onTogglePlayback: () => void;
  controlsLayout?: 'stacked' | 'compact';
  disableFirst: boolean;
  disablePrevious: boolean;
  disableNext: boolean;
  disableLast: boolean;
  disablePlayback: boolean;
  disableFullscreen: boolean;
  isFullscreen: boolean;
  isPlaying: boolean;
  fullscreenLabel: string;
  showOriginalAudioToggle?: boolean;
  onToggleOriginalAudio?: () => void;
  originalAudioEnabled?: boolean;
  disableOriginalAudioToggle?: boolean;
  showSubtitleToggle?: boolean;
  onToggleSubtitles?: () => void;
  subtitlesEnabled?: boolean;
  disableSubtitleToggle?: boolean;
  showCueLayerToggles?: boolean;
  cueVisibility?: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
  onToggleCueLayer?: (key: 'original' | 'transliteration' | 'translation') => void;
  disableCueLayerToggles?: boolean;
  showTranslationSpeed: boolean;
  translationSpeed: TranslationSpeed;
  translationSpeedMin: number;
  translationSpeedMax: number;
  translationSpeedStep: number;
  onTranslationSpeedChange: (value: TranslationSpeed) => void;
  showSubtitleScale?: boolean;
  subtitleScale?: number;
  subtitleScaleMin?: number;
  subtitleScaleMax?: number;
  subtitleScaleStep?: number;
  onSubtitleScaleChange?: (value: number) => void;
  showSubtitleBackgroundOpacity?: boolean;
  subtitleBackgroundOpacityPercent?: number;
  subtitleBackgroundOpacityMin?: number;
  subtitleBackgroundOpacityMax?: number;
  subtitleBackgroundOpacityStep?: number;
  onSubtitleBackgroundOpacityChange?: (value: number) => void;
  showSentenceJump?: boolean;
  sentenceJumpValue?: string;
  sentenceJumpMin?: number | null;
  sentenceJumpMax?: number | null;
  sentenceJumpError?: string | null;
  sentenceJumpDisabled?: boolean;
  sentenceJumpInputId?: string;
  sentenceJumpListId?: string;
  sentenceJumpPlaceholder?: string;
  onSentenceJumpChange?: (value: string) => void;
  onSentenceJumpSubmit?: () => void;
  showFontScale?: boolean;
  fontScalePercent?: number;
  fontScaleMin?: number;
  fontScaleMax?: number;
  fontScaleStep?: number;
  onFontScaleChange?: (value: number) => void;
  showMyLinguistFontScale?: boolean;
  myLinguistFontScalePercent?: number;
  myLinguistFontScaleMin?: number;
  myLinguistFontScaleMax?: number;
  myLinguistFontScaleStep?: number;
  onMyLinguistFontScaleChange?: (value: number) => void;
  nowPlayingText?: string | null;
  nowPlayingTitle?: string | null;
  activeSentenceNumber?: number | null;
  totalSentencesInBook?: number | null;
  jobStartSentence?: number | null;
  bookTotalSentences?: number | null;

  showInteractiveThemeControls?: boolean;
  interactiveTheme?: InteractiveTextTheme | null;
  onInteractiveThemeChange?: (next: InteractiveTextTheme) => void;
  showInteractiveBackgroundOpacity?: boolean;
  interactiveBackgroundOpacityPercent?: number;
  interactiveBackgroundOpacityMin?: number;
  interactiveBackgroundOpacityMax?: number;
  interactiveBackgroundOpacityStep?: number;
  onInteractiveBackgroundOpacityChange?: (value: number) => void;
  showInteractiveSentenceCardOpacity?: boolean;
  interactiveSentenceCardOpacityPercent?: number;
  interactiveSentenceCardOpacityMin?: number;
  interactiveSentenceCardOpacityMax?: number;
  interactiveSentenceCardOpacityStep?: number;
  onInteractiveSentenceCardOpacityChange?: (value: number) => void;
  onResetLayout?: () => void;

  showReadingBedToggle?: boolean;
  readingBedEnabled?: boolean;
  disableReadingBedToggle?: boolean;
  onToggleReadingBed?: () => void;
  showReadingBedVolume?: boolean;
  readingBedVolumePercent?: number;
  readingBedVolumeMin?: number;
  readingBedVolumeMax?: number;
  readingBedVolumeStep?: number;
  onReadingBedVolumeChange?: (value: number) => void;
  showReadingBedTrack?: boolean;
  readingBedTrack?: string;
  readingBedTrackOptions?: { value: string; label: string }[];
  onReadingBedTrackChange?: (value: string) => void;

  showBackToLibrary?: boolean;
  onBackToLibrary?: () => void;
}

export function NavigationControls({
  context,
  onNavigate,
  onToggleFullscreen,
  onTogglePlayback,
  controlsLayout = 'stacked',
  disableFirst,
  disablePrevious,
  disableNext,
  disableLast,
  disablePlayback,
  disableFullscreen,
  isFullscreen,
  isPlaying,
  fullscreenLabel,
  showOriginalAudioToggle = false,
  onToggleOriginalAudio,
  originalAudioEnabled = false,
  disableOriginalAudioToggle = false,
  showSubtitleToggle = false,
  onToggleSubtitles,
  subtitlesEnabled = true,
  disableSubtitleToggle = false,
  showCueLayerToggles = false,
  cueVisibility,
  onToggleCueLayer,
  disableCueLayerToggles = false,
  showTranslationSpeed,
  translationSpeed,
  translationSpeedMin,
  translationSpeedMax,
  translationSpeedStep,
  onTranslationSpeedChange,
  showSubtitleScale = false,
  subtitleScale = 1,
  subtitleScaleMin = 0.5,
  subtitleScaleMax = 2,
  subtitleScaleStep = 0.25,
  onSubtitleScaleChange,
  showSubtitleBackgroundOpacity = false,
  subtitleBackgroundOpacityPercent = 70,
  subtitleBackgroundOpacityMin = 0,
  subtitleBackgroundOpacityMax = 100,
  subtitleBackgroundOpacityStep = 10,
  onSubtitleBackgroundOpacityChange,
  showSentenceJump = false,
  sentenceJumpValue = '',
  sentenceJumpMin = null,
  sentenceJumpMax = null,
  sentenceJumpError = null,
  sentenceJumpDisabled = false,
  sentenceJumpInputId,
  sentenceJumpListId,
  sentenceJumpPlaceholder,
  onSentenceJumpChange,
  onSentenceJumpSubmit,
  showFontScale = false,
  fontScalePercent = 100,
  fontScaleMin = FONT_SCALE_MIN,
  fontScaleMax = FONT_SCALE_MAX,
  fontScaleStep = FONT_SCALE_STEP,
  onFontScaleChange,
  showMyLinguistFontScale = false,
  myLinguistFontScalePercent = 100,
  myLinguistFontScaleMin = MY_LINGUIST_FONT_SCALE_MIN,
  myLinguistFontScaleMax = MY_LINGUIST_FONT_SCALE_MAX,
  myLinguistFontScaleStep = MY_LINGUIST_FONT_SCALE_STEP,
  onMyLinguistFontScaleChange,
  nowPlayingText = null,
  nowPlayingTitle = null,
  activeSentenceNumber = null,
  totalSentencesInBook = null,
  jobStartSentence = null,
  bookTotalSentences = null,
  showInteractiveThemeControls = false,
  interactiveTheme = null,
  onInteractiveThemeChange,
  showInteractiveBackgroundOpacity = false,
  interactiveBackgroundOpacityPercent = DEFAULT_INTERACTIVE_TEXT_BG_OPACITY_PERCENT,
  interactiveBackgroundOpacityMin = 0,
  interactiveBackgroundOpacityMax = 100,
  interactiveBackgroundOpacityStep = 5,
  onInteractiveBackgroundOpacityChange,
  showInteractiveSentenceCardOpacity = false,
  interactiveSentenceCardOpacityPercent = DEFAULT_INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_PERCENT,
  interactiveSentenceCardOpacityMin = 0,
  interactiveSentenceCardOpacityMax = 100,
  interactiveSentenceCardOpacityStep = 5,
  onInteractiveSentenceCardOpacityChange,
  onResetLayout,
  showReadingBedToggle = false,
  readingBedEnabled = false,
  disableReadingBedToggle = false,
  onToggleReadingBed,
  showReadingBedVolume = false,
  readingBedVolumePercent = DEFAULT_READING_BED_VOLUME_PERCENT,
  readingBedVolumeMin = 0,
  readingBedVolumeMax = 100,
  readingBedVolumeStep = 5,
  onReadingBedVolumeChange,
  showReadingBedTrack = false,
  readingBedTrack = '',
  readingBedTrackOptions = [],
  onReadingBedTrackChange,
  showBackToLibrary = false,
  onBackToLibrary,
}: NavigationControlsProps) {
  const groupClassName = [
    context === 'fullscreen'
      ? 'player-panel__navigation-group player-panel__navigation-group--fullscreen'
      : 'player-panel__navigation-group',
    controlsLayout === 'compact' ? 'player-panel__navigation-group--compact-controls' : null,
  ]
    .filter(Boolean)
    .join(' ');
  const navigationClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation player-panel__navigation--fullscreen'
      : 'player-panel__navigation';
  const fullscreenTestId = context === 'panel' ? 'player-panel-interactive-fullscreen' : undefined;
  const playbackLabel = isPlaying ? 'Pause playback' : 'Play playback';
  const playbackIcon = isPlaying ? '⏸' : '▶';
  const auxiliaryToggleVariant = showSubtitleToggle ? 'subtitles' : showOriginalAudioToggle ? 'original' : null;
  const originalToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--audio',
    originalAudioEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off',
  ].join(' ');
  const originalToggleTitle = disableOriginalAudioToggle
    ? 'Original audio will appear after interactive assets regenerate'
    : 'Toggle Original Audio';
  const subtitleToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--audio',
    subtitlesEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off',
  ].join(' ');
  const subtitleToggleTitle = disableSubtitleToggle ? 'Subtitles will appear after media finalizes' : 'Toggle Subtitles';
  const readingBedToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--audio',
    readingBedEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off',
  ].join(' ');
  const readingBedToggleTitle = disableReadingBedToggle ? 'Reading music is not available' : 'Toggle Reading Music';
  const sliderId = useId();
  const subtitleSliderId = useId();
  const subtitleBackgroundSliderId = useId();
  const interactiveBackgroundSliderId = useId();
  const interactiveSentenceCardSliderId = useId();
  const readingBedSliderId = useId();
  const jumpInputFallbackId = useId();
  const jumpInputId = sentenceJumpInputId ?? jumpInputFallbackId;
  const fontScaleSliderId = useId();
  const myLinguistFontScaleSliderId = useId();
  const jumpRangeId = `${jumpInputId}-range`;
  const jumpErrorId = `${jumpInputId}-error`;
  const describedBy =
    sentenceJumpError && showSentenceJump
      ? jumpErrorId
      : showSentenceJump && sentenceJumpMin !== null && sentenceJumpMax !== null
        ? jumpRangeId
        : undefined;
  const fullscreenButtonClassName = ['player-panel__nav-button'];
  if (isFullscreen) {
    fullscreenButtonClassName.push('player-panel__nav-button--fullscreen-active');
  }
  const fullscreenIcon = isFullscreen ? '🗗' : '⛶';
  const formattedSpeed = formatTranslationSpeedLabel(translationSpeed);
  const formattedSubtitleBackgroundOpacity = `${Math.round(
    Math.min(Math.max(subtitleBackgroundOpacityPercent, subtitleBackgroundOpacityMin), subtitleBackgroundOpacityMax),
  )}%`;
  const formattedInteractiveBackgroundOpacity = `${Math.round(
    Math.min(Math.max(interactiveBackgroundOpacityPercent, interactiveBackgroundOpacityMin), interactiveBackgroundOpacityMax),
  )}%`;
  const formattedInteractiveSentenceCardOpacity = `${Math.round(
    Math.min(
      Math.max(interactiveSentenceCardOpacityPercent, interactiveSentenceCardOpacityMin),
      interactiveSentenceCardOpacityMax,
    ),
  )}%`;
  const formattedReadingBedVolume = `${Math.round(
    Math.min(Math.max(readingBedVolumePercent, readingBedVolumeMin), readingBedVolumeMax),
  )}%`;
  const shouldShowCompactControls =
    controlsLayout === 'compact' &&
    (showTranslationSpeed ||
      showSubtitleScale ||
      showSubtitleBackgroundOpacity ||
      showFontScale ||
      showMyLinguistFontScale ||
      showInteractiveBackgroundOpacity ||
      showInteractiveSentenceCardOpacity ||
      showInteractiveThemeControls ||
      showReadingBedVolume ||
      showReadingBedTrack);
  const resolvedCueVisibility =
    cueVisibility ??
    ({
      original: true,
      transliteration: true,
      translation: true,
    } as const);
  const handleToggleCueLayer = (key: 'original' | 'transliteration' | 'translation') => {
    onToggleCueLayer?.(key);
  };
  const handleSpeedChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (!Number.isFinite(raw)) {
      return;
    }
    onTranslationSpeedChange(raw);
  };
  const handleSentenceInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    onSentenceJumpChange?.(event.target.value);
  };
  const handleSentenceInputKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      onSentenceJumpSubmit?.();
    }
  };
  const handleFontScaleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (!Number.isFinite(raw)) {
      return;
    }
    onFontScaleChange?.(raw);
  };
  const handleMyLinguistFontScaleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (!Number.isFinite(raw)) {
      return;
    }
    onMyLinguistFontScaleChange?.(raw);
  };
  const handleReadingBedTrackChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onReadingBedTrackChange?.(event.target.value);
  };
  const formattedFontScale = `${Math.round(
    Math.min(Math.max(fontScalePercent, fontScaleMin), fontScaleMax),
  )}%`;
  const formattedMyLinguistFontScale = `${Math.round(
    Math.min(Math.max(myLinguistFontScalePercent, myLinguistFontScaleMin), myLinguistFontScaleMax),
  )}%`;

  const bgColorInputRef = useRef<HTMLInputElement | null>(null);
  const originalColorInputRef = useRef<HTMLInputElement | null>(null);
  const translationColorInputRef = useRef<HTMLInputElement | null>(null);
  const transliterationColorInputRef = useRef<HTMLInputElement | null>(null);
  const highlightColorInputRef = useRef<HTMLInputElement | null>(null);

  const openColorPicker = (ref: { current: HTMLInputElement | null }) => {
    ref.current?.click();
  };
  const sentenceNowPlaying = (() => {
    if (activeSentenceNumber === null) {
      return null;
    }
    const jobTotal = totalSentencesInBook;
    const title =
      jobTotal !== null
        ? `Playing sentence ${activeSentenceNumber} of ${jobTotal}`
        : `Playing sentence ${activeSentenceNumber}`;

    const jobPercent = (() => {
      if (jobStartSentence === null || jobTotal === null) {
        return null;
      }
      const span = Math.max(jobTotal - jobStartSentence, 0);
      const ratio = span > 0 ? (activeSentenceNumber - jobStartSentence) / span : 1;
      if (!Number.isFinite(ratio)) {
        return null;
      }
      return Math.min(Math.max(Math.round(ratio * 100), 0), 100);
    })();

    const bookPercent = (() => {
      if (bookTotalSentences === null) {
        return null;
      }
      const ratio = bookTotalSentences > 0 ? activeSentenceNumber / bookTotalSentences : null;
      if (ratio === null || !Number.isFinite(ratio)) {
        return null;
      }
      return Math.min(Math.max(Math.round(ratio * 100), 0), 100);
    })();

    const suffixParts: string[] = [];
    if (jobPercent !== null) {
      suffixParts.push(`Job ${jobPercent}%`);
    }
    if (bookPercent !== null) {
      suffixParts.push(`Book ${bookPercent}%`);
    }
    if (suffixParts.length === 0) {
      return {
        label: `S${activeSentenceNumber}`,
        title,
      };
    }
    const compactSuffix = suffixParts
      .map((entry) => entry.replace(/^Job\\s+/i, 'J').replace(/^Book\\s+/i, 'B'))
      .join(' · ');
    return {
      label: `S${activeSentenceNumber} · ${compactSuffix}`,
      title: `${title} · ${suffixParts.join(' · ')}`,
    };
  })();

  return (
    <div className={groupClassName}>
      <div className="player-panel__navigation-row">
        <div className={navigationClassName} role="group" aria-label="Navigate media items">
          <button
            type="button"
            className="player-panel__nav-button"
            onClick={() => onNavigate('first')}
            disabled={disableFirst}
            aria-label="Go to first item"
          >
            <span aria-hidden="true">⏮</span>
          </button>
          <button
            type="button"
            className="player-panel__nav-button"
            onClick={() => onNavigate('previous')}
            disabled={disablePrevious}
            aria-label="Go to previous item"
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
          >
            <span aria-hidden="true">{playbackIcon}</span>
          </button>
          <button
            type="button"
            className="player-panel__nav-button"
            onClick={() => onNavigate('next')}
            disabled={disableNext}
            aria-label="Go to next item"
          >
            <span aria-hidden="true">⏩</span>
          </button>
          <button
            type="button"
            className="player-panel__nav-button"
            onClick={() => onNavigate('last')}
            disabled={disableLast}
            aria-label="Go to last item"
          >
            <span aria-hidden="true">⏭</span>
          </button>
          {auxiliaryToggleVariant === 'original' ? (
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
                {originalAudioEnabled ? '🎧' : '🎵'}
              </span>
              <span aria-hidden="true" className="player-panel__nav-button-text">
                Orig
              </span>
            </button>
          ) : null}
          {auxiliaryToggleVariant === 'subtitles' ? (
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
                { key: 'original' as const, label: 'Orig' },
                { key: 'transliteration' as const, label: 'Translit' },
                { key: 'translation' as const, label: 'Trans' },
              ].map((entry) => (
                <button
                  key={entry.key}
                  type="button"
                  className="player-panel__subtitle-flag player-panel__subtitle-flag--compact"
                  aria-pressed={resolvedCueVisibility[entry.key]}
                  onClick={() => handleToggleCueLayer(entry.key)}
                  disabled={disableCueLayerToggles || disableSubtitleToggle}
                >
                  {entry.label}
                </button>
              ))}
            </div>
          ) : null}
          {sentenceNowPlaying ? (
            <span
              className="player-panel__now-playing player-panel__now-playing--sentence"
              title={sentenceNowPlaying.title}
            >
              {sentenceNowPlaying.label}
            </span>
          ) : null}
          {showBackToLibrary ? (
            <button
              type="button"
              className="player-panel__nav-button"
              onClick={onBackToLibrary}
              aria-label="Back to library"
              title="Back to Library"
              disabled={!onBackToLibrary}
            >
              <span aria-hidden="true">📚</span>
            </button>
          ) : null}
          <button
            type="button"
            className={fullscreenButtonClassName.join(' ')}
            onClick={onToggleFullscreen}
            disabled={disableFullscreen}
            aria-pressed={isFullscreen}
            aria-label={fullscreenLabel}
            data-testid={fullscreenTestId}
          >
            <span aria-hidden="true">{fullscreenIcon}</span>
          </button>
        </div>
        {nowPlayingText ? (
          <span className="player-panel__now-playing" title={nowPlayingTitle ?? nowPlayingText}>
            {nowPlayingText}
          </span>
        ) : null}
        {showSentenceJump ? (
          <div className="player-panel__sentence-jump" data-testid="player-panel-sentence-jump">
            {sentenceJumpError ? (
              <span id={jumpErrorId} className="visually-hidden">
                {sentenceJumpError}
              </span>
            ) : sentenceJumpMin !== null && sentenceJumpMax !== null ? (
              <span id={jumpRangeId} className="visually-hidden">
                Range {sentenceJumpMin}–{sentenceJumpMax}
              </span>
            ) : null}
            <span className="player-panel__sentence-jump-label" aria-hidden="true">
              Jump
            </span>
            <input
              id={jumpInputId}
              className="player-panel__sentence-jump-input"
              type="number"
              inputMode="numeric"
              min={sentenceJumpMin ?? undefined}
              max={sentenceJumpMax ?? undefined}
              step={1}
              list={sentenceJumpListId}
              value={sentenceJumpValue}
              onChange={handleSentenceInputChange}
              onKeyDown={handleSentenceInputKeyDown}
              placeholder="…"
              aria-label="Jump to sentence"
              aria-describedby={describedBy}
              aria-invalid={sentenceJumpError ? 'true' : undefined}
              disabled={sentenceJumpDisabled}
              title={
                sentenceJumpError ??
                (sentenceJumpPlaceholder ? `Jump (range ${sentenceJumpPlaceholder})` : 'Jump to sentence')
              }
            />
            <button
              type="button"
              className="player-panel__sentence-jump-button"
              onClick={onSentenceJumpSubmit}
              disabled={sentenceJumpDisabled || !onSentenceJumpSubmit}
            >
              Go
            </button>
          </div>
        ) : null}
      </div>
      {shouldShowCompactControls ? (
        <div className="player-panel__control-bar" role="group" aria-label="Playback tuning">
          {showTranslationSpeed ? (
            <div className="player-panel__control" data-testid="player-panel-speed">
              <label className="player-panel__control-label" htmlFor={sliderId}>
                Speed
              </label>
              <input
                id={sliderId}
                type="range"
                className="player-panel__control-slider"
                min={translationSpeedMin}
                max={translationSpeedMax}
                step={translationSpeedStep}
                value={translationSpeed}
                onChange={handleSpeedChange}
                aria-label="Speed"
                aria-valuetext={formattedSpeed}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {formattedSpeed}
              </span>
            </div>
          ) : null}
          {showFontScale ? (
            <div className="player-panel__control" data-testid="player-panel-font-scale">
              <label className="player-panel__control-label" htmlFor={fontScaleSliderId}>
                Font
              </label>
              <input
                id={fontScaleSliderId}
                type="range"
                className="player-panel__control-slider"
                min={fontScaleMin}
                max={fontScaleMax}
                step={fontScaleStep}
                value={Math.min(Math.max(fontScalePercent, fontScaleMin), fontScaleMax)}
                onChange={handleFontScaleInputChange}
                aria-label="Font size"
                aria-valuemin={fontScaleMin}
                aria-valuemax={fontScaleMax}
                aria-valuenow={Math.round(fontScalePercent)}
                aria-valuetext={formattedFontScale}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {formattedFontScale}
              </span>
            </div>
          ) : null}
          {showMyLinguistFontScale ? (
            <div className="player-panel__control" data-testid="player-panel-my-linguist-font-scale">
              <label className="player-panel__control-label" htmlFor={myLinguistFontScaleSliderId}>
                Linguist
              </label>
              <input
                id={myLinguistFontScaleSliderId}
                type="range"
                className="player-panel__control-slider"
                min={myLinguistFontScaleMin}
                max={myLinguistFontScaleMax}
                step={myLinguistFontScaleStep}
                value={Math.min(Math.max(myLinguistFontScalePercent, myLinguistFontScaleMin), myLinguistFontScaleMax)}
                onChange={handleMyLinguistFontScaleInputChange}
                aria-label="MyLinguist font size"
                aria-valuemin={myLinguistFontScaleMin}
                aria-valuemax={myLinguistFontScaleMax}
                aria-valuenow={Math.round(myLinguistFontScalePercent)}
                aria-valuetext={formattedMyLinguistFontScale}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {formattedMyLinguistFontScale}
              </span>
            </div>
          ) : null}
          {showSubtitleScale ? (
            <div className="player-panel__control" data-testid="player-panel-subtitle-scale">
              <label className="player-panel__control-label" htmlFor={subtitleSliderId}>
                Subs
              </label>
              <input
                id={subtitleSliderId}
                type="range"
                className="player-panel__control-slider"
                min={subtitleScaleMin}
                max={subtitleScaleMax}
                step={subtitleScaleStep}
                value={subtitleScale}
                onChange={(event) => onSubtitleScaleChange?.(Number(event.target.value))}
                aria-label="Subtitle size"
                aria-valuetext={`${Math.round(subtitleScale * 100)}%`}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {Math.round(subtitleScale * 100)}%
              </span>
            </div>
          ) : null}
          {showSubtitleBackgroundOpacity ? (
            <div className="player-panel__control" data-testid="player-panel-subtitle-background">
              <label className="player-panel__control-label" htmlFor={subtitleBackgroundSliderId}>
                Box
              </label>
              <input
                id={subtitleBackgroundSliderId}
                type="range"
                className="player-panel__control-slider"
                min={subtitleBackgroundOpacityMin}
                max={subtitleBackgroundOpacityMax}
                step={subtitleBackgroundOpacityStep}
                value={subtitleBackgroundOpacityPercent}
                onChange={(event) => onSubtitleBackgroundOpacityChange?.(Number(event.target.value))}
                aria-label="Subtitle background opacity"
                aria-valuetext={formattedSubtitleBackgroundOpacity}
                disabled={disableSubtitleToggle || !subtitlesEnabled}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {formattedSubtitleBackgroundOpacity}
              </span>
            </div>
          ) : null}
          {showInteractiveBackgroundOpacity ? (
            <div className="player-panel__control" data-testid="player-panel-interactive-background">
              <label className="player-panel__control-label" htmlFor={interactiveBackgroundSliderId}>
                BG
              </label>
              <input
                id={interactiveBackgroundSliderId}
                type="range"
                className="player-panel__control-slider"
                min={interactiveBackgroundOpacityMin}
                max={interactiveBackgroundOpacityMax}
                step={interactiveBackgroundOpacityStep}
                value={interactiveBackgroundOpacityPercent}
                onChange={(event) => onInteractiveBackgroundOpacityChange?.(Number(event.target.value))}
                aria-label="Interactive reader background opacity"
                aria-valuetext={formattedInteractiveBackgroundOpacity}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {formattedInteractiveBackgroundOpacity}
              </span>
            </div>
          ) : null}
          {showInteractiveSentenceCardOpacity ? (
            <div className="player-panel__control" data-testid="player-panel-interactive-cards">
              <label className="player-panel__control-label" htmlFor={interactiveSentenceCardSliderId}>
                Cards
              </label>
              <input
                id={interactiveSentenceCardSliderId}
                type="range"
                className="player-panel__control-slider"
                min={interactiveSentenceCardOpacityMin}
                max={interactiveSentenceCardOpacityMax}
                step={interactiveSentenceCardOpacityStep}
                value={interactiveSentenceCardOpacityPercent}
                onChange={(event) => onInteractiveSentenceCardOpacityChange?.(Number(event.target.value))}
                aria-label="Sentence card background opacity"
                aria-valuetext={formattedInteractiveSentenceCardOpacity}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {formattedInteractiveSentenceCardOpacity}
              </span>
            </div>
          ) : null}
          {showReadingBedVolume ? (
            <div className="player-panel__control" data-testid="player-panel-reading-music">
              <label className="player-panel__control-label" htmlFor={readingBedSliderId}>
                Music
              </label>
              <input
                id={readingBedSliderId}
                type="range"
                className="player-panel__control-slider"
                min={readingBedVolumeMin}
                max={readingBedVolumeMax}
                step={readingBedVolumeStep}
                value={Math.min(Math.max(readingBedVolumePercent, readingBedVolumeMin), readingBedVolumeMax)}
                onChange={(event) => onReadingBedVolumeChange?.(Number(event.target.value))}
                disabled={disableReadingBedToggle || !readingBedEnabled}
                aria-label="Reading music mix volume"
                aria-valuemin={readingBedVolumeMin}
                aria-valuemax={readingBedVolumeMax}
                aria-valuenow={Math.round(readingBedVolumePercent)}
                aria-valuetext={formattedReadingBedVolume}
              />
              <span className="player-panel__control-value" aria-live="polite">
                {formattedReadingBedVolume}
              </span>
            </div>
          ) : null}
          {showReadingBedTrack ? (
            <div
              className="player-panel__inline-audio"
              role="group"
              aria-label="Reading music track"
              data-testid="player-panel-reading-music-track"
            >
              <span className="player-panel__inline-audio-label">Bed</span>
              <select
                value={readingBedTrack}
                onChange={handleReadingBedTrackChange}
                disabled={disableReadingBedToggle || !readingBedEnabled}
                aria-label="Reading music track"
              >
                {readingBedTrackOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
          {showInteractiveThemeControls && interactiveTheme ? (
            <div className="player-panel__control-theme" role="group" aria-label="Interactive theme colors">
              <button
                type="button"
                className="player-panel__control-color-pill"
                onClick={() => openColorPicker(bgColorInputRef)}
                title="Background color"
                aria-label="Pick background color"
              >
                <span className="player-panel__control-color-pill-label">BG</span>
                <span
                  className="player-panel__control-color-pill-swatch"
                  style={{ backgroundColor: interactiveTheme.background }}
                  aria-hidden="true"
                />
              </button>
              <input
                ref={bgColorInputRef}
                className="player-panel__control-color-input"
                type="color"
                value={interactiveTheme.background}
                onChange={(event) =>
                  onInteractiveThemeChange?.({
                    ...interactiveTheme,
                    background: normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.background),
                  })
                }
                aria-label="Background color"
              />

              <button
                type="button"
                className="player-panel__control-color-pill"
                onClick={() => openColorPicker(originalColorInputRef)}
                title="Original text color"
                aria-label="Pick original text color"
              >
                <span className="player-panel__control-color-pill-label">OR</span>
                <span
                  className="player-panel__control-color-pill-swatch"
                  style={{ backgroundColor: interactiveTheme.original }}
                  aria-hidden="true"
                />
              </button>
              <input
                ref={originalColorInputRef}
                className="player-panel__control-color-input"
                type="color"
                value={interactiveTheme.original}
                onChange={(event) => {
                  const next = normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.original);
                  onInteractiveThemeChange?.({
                    ...interactiveTheme,
                    original: next,
                    originalActive: next,
                  });
                }}
                aria-label="Original text color"
              />

              <button
                type="button"
                className="player-panel__control-color-pill"
                onClick={() => openColorPicker(translationColorInputRef)}
                title="Translation text color"
                aria-label="Pick translation text color"
              >
                <span className="player-panel__control-color-pill-label">TR</span>
                <span
                  className="player-panel__control-color-pill-swatch"
                  style={{ backgroundColor: interactiveTheme.translation }}
                  aria-hidden="true"
                />
              </button>
              <input
                ref={translationColorInputRef}
                className="player-panel__control-color-input"
                type="color"
                value={interactiveTheme.translation}
                onChange={(event) => {
                  const next = normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.translation);
                  onInteractiveThemeChange?.({
                    ...interactiveTheme,
                    translation: next,
                  });
                }}
                aria-label="Translation text color"
              />

              <button
                type="button"
                className="player-panel__control-color-pill"
                onClick={() => openColorPicker(transliterationColorInputRef)}
                title="Transliteration text color"
                aria-label="Pick transliteration text color"
              >
                <span className="player-panel__control-color-pill-label">TL</span>
                <span
                  className="player-panel__control-color-pill-swatch"
                  style={{ backgroundColor: interactiveTheme.transliteration }}
                  aria-hidden="true"
                />
              </button>
              <input
                ref={transliterationColorInputRef}
                className="player-panel__control-color-input"
                type="color"
                value={interactiveTheme.transliteration}
                onChange={(event) => {
                  const next = normalizeHexColor(
                    event.target.value,
                    DEFAULT_INTERACTIVE_TEXT_THEME.transliteration,
                  );
                  onInteractiveThemeChange?.({
                    ...interactiveTheme,
                    transliteration: next,
                  });
                }}
                aria-label="Transliteration text color"
              />

              <button
                type="button"
                className="player-panel__control-color-pill"
                onClick={() => openColorPicker(highlightColorInputRef)}
                title="Highlight color"
                aria-label="Pick highlight color"
              >
                <span className="player-panel__control-color-pill-label">HL</span>
                <span
                  className="player-panel__control-color-pill-swatch"
                  style={{ backgroundColor: interactiveTheme.highlight }}
                  aria-hidden="true"
                />
              </button>
              <input
                ref={highlightColorInputRef}
                className="player-panel__control-color-input"
                type="color"
                value={interactiveTheme.highlight}
                onChange={(event) => {
                  const next = normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.highlight);
                  onInteractiveThemeChange?.({
                    ...interactiveTheme,
                    highlight: next,
                  });
                }}
                aria-label="Highlight color"
              />

              <button
                type="button"
                className="player-panel__control-reset-layout"
                onClick={() => onResetLayout?.()}
                title="Reset layout to defaults"
                aria-label="Reset layout to defaults"
              >
                ↺
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      {controlsLayout !== 'compact' && showTranslationSpeed ? (
        <div className="player-panel__nav-speed" data-testid="player-panel-speed">
          <label className="player-panel__nav-speed-label" htmlFor={sliderId}>
            Speed
          </label>
          <div className="player-panel__nav-speed-control">
            <input
              id={sliderId}
              type="range"
              className="player-panel__nav-speed-slider"
              min={translationSpeedMin}
              max={translationSpeedMax}
              step={translationSpeedStep}
              value={translationSpeed}
              onChange={handleSpeedChange}
              aria-label="Speed"
              aria-valuetext={formattedSpeed}
            />
            <span className="player-panel__nav-speed-value" aria-live="polite">
              {formattedSpeed}
            </span>
          </div>
          <div className="player-panel__nav-speed-scale" aria-hidden="true">
            <span>{formatTranslationSpeedLabel(translationSpeedMin)}</span>
            <span>{formatTranslationSpeedLabel(translationSpeedMax)}</span>
          </div>
        </div>
      ) : null}
      {controlsLayout !== 'compact' && showSubtitleScale ? (
        <div className="player-panel__nav-subtitles" data-testid="player-panel-subtitle-scale">
          <label className="player-panel__nav-subtitles-label" htmlFor={subtitleSliderId}>
            Subtitles
          </label>
          <div className="player-panel__nav-subtitles-control">
            <input
              id={subtitleSliderId}
              type="range"
              className="player-panel__nav-subtitles-slider"
              min={subtitleScaleMin}
              max={subtitleScaleMax}
              step={subtitleScaleStep}
              value={subtitleScale}
              onChange={(event) => onSubtitleScaleChange?.(Number(event.target.value))}
              aria-label="Subtitle size"
              aria-valuetext={`${Math.round(subtitleScale * 100)}%`}
            />
            <span className="player-panel__nav-subtitles-value" aria-live="polite">
              {Math.round(subtitleScale * 100)}%
            </span>
          </div>
          <div className="player-panel__nav-subtitles-scale" aria-hidden="true">
            <span>{Math.round(subtitleScaleMin * 100)}%</span>
            <span>{Math.round(subtitleScaleMax * 100)}%</span>
          </div>
        </div>
      ) : null}
      {controlsLayout !== 'compact' && showSubtitleBackgroundOpacity ? (
        <div className="player-panel__nav-subtitle-background" data-testid="player-panel-subtitle-background">
          <label className="player-panel__nav-subtitle-background-label" htmlFor={subtitleBackgroundSliderId}>
            Box
          </label>
          <div className="player-panel__nav-subtitle-background-control">
            <input
              id={subtitleBackgroundSliderId}
              type="range"
              className="player-panel__nav-subtitle-background-slider"
              min={subtitleBackgroundOpacityMin}
              max={subtitleBackgroundOpacityMax}
              step={subtitleBackgroundOpacityStep}
              value={subtitleBackgroundOpacityPercent}
              onChange={(event) => onSubtitleBackgroundOpacityChange?.(Number(event.target.value))}
              aria-label="Subtitle background opacity"
              aria-valuetext={formattedSubtitleBackgroundOpacity}
              disabled={disableSubtitleToggle || !subtitlesEnabled}
            />
            <span className="player-panel__nav-subtitle-background-value" aria-live="polite">
              {formattedSubtitleBackgroundOpacity}
            </span>
          </div>
          <div className="player-panel__nav-subtitle-background-scale" aria-hidden="true">
            <span>{Math.round(subtitleBackgroundOpacityMin)}%</span>
            <span>{Math.round(subtitleBackgroundOpacityMax)}%</span>
          </div>
        </div>
      ) : null}
      {showSentenceJump && controlsLayout !== 'compact' ? (
        <div className="player-panel__nav-jump">
          <label className="player-panel__nav-speed-label" htmlFor={jumpInputId}>
            Jump to sentence
          </label>
          <div className="player-panel__nav-jump-control">
            <input
              id={jumpInputId}
              className="player-panel__nav-jump-input"
              type="number"
              inputMode="numeric"
              min={sentenceJumpMin ?? undefined}
              max={sentenceJumpMax ?? undefined}
              step={1}
              list={sentenceJumpListId}
              value={sentenceJumpValue}
              onChange={handleSentenceInputChange}
              onKeyDown={handleSentenceInputKeyDown}
              placeholder={sentenceJumpPlaceholder}
              aria-describedby={describedBy}
              aria-invalid={sentenceJumpError ? 'true' : undefined}
            />
            <button
              type="button"
              className="player-panel__nav-jump-button"
              onClick={onSentenceJumpSubmit}
              disabled={sentenceJumpDisabled || !onSentenceJumpSubmit}
            >
              Go
            </button>
          </div>
          <div className="player-panel__nav-jump-meta" aria-live="polite">
            {sentenceJumpError ? (
              <span id={jumpErrorId} className="player-panel__nav-jump-error">
                {sentenceJumpError}
              </span>
            ) : sentenceJumpMin !== null && sentenceJumpMax !== null ? (
              <span id={jumpRangeId}>
                Range {sentenceJumpMin}–{sentenceJumpMax}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}
      {showFontScale && !shouldShowCompactControls ? (
        <div className="player-panel__nav-font">
          <label className="player-panel__nav-font-label" htmlFor={fontScaleSliderId}>
            Font size
          </label>
          <div className="player-panel__nav-font-control">
            <input
              id={fontScaleSliderId}
              className="player-panel__nav-font-input"
              type="range"
              min={fontScaleMin}
              max={fontScaleMax}
              step={fontScaleStep}
              value={Math.min(Math.max(fontScalePercent, fontScaleMin), fontScaleMax)}
              onChange={handleFontScaleInputChange}
              aria-valuemin={fontScaleMin}
              aria-valuemax={fontScaleMax}
              aria-valuenow={Math.round(fontScalePercent)}
              aria-valuetext={formattedFontScale}
              aria-label="Adjust font size"
            />
            <span className="player-panel__nav-font-value" aria-live="polite">
              {formattedFontScale}
            </span>
          </div>
        </div>
      ) : null}
      {showMyLinguistFontScale && !shouldShowCompactControls ? (
        <div className="player-panel__nav-font">
          <label className="player-panel__nav-font-label" htmlFor={myLinguistFontScaleSliderId}>
            MyLinguist font
          </label>
          <div className="player-panel__nav-font-control">
            <input
              id={myLinguistFontScaleSliderId}
              className="player-panel__nav-font-input"
              type="range"
              min={myLinguistFontScaleMin}
              max={myLinguistFontScaleMax}
              step={myLinguistFontScaleStep}
              value={Math.min(Math.max(myLinguistFontScalePercent, myLinguistFontScaleMin), myLinguistFontScaleMax)}
              onChange={handleMyLinguistFontScaleInputChange}
              aria-valuemin={myLinguistFontScaleMin}
              aria-valuemax={myLinguistFontScaleMax}
              aria-valuenow={Math.round(myLinguistFontScalePercent)}
              aria-valuetext={formattedMyLinguistFontScale}
              aria-label="Adjust MyLinguist font size"
            />
            <span className="player-panel__nav-font-value" aria-live="polite">
              {formattedMyLinguistFontScale}
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
