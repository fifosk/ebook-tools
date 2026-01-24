import { useId, type ChangeEvent } from 'react';
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
  type TranslationSpeed,
} from '../constants';
import type {
  TranslationSpeedProps,
  SubtitleScaleProps,
  SubtitleBackgroundProps,
  FontScaleProps,
  InteractiveThemeProps,
  ReadingBedProps,
} from './types';

interface ControlBarSlidersProps
  extends TranslationSpeedProps,
    SubtitleScaleProps,
    SubtitleBackgroundProps,
    FontScaleProps,
    Omit<InteractiveThemeProps, 'showInteractiveThemeControls' | 'interactiveTheme' | 'onInteractiveThemeChange' | 'onResetLayout'>,
    ReadingBedProps {}

/**
 * Compact control bar with sliders for speed, font scale, opacity, etc.
 */
export function ControlBarSliders({
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
  disableSubtitleToggle = false,
  subtitlesEnabled = true,
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
  disableReadingBedToggle = false,
  readingBedEnabled = false,
}: ControlBarSlidersProps) {
  const sliderId = useId();
  const subtitleSliderId = useId();
  const subtitleBackgroundSliderId = useId();
  const interactiveBackgroundSliderId = useId();
  const interactiveSentenceCardSliderId = useId();
  const readingBedSliderId = useId();
  const fontScaleSliderId = useId();
  const myLinguistFontScaleSliderId = useId();

  const handleSpeedChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (!Number.isFinite(raw)) {
      return;
    }
    onTranslationSpeedChange(raw as TranslationSpeed);
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
  const formattedFontScale = `${Math.round(
    Math.min(Math.max(fontScalePercent, fontScaleMin), fontScaleMax),
  )}%`;
  const formattedMyLinguistFontScale = `${Math.round(
    Math.min(Math.max(myLinguistFontScalePercent, myLinguistFontScaleMin), myLinguistFontScaleMax),
  )}%`;

  return (
    <>
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
            title="Translation speed"
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
            title="Font size"
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
            title="MyLinguist font size"
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
            title="Subtitle size"
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
            title="Subtitle background opacity"
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
            title="Interactive reader background opacity"
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
            title="Sentence card opacity"
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
            title="Reading music volume"
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
            title="Reading music track"
          >
            {readingBedTrackOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}
    </>
  );
}

export default ControlBarSliders;
