import {
  DEFAULT_INTERACTIVE_TEXT_BG_OPACITY_PERCENT,
  DEFAULT_INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_PERCENT,
  DEFAULT_READING_BED_VOLUME_PERCENT,
  FONT_SCALE_MAX,
  FONT_SCALE_MIN,
  FONT_SCALE_STEP,
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
  StackedAdvancedControls,
} from './navigation';
import type { NavigationControlsProps } from './navigation';
import { buildNavigationControlsState } from './navigationControlsState';

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
  sleepTimerControl,
  jobStartSentence = null,
  totalSentencesInBook = null,
}: NavigationControlsProps) {
  const {
    shouldShowPrimaryControls,
    shouldShowAdvancedControls,
    groupClassName,
    navigationClassName,
    fullscreenTestId,
    searchInPrimary,
    searchInSecondary,
    showPrimaryInfoRow,
    advancedToggleClassName,
    advancedToggleLabel,
    resolvedExportLabel,
    resolvedExportTitle,
    shouldShowCompactControls,
  } = buildNavigationControlsState({
    context,
    controlsLayout,
    showPrimaryControls,
    showAdvancedControls,
    searchPanel,
    searchPlacement,
    advancedControlsOpen,
    exportBusy,
    exportLabel,
    exportTitle,
    showTranslationSpeed,
    showSubtitleScale,
    showSubtitleBackgroundOpacity,
    showFontScale,
    showMyLinguistFontScale,
    showInteractiveBackgroundOpacity,
    showInteractiveSentenceCardOpacity,
    showInteractiveThemeControls,
    showReadingBedVolume,
    showReadingBedTrack,
  });

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

            {sleepTimerControl}

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

      <StackedAdvancedControls
        showAdvancedControls={shouldShowAdvancedControls}
        controlsLayout={controlsLayout}
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
      />
    </div>
  );
}
