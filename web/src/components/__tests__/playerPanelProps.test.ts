import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_INTERACTIVE_TEXT_THEME } from '../../types/interactiveTextTheme';
import { buildNavigationBaseProps } from '../player-panel/playerPanelProps';

type BuildNavigationBasePropsArgs = Parameters<typeof buildNavigationBaseProps>[0];

function args(overrides: Partial<BuildNavigationBasePropsArgs> = {}): BuildNavigationBasePropsArgs {
  const base: BuildNavigationBasePropsArgs = {
    navigation: {
      onNavigate: vi.fn(),
      onToggleFullscreen: vi.fn(),
      onTogglePlayback: vi.fn(),
      disableFirst: false,
      disablePrevious: false,
      disableNext: false,
      disableLast: false,
      disablePlayback: false,
      disableFullscreen: false,
      isFullscreen: false,
      isPlaying: false,
      fullscreenLabel: 'Enter fullscreen',
      showBackToLibrary: false,
      onBackToLibrary: undefined,
    },
    sentenceNavigation: {
      sentenceLookup: {
        min: 1,
        max: 25,
        exact: new Map(),
        ranges: [],
        suggestions: [1, 2, 3],
      },
      canJumpToSentence: true,
      sentenceJumpPlaceholder: '1-25',
      sentenceJumpValue: '7',
      sentenceJumpError: null,
      onSentenceJumpChange: vi.fn(),
      onSentenceJumpSubmit: vi.fn(),
    },
    textSettings: {
      interactiveTextVisibility: {
        original: true,
        transliteration: false,
        translation: true,
      },
      toggleInteractiveTextLayer: vi.fn(),
      translationSpeed: 1,
      setTranslationSpeed: vi.fn(),
      fontScalePercent: 125,
      setFontScalePercent: vi.fn(),
      interactiveTextTheme: DEFAULT_INTERACTIVE_TEXT_THEME,
      setInteractiveTextTheme: vi.fn(),
      interactiveBackgroundOpacityPercent: 80,
      setInteractiveBackgroundOpacityPercent: vi.fn(),
      interactiveSentenceCardOpacityPercent: 90,
      setInteractiveSentenceCardOpacityPercent: vi.fn(),
    },
    myLinguist: {
      enabled: true,
      baseFontScalePercent: 110,
      setBaseFontScalePercent: vi.fn(),
    },
    inlineAudioOptions: {
      canToggleOriginalAudio: true,
      canToggleTranslationAudio: true,
      effectiveOriginalAudioEnabled: true,
      effectiveTranslationAudioEnabled: false,
      handleOriginalAudioToggle: vi.fn(),
      handleTranslationAudioToggle: vi.fn(),
    },
    readingBedControls: {
      readingBedEnabled: true,
      readingBedSupported: true,
      toggleReadingBed: vi.fn(),
      readingBedVolumePercent: 35,
      onReadingBedVolumeChange: vi.fn(),
      readingBedTrackSelection: 'rain',
      readingBedTrackOptions: [{ value: 'rain', label: 'Rain' }],
      onReadingBedTrackChange: vi.fn(),
    },
    chapters: {
      chapterEntries: [{ id: 'chapter-1', title: 'One', startSentence: 1, endSentence: 10 }],
      activeChapterId: 'chapter-1',
      onChapterJump: vi.fn(),
    },
    bookmarks: {
      showBookmarks: true,
      bookmarks: [],
      onAddBookmark: vi.fn(),
      onJumpToBookmark: vi.fn(),
      onRemoveBookmark: vi.fn(),
    },
    exportState: {
      canExport: true,
      isExporting: false,
      exportError: null,
      handleExport: vi.fn(),
    },
    sentenceJumpListId: 'sentence-list',
    sentenceTotals: {
      activeSentenceNumber: 7,
      chapterScopeStart: 1,
      chapterScopeEnd: 25,
      bookSentenceCount: 300,
    },
    onResetLayout: vi.fn(),
  };

  return { ...base, ...overrides };
}

describe('buildNavigationBaseProps', () => {
  it('routes shared playback controls and sentence scope into navigation props', () => {
    const props = buildNavigationBaseProps(args());

    expect(props.controlsLayout).toBe('compact');
    expect(props.showSentenceJump).toBe(true);
    expect(props.sentenceJumpMin).toBe(1);
    expect(props.sentenceJumpMax).toBe(25);
    expect(props.sentenceJumpListId).toBe('sentence-list');
    expect(props.activeSentenceNumber).toBe(7);
    expect(props.totalSentencesInBook).toBe(25);
    expect(props.jobStartSentence).toBe(1);
    expect(props.bookTotalSentences).toBe(300);
  });

  it('keeps advanced media controls and sleep timer in the base prop bundle', () => {
    const sleepTimerControl = 'Sleep timer';
    const props = buildNavigationBaseProps(args({ sleepTimerControl }));

    expect(props.sleepTimerControl).toBe(sleepTimerControl);
    expect(props.showOriginalAudioToggle).toBe(true);
    expect(props.originalAudioEnabled).toBe(true);
    expect(props.showTranslationAudioToggle).toBe(true);
    expect(props.translationAudioEnabled).toBe(false);
    expect(props.showReadingBedTrack).toBe(true);
    expect(props.readingBedTrack).toBe('rain');
    expect(props.readingBedVolumePercent).toBe(35);
  });

  it('hides optional controls when their source state is unavailable', () => {
    const props = buildNavigationBaseProps(args({
      sentenceNavigation: {
        ...args().sentenceNavigation,
        canJumpToSentence: false,
      },
      chapters: {
        chapterEntries: [],
        activeChapterId: null,
        onChapterJump: vi.fn(),
      },
      myLinguist: {
        enabled: false,
        baseFontScalePercent: 100,
        setBaseFontScalePercent: vi.fn(),
      },
      exportState: {
        canExport: false,
        isExporting: false,
        exportError: null,
        handleExport: vi.fn(),
      },
    }));

    expect(props.showSentenceJump).toBe(false);
    expect(props.sentenceJumpDisabled).toBe(true);
    expect(props.showChapterJump).toBe(false);
    expect(props.showMyLinguistFontScale).toBe(false);
    expect(props.onMyLinguistFontScaleChange).toBeUndefined();
    expect(props.showExport).toBe(false);
  });
});
