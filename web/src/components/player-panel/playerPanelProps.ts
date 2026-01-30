import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import InteractiveTextViewer from '../InteractiveTextViewer';
import type { ChapterNavigationEntry, NavigationControlsProps } from './NavigationControls';
import type { SentenceLookup } from './helpers';
import {
  FONT_SCALE_MAX,
  FONT_SCALE_MIN,
  FONT_SCALE_STEP,
  MY_LINGUIST_FONT_SCALE_MAX,
  MY_LINGUIST_FONT_SCALE_MIN,
  MY_LINGUIST_FONT_SCALE_STEP,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
} from './constants';

type NavigationBaseProps = Omit<NavigationControlsProps, 'context' | 'sentenceJumpInputId'>;
type InteractiveTextViewerProps = ComponentPropsWithoutRef<typeof InteractiveTextViewer>;

type NavigationHandlers = {
  onNavigate: NavigationBaseProps['onNavigate'];
  onToggleFullscreen: NavigationBaseProps['onToggleFullscreen'];
  onTogglePlayback: NavigationBaseProps['onTogglePlayback'];
  disableFirst: boolean;
  disablePrevious: boolean;
  disableNext: boolean;
  disableLast: boolean;
  disablePlayback: boolean;
  disableFullscreen: boolean;
  isFullscreen: boolean;
  isPlaying: boolean;
  fullscreenLabel: string;
  showBackToLibrary: boolean;
  onBackToLibrary: NavigationBaseProps['onBackToLibrary'];
};

type SentenceNavigation = {
  sentenceLookup: SentenceLookup;
  canJumpToSentence: boolean;
  sentenceJumpPlaceholder: string | undefined;
  sentenceJumpValue: string;
  sentenceJumpError: string | null;
  onSentenceJumpChange: (value: string) => void;
  onSentenceJumpSubmit: () => void;
};

type TextSettings = {
  interactiveTextVisibility: NavigationBaseProps['cueVisibility'];
  toggleInteractiveTextLayer: NavigationBaseProps['onToggleCueLayer'];
  translationSpeed: NavigationBaseProps['translationSpeed'];
  setTranslationSpeed: NavigationBaseProps['onTranslationSpeedChange'];
  fontScalePercent: NavigationBaseProps['fontScalePercent'];
  setFontScalePercent: NavigationBaseProps['onFontScaleChange'];
  interactiveTextTheme: NavigationBaseProps['interactiveTheme'];
  setInteractiveTextTheme: NavigationBaseProps['onInteractiveThemeChange'];
  interactiveBackgroundOpacityPercent: NavigationBaseProps['interactiveBackgroundOpacityPercent'];
  setInteractiveBackgroundOpacityPercent: NavigationBaseProps['onInteractiveBackgroundOpacityChange'];
  interactiveSentenceCardOpacityPercent: NavigationBaseProps['interactiveSentenceCardOpacityPercent'];
  setInteractiveSentenceCardOpacityPercent: NavigationBaseProps['onInteractiveSentenceCardOpacityChange'];
};

type MyLinguistSettings = {
  enabled: boolean;
  baseFontScalePercent: number;
  setBaseFontScalePercent: (value: number) => void;
};

type InlineAudioOptions = {
  canToggleOriginalAudio: boolean;
  canToggleTranslationAudio: boolean;
  effectiveOriginalAudioEnabled: boolean;
  effectiveTranslationAudioEnabled: boolean;
  handleOriginalAudioToggle: NavigationBaseProps['onToggleOriginalAudio'];
  handleTranslationAudioToggle: NavigationBaseProps['onToggleTranslationAudio'];
};

type ReadingBedControls = {
  readingBedEnabled: NavigationBaseProps['readingBedEnabled'];
  readingBedSupported: boolean;
  toggleReadingBed: NavigationBaseProps['onToggleReadingBed'];
  readingBedVolumePercent: NavigationBaseProps['readingBedVolumePercent'];
  onReadingBedVolumeChange: NavigationBaseProps['onReadingBedVolumeChange'];
  readingBedTrackSelection: string | null;
  readingBedTrackOptions: NavigationBaseProps['readingBedTrackOptions'];
  onReadingBedTrackChange: NavigationBaseProps['onReadingBedTrackChange'];
};

type Chapters = {
  chapterEntries: ChapterNavigationEntry[];
  activeChapterId: string | null;
  onChapterJump: NavigationBaseProps['onChapterJump'];
};

type Bookmarks = {
  showBookmarks: boolean;
  bookmarks: NavigationBaseProps['bookmarks'];
  onAddBookmark: NavigationBaseProps['onAddBookmark'];
  onJumpToBookmark: NavigationBaseProps['onJumpToBookmark'];
  onRemoveBookmark: NavigationBaseProps['onRemoveBookmark'];
};

type ExportState = {
  canExport: boolean;
  isExporting: boolean;
  exportError: string | null;
  handleExport: NavigationBaseProps['onExport'];
};

type SentenceTotals = {
  activeSentenceNumber: NavigationBaseProps['activeSentenceNumber'];
  chapterScopeStart: NavigationBaseProps['jobStartSentence'];
  chapterScopeEnd: NavigationBaseProps['totalSentencesInBook'];
  bookSentenceCount: NavigationBaseProps['bookTotalSentences'];
};

type BuildNavigationBasePropsArgs = {
  navigation: NavigationHandlers;
  sentenceNavigation: SentenceNavigation;
  textSettings: TextSettings;
  myLinguist: MyLinguistSettings;
  inlineAudioOptions: InlineAudioOptions;
  readingBedControls: ReadingBedControls;
  chapters: Chapters;
  bookmarks: Bookmarks;
  exportState: ExportState;
  sentenceJumpListId: string;
  sentenceTotals: SentenceTotals;
  onResetLayout: NavigationBaseProps['onResetLayout'];
};

export function buildNavigationBaseProps({
  navigation,
  sentenceNavigation,
  textSettings,
  myLinguist,
  inlineAudioOptions,
  readingBedControls,
  chapters,
  bookmarks,
  exportState,
  sentenceJumpListId,
  sentenceTotals,
  onResetLayout,
}: BuildNavigationBasePropsArgs): NavigationBaseProps {
  return {
    onNavigate: navigation.onNavigate,
    onToggleFullscreen: navigation.onToggleFullscreen,
    onTogglePlayback: navigation.onTogglePlayback,
    controlsLayout: 'compact',
    disableFirst: navigation.disableFirst,
    disablePrevious: navigation.disablePrevious,
    disableNext: navigation.disableNext,
    disableLast: navigation.disableLast,
    disablePlayback: navigation.disablePlayback,
    disableFullscreen: navigation.disableFullscreen,
    isFullscreen: navigation.isFullscreen,
    isPlaying: navigation.isPlaying,
    fullscreenLabel: navigation.fullscreenLabel,
    showBackToLibrary: navigation.showBackToLibrary,
    onBackToLibrary: navigation.onBackToLibrary,
    showOriginalAudioToggle: inlineAudioOptions.canToggleOriginalAudio,
    onToggleOriginalAudio: inlineAudioOptions.handleOriginalAudioToggle,
    originalAudioEnabled: inlineAudioOptions.effectiveOriginalAudioEnabled,
    disableOriginalAudioToggle: !inlineAudioOptions.canToggleOriginalAudio,
    showTranslationAudioToggle: inlineAudioOptions.canToggleTranslationAudio,
    onToggleTranslationAudio: inlineAudioOptions.handleTranslationAudioToggle,
    translationAudioEnabled: inlineAudioOptions.effectiveTranslationAudioEnabled,
    disableTranslationAudioToggle: !inlineAudioOptions.canToggleTranslationAudio,
    showCueLayerToggles: true,
    cueVisibility: textSettings.interactiveTextVisibility,
    onToggleCueLayer: textSettings.toggleInteractiveTextLayer,
    showTranslationSpeed: true,
    translationSpeed: textSettings.translationSpeed,
    translationSpeedMin: TRANSLATION_SPEED_MIN,
    translationSpeedMax: TRANSLATION_SPEED_MAX,
    translationSpeedStep: TRANSLATION_SPEED_STEP,
    onTranslationSpeedChange: textSettings.setTranslationSpeed,
    showSubtitleScale: false,
    showSubtitleBackgroundOpacity: false,
    showSentenceJump: sentenceNavigation.canJumpToSentence,
    sentenceJumpValue: sentenceNavigation.sentenceJumpValue,
    sentenceJumpMin: sentenceNavigation.sentenceLookup.min,
    sentenceJumpMax: sentenceNavigation.sentenceLookup.max,
    sentenceJumpError: sentenceNavigation.sentenceJumpError,
    sentenceJumpDisabled: !sentenceNavigation.canJumpToSentence,
    sentenceJumpListId,
    sentenceJumpPlaceholder: sentenceNavigation.sentenceJumpPlaceholder,
    onSentenceJumpChange: sentenceNavigation.onSentenceJumpChange,
    onSentenceJumpSubmit: sentenceNavigation.onSentenceJumpSubmit,
    showFontScale: true,
    fontScalePercent: textSettings.fontScalePercent,
    fontScaleMin: FONT_SCALE_MIN,
    fontScaleMax: FONT_SCALE_MAX,
    fontScaleStep: FONT_SCALE_STEP,
    onFontScaleChange: textSettings.setFontScalePercent,
    showMyLinguistFontScale: myLinguist.enabled,
    myLinguistFontScalePercent: myLinguist.baseFontScalePercent,
    myLinguistFontScaleMin: MY_LINGUIST_FONT_SCALE_MIN,
    myLinguistFontScaleMax: MY_LINGUIST_FONT_SCALE_MAX,
    myLinguistFontScaleStep: MY_LINGUIST_FONT_SCALE_STEP,
    onMyLinguistFontScaleChange: myLinguist.enabled ? myLinguist.setBaseFontScalePercent : undefined,
    showInteractiveThemeControls: true,
    interactiveTheme: textSettings.interactiveTextTheme,
    onInteractiveThemeChange: textSettings.setInteractiveTextTheme,
    showInteractiveBackgroundOpacity: true,
    interactiveBackgroundOpacityPercent: textSettings.interactiveBackgroundOpacityPercent,
    interactiveBackgroundOpacityMin: 0,
    interactiveBackgroundOpacityMax: 100,
    interactiveBackgroundOpacityStep: 5,
    onInteractiveBackgroundOpacityChange: textSettings.setInteractiveBackgroundOpacityPercent,
    showInteractiveSentenceCardOpacity: true,
    interactiveSentenceCardOpacityPercent: textSettings.interactiveSentenceCardOpacityPercent,
    interactiveSentenceCardOpacityMin: 0,
    interactiveSentenceCardOpacityMax: 100,
    interactiveSentenceCardOpacityStep: 5,
    onInteractiveSentenceCardOpacityChange: textSettings.setInteractiveSentenceCardOpacityPercent,
    onResetLayout,
    showReadingBedToggle: true,
    readingBedEnabled: readingBedControls.readingBedEnabled,
    disableReadingBedToggle: !readingBedControls.readingBedSupported,
    onToggleReadingBed: readingBedControls.toggleReadingBed,
    showReadingBedVolume: true,
    readingBedVolumePercent: readingBedControls.readingBedVolumePercent,
    readingBedVolumeMin: 0,
    readingBedVolumeMax: 100,
    readingBedVolumeStep: 5,
    onReadingBedVolumeChange: readingBedControls.onReadingBedVolumeChange,
    showReadingBedTrack: true,
    readingBedTrack: readingBedControls.readingBedTrackSelection ?? '',
    readingBedTrackOptions: readingBedControls.readingBedTrackOptions,
    onReadingBedTrackChange: readingBedControls.onReadingBedTrackChange,
    showChapterJump: chapters.chapterEntries.length > 0 && sentenceNavigation.canJumpToSentence,
    chapters: chapters.chapterEntries,
    activeChapterId: chapters.activeChapterId,
    onChapterJump: chapters.onChapterJump,
    showBookmarks: bookmarks.showBookmarks,
    bookmarks: bookmarks.bookmarks,
    onAddBookmark: bookmarks.onAddBookmark,
    onJumpToBookmark: bookmarks.onJumpToBookmark,
    onRemoveBookmark: bookmarks.onRemoveBookmark,
    showExport: exportState.canExport,
    onExport: exportState.handleExport,
    exportDisabled: exportState.isExporting,
    exportBusy: exportState.isExporting,
    exportLabel: exportState.isExporting ? 'Preparing export' : 'Export offline player',
    exportTitle: exportState.isExporting ? 'Preparing export...' : 'Export offline player',
    exportError: exportState.exportError,
    activeSentenceNumber: sentenceTotals.activeSentenceNumber,
    totalSentencesInBook: sentenceTotals.chapterScopeEnd,
    jobStartSentence: sentenceTotals.chapterScopeStart,
    bookTotalSentences: sentenceTotals.bookSentenceCount,
  };
}

type SubtitleInfo = {
  title: string | null;
  meta: string | null;
  coverUrl: string | null;
  coverSecondaryUrl: string | null;
  coverAltText: string | null;
};

type BuildInteractiveViewerPropsArgs = {
  core: {
    playerMode: InteractiveTextViewerProps['playerMode'];
    playerFeatures: InteractiveTextViewerProps['playerFeatures'];
    content: InteractiveTextViewerProps['content'];
    rawContent: InteractiveTextViewerProps['rawContent'];
    chunk: InteractiveTextViewerProps['chunk'];
    chunks: InteractiveTextViewerProps['chunks'];
    activeChunkIndex: InteractiveTextViewerProps['activeChunkIndex'];
    bookSentenceCount: number | null;
    jobStartSentence: InteractiveTextViewerProps['jobStartSentence'];
    jobEndSentence: InteractiveTextViewerProps['jobEndSentence'];
    jobOriginalLanguage: InteractiveTextViewerProps['jobOriginalLanguage'];
    jobTranslationLanguage: InteractiveTextViewerProps['jobTranslationLanguage'];
    cueVisibility: InteractiveTextViewerProps['cueVisibility'];
    onToggleCueVisibility: InteractiveTextViewerProps['onToggleCueVisibility'];
    activeAudioUrl: InteractiveTextViewerProps['activeAudioUrl'];
    noAudioAvailable: InteractiveTextViewerProps['noAudioAvailable'];
    jobId: InteractiveTextViewerProps['jobId'];
    onActiveSentenceChange: InteractiveTextViewerProps['onActiveSentenceChange'];
    onRequestSentenceJump: InteractiveTextViewerProps['onRequestSentenceJump'];
    onScroll: InteractiveTextViewerProps['onScroll'];
    onAudioProgress: InteractiveTextViewerProps['onAudioProgress'];
    getStoredAudioPosition: InteractiveTextViewerProps['getStoredAudioPosition'];
    onRegisterInlineAudioControls: InteractiveTextViewerProps['onRegisterInlineAudioControls'];
    onInlineAudioPlaybackStateChange: InteractiveTextViewerProps['onInlineAudioPlaybackStateChange'];
    onRequestAdvanceChunk: InteractiveTextViewerProps['onRequestAdvanceChunk'];
    onRegisterSequenceSkip: InteractiveTextViewerProps['onRegisterSequenceSkip'];
  };
  fullscreen: {
    isFullscreen: InteractiveTextViewerProps['isFullscreen'];
    onRequestExitFullscreen: InteractiveTextViewerProps['onRequestExitFullscreen'];
    fullscreenControls: ReactNode | null;
    fullscreenAdvancedControls: ReactNode | null;
    shortcutHelpOverlay: ReactNode | null;
  };
  playback: {
    translationSpeed: InteractiveTextViewerProps['translationSpeed'];
    audioTracks: InteractiveTextViewerProps['audioTracks'];
    activeTimingTrack: InteractiveTextViewerProps['activeTimingTrack'];
    originalAudioEnabled: InteractiveTextViewerProps['originalAudioEnabled'];
    translationAudioEnabled: InteractiveTextViewerProps['translationAudioEnabled'];
  };
  appearance: {
    fontScale: InteractiveTextViewerProps['fontScale'];
    theme: InteractiveTextViewerProps['theme'];
    backgroundOpacityPercent: InteractiveTextViewerProps['backgroundOpacityPercent'];
    sentenceCardOpacityPercent: InteractiveTextViewerProps['sentenceCardOpacityPercent'];
  };
  info: {
    channelBug: { glyph: string; label: string };
    isSubtitleContext: boolean;
    subtitleInfo: SubtitleInfo;
  };
  book: {
    bookTitle: string | null;
    bookAuthor: string | null;
    bookYear: string | null;
    bookGenre: string | null;
    displayCoverUrl: string | null;
    coverAltText: string;
    shouldShowCoverImage: boolean;
  };
};

export function buildInteractiveViewerProps({
  core,
  fullscreen,
  playback,
  appearance,
  info,
  book,
}: BuildInteractiveViewerPropsArgs): InteractiveTextViewerProps {
  return {
    playerMode: core.playerMode,
    playerFeatures: core.playerFeatures,
    content: core.content,
    rawContent: core.rawContent,
    chunk: core.chunk,
    chunks: core.chunks,
    activeChunkIndex: core.activeChunkIndex,
    totalSentencesInBook: core.bookSentenceCount,
    bookTotalSentences: core.bookSentenceCount,
    jobStartSentence: core.jobStartSentence,
    jobEndSentence: core.jobEndSentence,
    jobOriginalLanguage: core.jobOriginalLanguage,
    jobTranslationLanguage: core.jobTranslationLanguage,
    cueVisibility: core.cueVisibility,
    onToggleCueVisibility: core.onToggleCueVisibility,
    activeAudioUrl: core.activeAudioUrl,
    noAudioAvailable: core.noAudioAvailable,
    jobId: core.jobId,
    onActiveSentenceChange: core.onActiveSentenceChange,
    onRequestSentenceJump: core.onRequestSentenceJump,
    onScroll: core.onScroll,
    onAudioProgress: core.onAudioProgress,
    getStoredAudioPosition: core.getStoredAudioPosition,
    onRegisterInlineAudioControls: core.onRegisterInlineAudioControls,
    onInlineAudioPlaybackStateChange: core.onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk: core.onRequestAdvanceChunk,
    onRegisterSequenceSkip: core.onRegisterSequenceSkip,
    isFullscreen: fullscreen.isFullscreen,
    onRequestExitFullscreen: fullscreen.onRequestExitFullscreen,
    fullscreenControls: fullscreen.fullscreenControls,
    fullscreenAdvancedControls: fullscreen.fullscreenAdvancedControls,
    shortcutHelpOverlay: fullscreen.shortcutHelpOverlay,
    translationSpeed: playback.translationSpeed,
    audioTracks: playback.audioTracks,
    activeTimingTrack: playback.activeTimingTrack,
    originalAudioEnabled: playback.originalAudioEnabled,
    translationAudioEnabled: playback.translationAudioEnabled,
    fontScale: appearance.fontScale,
    theme: appearance.theme,
    backgroundOpacityPercent: appearance.backgroundOpacityPercent,
    sentenceCardOpacityPercent: appearance.sentenceCardOpacityPercent,
    infoGlyph: info.channelBug.glyph,
    infoGlyphLabel: info.channelBug.label,
    infoTitle: info.isSubtitleContext ? info.subtitleInfo.title : null,
    infoMeta: info.isSubtitleContext ? info.subtitleInfo.meta : null,
    infoCoverUrl: info.isSubtitleContext ? info.subtitleInfo.coverUrl : null,
    infoCoverSecondaryUrl: info.isSubtitleContext ? info.subtitleInfo.coverSecondaryUrl : null,
    infoCoverAltText: info.isSubtitleContext ? info.subtitleInfo.coverAltText : null,
    infoCoverVariant: (info.isSubtitleContext ? 'subtitles' : null) as 'subtitles' | null,
    bookTitle: book.bookTitle ?? 'Player',
    bookAuthor: book.bookAuthor,
    bookYear: book.bookYear,
    bookGenre: book.bookGenre,
    bookCoverUrl: book.shouldShowCoverImage ? book.displayCoverUrl : null,
    bookCoverAltText: book.coverAltText,
  };
}
