import { useId, type ChangeEvent, type KeyboardEvent as ReactKeyboardEvent } from 'react';
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
} from './constants';
import {
  PrimaryNavigationButtons,
  BookmarkPanel,
  ControlBarSliders,
  ThemeColorPickers,
  SecondaryNavigation,
} from './navigation';
import type { NavigationControlsProps } from './navigation';

// Re-export types for backward compatibility
export type { ChapterNavigationEntry, NavigationControlsProps } from './navigation';

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
  showTranslationAudioToggle = false,
  onToggleTranslationAudio,
  translationAudioEnabled = false,
  disableTranslationAudioToggle = false,
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
  searchPanel,
  searchPlacement = 'secondary',
  showChapterJump = false,
  chapters = [],
  activeChapterId = null,
  onChapterJump,
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
  showPrimaryControls = true,
  showAdvancedControls = true,
  showAdvancedToggle = false,
  advancedControlsOpen = false,
  onToggleAdvancedControls,
  showExport = false,
  exportDisabled = false,
  exportBusy = false,
  exportLabel,
  exportTitle,
  exportError = null,
  onExport,
  showBookmarks = false,
  bookmarks = [],
  onAddBookmark,
  onJumpToBookmark,
  onRemoveBookmark,
  jobStartSentence = null,
  totalSentencesInBook = null,
}: NavigationControlsProps) {
  const shouldShowPrimaryControls = showPrimaryControls !== false;
  const shouldShowAdvancedControls = showAdvancedControls !== false;

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
  const searchInPrimary = Boolean(searchPanel) && searchPlacement === 'primary';
  const searchInSecondary = Boolean(searchPanel) && !searchInPrimary;
  const showPrimaryInfoRow = searchInPrimary;

  const advancedToggleClassName = [
    'player-panel__nav-button',
    'player-panel__nav-button--caret',
    advancedControlsOpen ? 'player-panel__nav-button--advanced-active' : null,
  ]
    .filter(Boolean)
    .join(' ');

  const advancedToggleLabel = advancedControlsOpen ? 'Hide advanced controls' : 'Show advanced controls';
  const resolvedExportLabel = exportLabel ?? (exportBusy ? 'Preparing export' : 'Export offline player');
  const resolvedExportTitle = exportTitle ?? resolvedExportLabel;

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

  // IDs for stacked layout sliders
  const sliderId = useId();
  const subtitleSliderId = useId();
  const subtitleBackgroundSliderId = useId();
  const fontScaleSliderId = useId();
  const myLinguistFontScaleSliderId = useId();
  const jumpInputFallbackId = useId();
  const jumpInputId = sentenceJumpInputId ?? jumpInputFallbackId;
  const jumpRangeId = `${jumpInputId}-range`;
  const jumpErrorId = `${jumpInputId}-error`;

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
      onTranslationSpeedChange(raw);
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
    <div className={groupClassName}>
      {shouldShowPrimaryControls ? (
        <div className="player-panel__navigation-row">
          <div className={navigationClassName} role="group" aria-label="Navigate media items">
            <PrimaryNavigationButtons
              onNavigate={onNavigate}
              onToggleFullscreen={onToggleFullscreen}
              onTogglePlayback={onTogglePlayback}
              disableFirst={disableFirst}
              disablePrevious={disablePrevious}
              disableNext={disableNext}
              disableLast={disableLast}
              disablePlayback={disablePlayback}
              disableFullscreen={disableFullscreen}
              isFullscreen={isFullscreen}
              isPlaying={isPlaying}
              fullscreenLabel={fullscreenLabel}
              fullscreenTestId={fullscreenTestId}
              showOriginalAudioToggle={showOriginalAudioToggle}
              onToggleOriginalAudio={onToggleOriginalAudio}
              originalAudioEnabled={originalAudioEnabled}
              disableOriginalAudioToggle={disableOriginalAudioToggle}
              showTranslationAudioToggle={showTranslationAudioToggle}
              onToggleTranslationAudio={onToggleTranslationAudio}
              translationAudioEnabled={translationAudioEnabled}
              disableTranslationAudioToggle={disableTranslationAudioToggle}
              showSubtitleToggle={showSubtitleToggle}
              onToggleSubtitles={onToggleSubtitles}
              subtitlesEnabled={subtitlesEnabled}
              disableSubtitleToggle={disableSubtitleToggle}
              showReadingBedToggle={showReadingBedToggle}
              readingBedEnabled={readingBedEnabled}
              disableReadingBedToggle={disableReadingBedToggle}
              onToggleReadingBed={onToggleReadingBed}
              showCueLayerToggles={showCueLayerToggles}
              cueVisibility={cueVisibility}
              onToggleCueLayer={onToggleCueLayer}
              disableCueLayerToggles={disableCueLayerToggles}
            />

            <BookmarkPanel
              showBookmarks={showBookmarks}
              bookmarks={bookmarks}
              onAddBookmark={onAddBookmark}
              onJumpToBookmark={onJumpToBookmark}
              onRemoveBookmark={onRemoveBookmark}
            />

            {showExport ? (
              <button
                type="button"
                className="player-panel__nav-button player-panel__nav-button--export"
                onClick={onExport}
                disabled={exportDisabled || !onExport}
                aria-label={resolvedExportLabel}
                title={resolvedExportTitle}
                aria-busy={exportBusy ? 'true' : undefined}
              >
                <span aria-hidden="true" className="player-panel__nav-button-icon">
                  {exportBusy ? '⏳' : '📦'}
                </span>
              </button>
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

            {showAdvancedToggle && onToggleAdvancedControls ? (
              <button
                type="button"
                className={advancedToggleClassName}
                onClick={onToggleAdvancedControls}
                aria-pressed={advancedControlsOpen}
                aria-label={advancedToggleLabel}
                title={advancedToggleLabel}
              >
                <span aria-hidden="true" className="player-panel__nav-button-caret" />
              </button>
            ) : null}
          </div>

          {showPrimaryInfoRow ? (
            <div className="player-panel__navigation-row-info">
              {nowPlayingText ? (
                <span className="player-panel__now-playing" title={nowPlayingTitle ?? nowPlayingText}>
                  {nowPlayingText}
                </span>
              ) : null}
              {searchInPrimary ? (
                <div className="player-panel__navigation-search player-panel__navigation-search--primary">
                  {searchPanel}
                </div>
              ) : null}
            </div>
          ) : nowPlayingText ? (
            <span className="player-panel__now-playing" title={nowPlayingTitle ?? nowPlayingText}>
              {nowPlayingText}
            </span>
          ) : null}

          <SecondaryNavigation
            searchPanel={searchPanel}
            searchInSecondary={searchInSecondary}
            showSentenceJump={showSentenceJump}
            sentenceJumpValue={sentenceJumpValue}
            sentenceJumpMin={sentenceJumpMin}
            sentenceJumpMax={sentenceJumpMax}
            sentenceJumpError={sentenceJumpError}
            sentenceJumpDisabled={sentenceJumpDisabled}
            sentenceJumpInputId={sentenceJumpInputId}
            sentenceJumpListId={sentenceJumpListId}
            sentenceJumpPlaceholder={sentenceJumpPlaceholder}
            onSentenceJumpChange={onSentenceJumpChange}
            onSentenceJumpSubmit={onSentenceJumpSubmit}
            showChapterJump={showChapterJump}
            chapters={chapters}
            activeChapterId={activeChapterId}
            onChapterJump={onChapterJump}
            jobStartSentence={jobStartSentence}
            totalSentencesInBook={totalSentencesInBook}
          />
        </div>
      ) : null}

      {shouldShowPrimaryControls && exportError ? (
        <span className="player-panel__export-error" role="alert">
          {exportError}
        </span>
      ) : null}

      {shouldShowAdvancedControls && shouldShowCompactControls ? (
        <div className="player-panel__control-bar" role="group" aria-label="Playback tuning">
          <ControlBarSliders
            showTranslationSpeed={showTranslationSpeed}
            translationSpeed={translationSpeed}
            translationSpeedMin={translationSpeedMin}
            translationSpeedMax={translationSpeedMax}
            translationSpeedStep={translationSpeedStep}
            onTranslationSpeedChange={onTranslationSpeedChange}
            showSubtitleScale={showSubtitleScale}
            subtitleScale={subtitleScale}
            subtitleScaleMin={subtitleScaleMin}
            subtitleScaleMax={subtitleScaleMax}
            subtitleScaleStep={subtitleScaleStep}
            onSubtitleScaleChange={onSubtitleScaleChange}
            showSubtitleBackgroundOpacity={showSubtitleBackgroundOpacity}
            subtitleBackgroundOpacityPercent={subtitleBackgroundOpacityPercent}
            subtitleBackgroundOpacityMin={subtitleBackgroundOpacityMin}
            subtitleBackgroundOpacityMax={subtitleBackgroundOpacityMax}
            subtitleBackgroundOpacityStep={subtitleBackgroundOpacityStep}
            onSubtitleBackgroundOpacityChange={onSubtitleBackgroundOpacityChange}
            disableSubtitleToggle={disableSubtitleToggle}
            subtitlesEnabled={subtitlesEnabled}
            showFontScale={showFontScale}
            fontScalePercent={fontScalePercent}
            fontScaleMin={fontScaleMin}
            fontScaleMax={fontScaleMax}
            fontScaleStep={fontScaleStep}
            onFontScaleChange={onFontScaleChange}
            showMyLinguistFontScale={showMyLinguistFontScale}
            myLinguistFontScalePercent={myLinguistFontScalePercent}
            myLinguistFontScaleMin={myLinguistFontScaleMin}
            myLinguistFontScaleMax={myLinguistFontScaleMax}
            myLinguistFontScaleStep={myLinguistFontScaleStep}
            onMyLinguistFontScaleChange={onMyLinguistFontScaleChange}
            showInteractiveBackgroundOpacity={showInteractiveBackgroundOpacity}
            interactiveBackgroundOpacityPercent={interactiveBackgroundOpacityPercent}
            interactiveBackgroundOpacityMin={interactiveBackgroundOpacityMin}
            interactiveBackgroundOpacityMax={interactiveBackgroundOpacityMax}
            interactiveBackgroundOpacityStep={interactiveBackgroundOpacityStep}
            onInteractiveBackgroundOpacityChange={onInteractiveBackgroundOpacityChange}
            showInteractiveSentenceCardOpacity={showInteractiveSentenceCardOpacity}
            interactiveSentenceCardOpacityPercent={interactiveSentenceCardOpacityPercent}
            interactiveSentenceCardOpacityMin={interactiveSentenceCardOpacityMin}
            interactiveSentenceCardOpacityMax={interactiveSentenceCardOpacityMax}
            interactiveSentenceCardOpacityStep={interactiveSentenceCardOpacityStep}
            onInteractiveSentenceCardOpacityChange={onInteractiveSentenceCardOpacityChange}
            showReadingBedVolume={showReadingBedVolume}
            readingBedVolumePercent={readingBedVolumePercent}
            readingBedVolumeMin={readingBedVolumeMin}
            readingBedVolumeMax={readingBedVolumeMax}
            readingBedVolumeStep={readingBedVolumeStep}
            onReadingBedVolumeChange={onReadingBedVolumeChange}
            showReadingBedTrack={showReadingBedTrack}
            readingBedTrack={readingBedTrack}
            readingBedTrackOptions={readingBedTrackOptions}
            onReadingBedTrackChange={onReadingBedTrackChange}
            disableReadingBedToggle={disableReadingBedToggle}
            readingBedEnabled={readingBedEnabled}
          />

          {showInteractiveThemeControls && interactiveTheme ? (
            <ThemeColorPickers
              interactiveTheme={interactiveTheme}
              onInteractiveThemeChange={onInteractiveThemeChange}
              onResetLayout={onResetLayout}
            />
          ) : null}
        </div>
      ) : null}

      {/* Stacked layout controls (non-compact mode) */}
      {shouldShowAdvancedControls && controlsLayout !== 'compact' && showTranslationSpeed ? (
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

      {shouldShowAdvancedControls && controlsLayout !== 'compact' && showSubtitleScale ? (
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

      {shouldShowAdvancedControls && controlsLayout !== 'compact' && showSubtitleBackgroundOpacity ? (
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

      {shouldShowAdvancedControls && showSentenceJump && controlsLayout !== 'compact' ? (
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

      {shouldShowAdvancedControls && showFontScale && !shouldShowCompactControls ? (
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

      {shouldShowAdvancedControls && showMyLinguistFontScale && !shouldShowCompactControls ? (
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
