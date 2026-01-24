import type { ReactNode } from 'react';
import type { PlaybackBookmark } from '../../../hooks/usePlaybackBookmarks';
import type { InteractiveTextTheme } from '../../../types/interactiveTextTheme';
import type { NavigationIntent, TranslationSpeed } from '../constants';

export type ChapterNavigationEntry = {
  id: string;
  title: string;
  startSentence: number;
  endSentence?: number | null;
};

export interface CueVisibility {
  original: boolean;
  transliteration: boolean;
  translation: boolean;
}

/**
 * Props for primary playback control buttons.
 */
export interface PrimaryButtonsProps {
  onNavigate: (intent: NavigationIntent) => void;
  onToggleFullscreen: () => void;
  onTogglePlayback: () => void;
  disableFirst: boolean;
  disablePrevious: boolean;
  disableNext: boolean;
  disableLast: boolean;
  disablePlayback: boolean;
  disableFullscreen: boolean;
  isFullscreen: boolean;
  isPlaying: boolean;
  fullscreenLabel: string;
  fullscreenTestId?: string;
}

/**
 * Props for audio toggle buttons.
 */
export interface AudioTogglesProps {
  showOriginalAudioToggle?: boolean;
  onToggleOriginalAudio?: () => void;
  originalAudioEnabled?: boolean;
  disableOriginalAudioToggle?: boolean;
  showTranslationAudioToggle?: boolean;
  onToggleTranslationAudio?: () => void;
  translationAudioEnabled?: boolean;
  disableTranslationAudioToggle?: boolean;
  showSubtitleToggle?: boolean;
  onToggleSubtitles?: () => void;
  subtitlesEnabled?: boolean;
  disableSubtitleToggle?: boolean;
  showReadingBedToggle?: boolean;
  readingBedEnabled?: boolean;
  disableReadingBedToggle?: boolean;
  onToggleReadingBed?: () => void;
}

/**
 * Props for cue layer toggle buttons.
 */
export interface CueLayerTogglesProps {
  showCueLayerToggles?: boolean;
  cueVisibility?: CueVisibility;
  onToggleCueLayer?: (key: 'original' | 'transliteration' | 'translation') => void;
  disableCueLayerToggles?: boolean;
  disableSubtitleToggle?: boolean;
}

/**
 * Props for bookmark functionality.
 */
export interface BookmarkProps {
  showBookmarks?: boolean;
  bookmarks?: PlaybackBookmark[];
  onAddBookmark?: () => void;
  onJumpToBookmark?: (bookmark: PlaybackBookmark) => void;
  onRemoveBookmark?: (bookmark: PlaybackBookmark) => void;
}

/**
 * Props for export button.
 */
export interface ExportButtonProps {
  showExport?: boolean;
  exportDisabled?: boolean;
  exportBusy?: boolean;
  exportLabel?: string;
  exportTitle?: string;
  exportError?: string | null;
  onExport?: () => void;
}

/**
 * Props for advanced controls toggle.
 */
export interface AdvancedToggleProps {
  showAdvancedToggle?: boolean;
  advancedControlsOpen?: boolean;
  onToggleAdvancedControls?: () => void;
}

/**
 * Props for translation speed slider.
 */
export interface TranslationSpeedProps {
  showTranslationSpeed: boolean;
  translationSpeed: TranslationSpeed;
  translationSpeedMin: number;
  translationSpeedMax: number;
  translationSpeedStep: number;
  onTranslationSpeedChange: (value: TranslationSpeed) => void;
}

/**
 * Props for subtitle scale slider.
 */
export interface SubtitleScaleProps {
  showSubtitleScale?: boolean;
  subtitleScale?: number;
  subtitleScaleMin?: number;
  subtitleScaleMax?: number;
  subtitleScaleStep?: number;
  onSubtitleScaleChange?: (value: number) => void;
}

/**
 * Props for subtitle background opacity slider.
 */
export interface SubtitleBackgroundProps {
  showSubtitleBackgroundOpacity?: boolean;
  subtitleBackgroundOpacityPercent?: number;
  subtitleBackgroundOpacityMin?: number;
  subtitleBackgroundOpacityMax?: number;
  subtitleBackgroundOpacityStep?: number;
  onSubtitleBackgroundOpacityChange?: (value: number) => void;
  disableSubtitleToggle?: boolean;
  subtitlesEnabled?: boolean;
}

/**
 * Props for sentence jump input.
 */
export interface SentenceJumpProps {
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
}

/**
 * Props for font scale sliders.
 */
export interface FontScaleProps {
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
}

/**
 * Props for chapter jump select.
 */
export interface ChapterJumpProps {
  showChapterJump?: boolean;
  chapters?: ChapterNavigationEntry[];
  activeChapterId?: string | null;
  onChapterJump?: (chapterId: string) => void;
  jobStartSentence?: number | null;
  totalSentencesInBook?: number | null;
}

/**
 * Props for interactive theme controls.
 */
export interface InteractiveThemeProps {
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
}

/**
 * Props for reading bed controls.
 */
export interface ReadingBedProps {
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
  disableReadingBedToggle?: boolean;
  readingBedEnabled?: boolean;
}

/**
 * Props for now playing display.
 */
export interface NowPlayingProps {
  nowPlayingText?: string | null;
  nowPlayingTitle?: string | null;
  activeSentenceNumber?: number | null;
  totalSentencesInBook?: number | null;
  bookTotalSentences?: number | null;
}

/**
 * Props for search panel placement.
 */
export interface SearchPanelProps {
  searchPanel?: ReactNode;
  searchPlacement?: 'primary' | 'secondary';
}

/**
 * Combined interface for all NavigationControls props.
 */
export interface NavigationControlsProps
  extends PrimaryButtonsProps,
    AudioTogglesProps,
    CueLayerTogglesProps,
    BookmarkProps,
    ExportButtonProps,
    AdvancedToggleProps,
    TranslationSpeedProps,
    SubtitleScaleProps,
    SubtitleBackgroundProps,
    SentenceJumpProps,
    FontScaleProps,
    ChapterJumpProps,
    InteractiveThemeProps,
    ReadingBedProps,
    NowPlayingProps,
    SearchPanelProps {
  context: 'panel' | 'fullscreen';
  controlsLayout?: 'stacked' | 'compact';
  showBackToLibrary?: boolean;
  onBackToLibrary?: () => void;
  showPrimaryControls?: boolean;
  showAdvancedControls?: boolean;
  jobStartSentence?: number | null;
}
