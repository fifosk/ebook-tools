import { useId, type ChangeEvent, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import {
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
  FontScaleProps,
  SentenceJumpProps,
  SubtitleBackgroundProps,
  SubtitleScaleProps,
  TranslationSpeedProps,
} from './types';

interface StackedAdvancedControlsProps
  extends TranslationSpeedProps,
    SubtitleScaleProps,
    SubtitleBackgroundProps,
    SentenceJumpProps,
    FontScaleProps {
  showAdvancedControls: boolean;
  controlsLayout: 'stacked' | 'compact';
}

export function StackedAdvancedControls({
  showAdvancedControls,
  controlsLayout,
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
}: StackedAdvancedControlsProps) {
  const sliderId = useId();
  const subtitleSliderId = useId();
  const subtitleBackgroundSliderId = useId();
  const fontScaleSliderId = useId();
  const myLinguistFontScaleSliderId = useId();
  const jumpInputFallbackId = useId();
  const jumpInputId = sentenceJumpInputId ?? jumpInputFallbackId;
  const jumpRangeId = `${jumpInputId}-range`;
  const jumpErrorId = `${jumpInputId}-error`;

  if (!showAdvancedControls || controlsLayout === 'compact') {
    return null;
  }

  const describedBy =
    sentenceJumpError && showSentenceJump
      ? jumpErrorId
      : showSentenceJump && sentenceJumpMin !== null && sentenceJumpMax !== null
        ? jumpRangeId
        : undefined;

  const formattedSpeed = formatTranslationSpeedLabel(translationSpeed);
  const formattedFontScale = `${Math.round(Math.min(Math.max(fontScalePercent, fontScaleMin), fontScaleMax))}%`;
  const formattedMyLinguistFontScale = `${Math.round(Math.min(Math.max(myLinguistFontScalePercent, myLinguistFontScaleMin), myLinguistFontScaleMax))}%`;
  const formattedSubtitleBackgroundOpacity = `${Math.round(Math.min(Math.max(subtitleBackgroundOpacityPercent, subtitleBackgroundOpacityMin), subtitleBackgroundOpacityMax))}%`;

  const handleSpeedChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (Number.isFinite(raw)) {
      onTranslationSpeedChange(raw as TranslationSpeed);
    }
  };

  const handleFontScaleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (Number.isFinite(raw)) {
      onFontScaleChange?.(raw);
    }
  };

  const handleMyLinguistFontScaleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (Number.isFinite(raw)) {
      onMyLinguistFontScaleChange?.(raw);
    }
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

  return (
    <>
      {showTranslationSpeed ? (
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
              title="Translation speed"
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

      {showSubtitleScale ? (
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
              title="Subtitle size"
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

      {showSubtitleBackgroundOpacity ? (
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
              title="Subtitle background opacity"
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

      {showSentenceJump ? (
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
                Range {sentenceJumpMin}&ndash;{sentenceJumpMax}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      {showFontScale ? (
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

      {showMyLinguistFontScale ? (
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
    </>
  );
}
