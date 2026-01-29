import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

// MARK: - Playback Configuration

struct VideoPlayerPlaybackConfig {
    let currentTime: Double
    let duration: Double
    let isPlaying: Bool
    let playbackRate: Double
    let playbackRateOptions: [Double]
    let isScrubbing: Bool
    let scrubberValue: Double
}

// MARK: - Subtitle Configuration

struct VideoPlayerSubtitleConfig {
    let cues: [VideoSubtitleCue]
    let tracks: [VideoSubtitleTrack]
    let selectedTrack: VideoSubtitleTrack?
    let visibility: SubtitleVisibility
    let fontScale: CGFloat
    let selection: VideoSubtitleWordSelection?
    let selectionRange: VideoSubtitleWordSelectionRange?
    let alignment: HorizontalAlignment
    let maxWidth: CGFloat?
    let leadingInset: CGFloat
    let error: String?
}

// MARK: - Linguist Bubble Configuration

struct VideoPlayerLinguistConfig {
    let bubble: VideoLinguistBubbleState?
    let fontScale: CGFloat
    let canIncreaseFont: Bool
    let canDecreaseFont: Bool
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let llmModel: String
    let llmModelOptions: [String]
}

// MARK: - Header Configuration

struct VideoPlayerHeaderConfig {
    let metadata: VideoPlaybackMetadata
    let isCollapsed: Bool
    let topInset: CGFloat
    let scaleValue: Double
    let segmentOptions: [VideoSegmentOption]
    let selectedSegmentID: String?
    let jobProgressLabel: String?
    let jobRemainingLabel: String?
}

// MARK: - Bookmark Configuration

struct VideoPlayerBookmarkConfig {
    let bookmarks: [PlaybackBookmarkEntry]
    let canShowBookmarks: Bool
}

// MARK: - Callback Closures

struct VideoPlayerOverlayCallbacks {
    // Playback
    let onPlayPause: () -> Void
    let onSkipForward: () -> Void
    let onSkipBackward: () -> Void
    let onSeek: (Double) -> Void
    let onSkipSentence: (Int) -> Void
    let onPlaybackRateChange: (Double) -> Void

    // Subtitles
    let onNavigateSubtitleWord: (Int) -> Void
    let onNavigateSubtitleTrack: (Int) -> Bool
    let onSubtitleLookup: () -> Void
    let onSubtitleTokenLookup: (VideoSubtitleTokenReference) -> Void
    let onSubtitleTokenSeek: (VideoSubtitleTokenReference) -> Void
    let onUpdateSubtitleSelectionRange: (VideoSubtitleWordSelectionRange, VideoSubtitleWordSelection) -> Void
    let onSubtitleInteractionFrameChange: (CGRect) -> Void
    let onToggleTransliteration: () -> Void
    let onResetSubtitleFont: (() -> Void)?
    let onSetSubtitleFont: ((CGFloat) -> Void)?

    // Linguist Bubble
    let onLookupLanguageChange: (String) -> Void
    let onLlmModelChange: (String) -> Void
    let onIncreaseSubtitleLinguistFont: () -> Void
    let onDecreaseSubtitleLinguistFont: () -> Void
    let onResetSubtitleBubbleFont: (() -> Void)?
    let onSetSubtitleBubbleFont: ((CGFloat) -> Void)?
    let onCloseSubtitleBubble: () -> Void

    // Header
    let onToggleHeaderCollapsed: () -> Void
    let onSelectSegment: ((String) -> Void)?

    // Bookmarks
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void

    // General
    let onUserInteraction: () -> Void
}

// MARK: - Binding Wrapper

struct VideoPlayerOverlayBindings {
    let selectedTrack: Binding<VideoSubtitleTrack?>
    let subtitleVisibility: Binding<SubtitleVisibility>
    let showSubtitleSettings: Binding<Bool>
    let showTVControls: Binding<Bool>
    let scrubberValue: Binding<Double>
    let isScrubbing: Binding<Bool>
}

// MARK: - tvOS Focus Target

#if os(tvOS)
enum TVPlayerControlTarget: Hashable {
    case playPause
    case skipBackward
    case skipForward
    case bookmark
    case speed
    case captions
    case header
    case headerBookmark
    case scrubber
}

enum VideoPlayerFocusTarget: Hashable {
    case subtitles
    case bubble
    case control(TVPlayerControlTarget)
}
#endif

// MARK: - Platform Helpers

enum VideoPlayerPlatform {
    static var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    static var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    static var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }
}
