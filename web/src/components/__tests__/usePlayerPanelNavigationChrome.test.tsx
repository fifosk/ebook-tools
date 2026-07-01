import { act, render, renderHook, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DEFAULT_INTERACTIVE_TEXT_THEME } from '../../types/interactiveTextTheme';
import { usePlayerPanelNavigationChrome } from '../player-panel/usePlayerPanelNavigationChrome';
import type { NavigationControlsProps } from '../player-panel/NavigationControls';

const navigationControlsMock = vi.hoisted(() => ({
  calls: [] as NavigationControlsProps[],
}));

vi.mock('../player-panel/NavigationControls', () => ({
  NavigationControls: (props: NavigationControlsProps) => {
    navigationControlsMock.calls.push(props);
    const role = props.context === 'panel'
      ? 'panel'
      : props.showPrimaryControls === false
        ? 'fullscreen-advanced'
        : 'fullscreen-main';
    return (
      <div data-testid={`navigation-${role}`}>
        {props.searchPanel}
        {props.sleepTimerControl}
      </div>
    );
  },
}));

type HookArgs = Parameters<typeof usePlayerPanelNavigationChrome>[0];

function args(overrides: Partial<HookArgs> = {}): HookArgs {
  const base: HookArgs = {
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
        max: 30,
        exact: new Map(),
        ranges: [],
        suggestions: [1, 10, 20],
      },
      canJumpToSentence: true,
      sentenceJumpPlaceholder: '1-30',
      sentenceJumpValue: '10',
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
      effectiveTranslationAudioEnabled: true,
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
    sentenceTotals: {
      activeSentenceNumber: 7,
      chapterScopeStart: 1,
      chapterScopeEnd: 30,
      bookSentenceCount: 300,
    },
    onResetLayout: vi.fn(),
    sleepTimerControl: <span>Sleep timer</span>,
    panelSearchPanel: <span>Panel search</span>,
    fullscreenSearchPanel: <span>Fullscreen search</span>,
  };

  return { ...base, ...overrides };
}

describe('usePlayerPanelNavigationChrome', () => {
  beforeEach(() => {
    navigationControlsMock.calls = [];
  });

  it('builds panel and fullscreen navigation with shared generated sentence ids', () => {
    const { result } = renderHook(() => usePlayerPanelNavigationChrome(args()));

    render(
      <>
        {result.current.panelNavigation}
        {result.current.fullscreenMainControls}
      </>,
    );

    expect(screen.getByTestId('navigation-panel')).toHaveTextContent('Panel search');
    expect(screen.getByTestId('navigation-panel')).toHaveTextContent('Sleep timer');
    expect(screen.getByTestId('navigation-fullscreen-main')).toHaveTextContent('Fullscreen search');
    expect(navigationControlsMock.calls[0]).toMatchObject({
      context: 'panel',
      sentenceJumpListId: result.current.sentenceJumpListId,
      showAdvancedToggle: true,
      advancedControlsOpen: false,
    });
    expect(navigationControlsMock.calls[1]).toMatchObject({
      context: 'fullscreen',
      sentenceJumpListId: result.current.sentenceJumpListId,
      showPrimaryControls: true,
    });
    expect(navigationControlsMock.calls[0].sentenceJumpInputId).not.toEqual(
      navigationControlsMock.calls[1].sentenceJumpInputId,
    );
  });

  it('owns the panel advanced-controls toggle state', () => {
    const { result } = renderHook(() => usePlayerPanelNavigationChrome(args()));
    const view = render(<>{result.current.panelNavigation}</>);

    expect(navigationControlsMock.calls.at(-1)).toMatchObject({
      advancedControlsOpen: false,
    });

    act(() => {
      navigationControlsMock.calls.at(-1)?.onToggleAdvancedControls?.();
    });
    view.rerender(<>{result.current.panelNavigation}</>);

    expect(navigationControlsMock.calls.at(-1)).toMatchObject({
      advancedControlsOpen: true,
    });
  });
});
