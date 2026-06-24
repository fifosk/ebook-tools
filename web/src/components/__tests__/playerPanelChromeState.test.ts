import { describe, expect, it } from 'vitest';
import {
  buildPlayerPanelChromeState,
  hasPlayerPanelAdvancedControls,
} from '../player-panel/playerPanelChromeState';

function chromeState(
  overrides: Partial<Parameters<typeof buildPlayerPanelChromeState>[0]> = {},
) {
  return buildPlayerPanelChromeState({
    mediaTextCount: 0,
    mediaAudioCount: 0,
    mediaVideoCount: 0,
    isLoading: false,
    hasInlineAudioControls: false,
    canRenderInteractiveViewer: false,
    isInlineAudioPlaying: false,
    origin: 'job',
    showBackToLibrary: false,
    ...overrides,
  });
}

describe('buildPlayerPanelChromeState', () => {
  it('tracks media presence and initial loading state from media counts', () => {
    expect(chromeState({ isLoading: true })).toMatchObject({
      hasAnyMedia: false,
      hasTextItems: false,
      isInitialLoading: true,
    });

    expect(
      chromeState({
        mediaTextCount: 1,
        mediaAudioCount: 0,
        mediaVideoCount: 0,
        isLoading: true,
      }),
    ).toMatchObject({
      hasAnyMedia: true,
      hasTextItems: true,
      isInitialLoading: false,
    });

    expect(chromeState({ mediaVideoCount: 1 })).toMatchObject({
      hasAnyMedia: true,
      hasTextItems: false,
    });
  });

  it('derives playback, fullscreen, and wake-lock flags from active capabilities', () => {
    expect(
      chromeState({
        hasInlineAudioControls: false,
        canRenderInteractiveViewer: false,
        isInlineAudioPlaying: false,
      }),
    ).toMatchObject({
      playbackControlsAvailable: false,
      isPlaybackDisabled: true,
      isFullscreenDisabled: true,
      isActiveMediaPlaying: false,
      shouldHoldWakeLock: false,
    });

    expect(
      chromeState({
        hasInlineAudioControls: true,
        canRenderInteractiveViewer: true,
        isInlineAudioPlaying: true,
      }),
    ).toMatchObject({
      playbackControlsAvailable: true,
      isPlaybackDisabled: false,
      isFullscreenDisabled: false,
      isActiveMediaPlaying: true,
      shouldHoldWakeLock: true,
    });
  });

  it('shows the back-to-library control only for library-origin panels with the flag enabled', () => {
    expect(
      chromeState({
        origin: 'library',
        showBackToLibrary: true,
      }).shouldShowBackToLibrary,
    ).toBe(true);

    expect(
      chromeState({
        origin: 'job',
        showBackToLibrary: true,
      }).shouldShowBackToLibrary,
    ).toBe(false);

    expect(
      chromeState({
        origin: 'library',
        showBackToLibrary: false,
      }).shouldShowBackToLibrary,
    ).toBe(false);
  });
});

describe('hasPlayerPanelAdvancedControls', () => {
  it('detects compact advanced controls from any advanced visibility flag', () => {
    expect(hasPlayerPanelAdvancedControls({})).toBe(false);
    expect(hasPlayerPanelAdvancedControls({ showTranslationSpeed: true })).toBe(true);
    expect(hasPlayerPanelAdvancedControls({ showReadingBedTrack: true })).toBe(true);
  });
});
