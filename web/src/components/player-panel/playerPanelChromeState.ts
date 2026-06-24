import type { NavigationControlsProps } from './navigation';

type PlayerPanelOrigin = 'job' | 'library';

type AdvancedControlVisibility = Partial<
  Pick<
    NavigationControlsProps,
    | 'showTranslationSpeed'
    | 'showSubtitleScale'
    | 'showSubtitleBackgroundOpacity'
    | 'showFontScale'
    | 'showMyLinguistFontScale'
    | 'showInteractiveBackgroundOpacity'
    | 'showInteractiveSentenceCardOpacity'
    | 'showInteractiveThemeControls'
    | 'showReadingBedVolume'
    | 'showReadingBedTrack'
  >
>;

type BuildPlayerPanelChromeStateArgs = {
  mediaTextCount: number;
  mediaAudioCount: number;
  mediaVideoCount: number;
  isLoading: boolean;
  hasInlineAudioControls: boolean;
  canRenderInteractiveViewer: boolean;
  isInlineAudioPlaying: boolean;
  origin: PlayerPanelOrigin;
  showBackToLibrary: boolean;
};

export function hasPlayerPanelAdvancedControls(controls: AdvancedControlVisibility): boolean {
  return Boolean(
    controls.showTranslationSpeed ||
      controls.showSubtitleScale ||
      controls.showSubtitleBackgroundOpacity ||
      controls.showFontScale ||
      controls.showMyLinguistFontScale ||
      controls.showInteractiveBackgroundOpacity ||
      controls.showInteractiveSentenceCardOpacity ||
      controls.showInteractiveThemeControls ||
      controls.showReadingBedVolume ||
      controls.showReadingBedTrack,
  );
}

export function buildPlayerPanelChromeState({
  mediaTextCount,
  mediaAudioCount,
  mediaVideoCount,
  isLoading,
  hasInlineAudioControls,
  canRenderInteractiveViewer,
  isInlineAudioPlaying,
  origin,
  showBackToLibrary,
}: BuildPlayerPanelChromeStateArgs) {
  const hasAnyMedia = mediaTextCount + mediaAudioCount + mediaVideoCount > 0;
  const playbackControlsAvailable = hasInlineAudioControls;

  return {
    hasAnyMedia,
    hasTextItems: mediaTextCount > 0,
    isInitialLoading: isLoading && !hasAnyMedia,
    playbackControlsAvailable,
    isActiveMediaPlaying: isInlineAudioPlaying,
    shouldHoldWakeLock: isInlineAudioPlaying,
    isPlaybackDisabled: !playbackControlsAvailable,
    isFullscreenDisabled: !canRenderInteractiveViewer,
    shouldShowBackToLibrary: origin === 'library' && showBackToLibrary,
  };
}
