import Foundation

// MARK: - Video Playback Actions

/// Actions for controlling video playback state
enum VideoPlaybackAction {
    case playPause
    case skipForward
    case skipBackward
    case seek(Double)
    case setPlaybackRate(Double)
    case skipSentence(Int)
}

// MARK: - Subtitle Actions

/// Actions for subtitle navigation and interaction
enum VideoSubtitleAction {
    case navigateWord(Int)
    case navigateTrack(Int)
    case lookup
    case tokenLookup(VideoSubtitleTokenReference)
    case tokenSeek(VideoSubtitleTokenReference)
    case updateSelectionRange(VideoSubtitleWordSelectionRange, VideoSubtitleWordSelection)
    case interactionFrameChange(CGRect)
    case toggleTransliteration
    case closeBubble
}

// MARK: - Font Scaling Actions

/// Actions for adjusting font sizes
enum VideoFontAction {
    case increaseSubtitleLinguistFont
    case decreaseSubtitleLinguistFont
    case resetSubtitleFont
    case setSubtitleFont(CGFloat)
    case resetSubtitleBubbleFont
    case setSubtitleBubbleFont(CGFloat)
}

// MARK: - Bookmark Actions

/// Actions for managing playback bookmarks
enum VideoBookmarkAction {
    case add
    case jumpTo(PlaybackBookmarkEntry)
    case remove(PlaybackBookmarkEntry)
}

// MARK: - Linguist Settings Actions

/// Actions for linguist lookup configuration
enum VideoLinguistSettingsAction {
    case setLookupLanguage(String)
    case setLlmModel(String)
}

// MARK: - UI Actions

/// Actions for UI state changes
enum VideoUIAction {
    case toggleHeaderCollapsed
    case selectSegment(String)
    case userInteraction
}

// MARK: - Action Handler Protocol

/// Protocol for handling video player actions
protocol VideoPlayerActionHandler {
    func handlePlayback(_ action: VideoPlaybackAction)
    func handleSubtitle(_ action: VideoSubtitleAction) -> Bool
    func handleFont(_ action: VideoFontAction)
    func handleBookmark(_ action: VideoBookmarkAction)
    func handleLinguistSettings(_ action: VideoLinguistSettingsAction)
    func handleUI(_ action: VideoUIAction)
}

/// Extension with default implementation for optional Bool return
extension VideoPlayerActionHandler {
    func handleSubtitle(_ action: VideoSubtitleAction) -> Bool {
        return true
    }
}

// MARK: - Action Handler Struct

/// Concrete implementation that wraps closures for backward compatibility
struct VideoPlayerActions: VideoPlayerActionHandler {
    // Playback closures
    var onPlayPause: () -> Void = {}
    var onSkipForward: () -> Void = {}
    var onSkipBackward: () -> Void = {}
    var onSeek: (Double) -> Void = { _ in }
    var onPlaybackRateChange: (Double) -> Void = { _ in }
    var onSkipSentence: (Int) -> Void = { _ in }

    // Subtitle closures
    var onNavigateSubtitleWord: (Int) -> Void = { _ in }
    var onNavigateSubtitleTrack: (Int) -> Bool = { _ in true }
    var onSubtitleLookup: () -> Void = {}
    var onSubtitleTokenLookup: (VideoSubtitleTokenReference) -> Void = { _ in }
    var onSubtitleTokenSeek: (VideoSubtitleTokenReference) -> Void = { _ in }
    var onUpdateSubtitleSelectionRange: (VideoSubtitleWordSelectionRange, VideoSubtitleWordSelection) -> Void = { _, _ in }
    var onSubtitleInteractionFrameChange: (CGRect) -> Void = { _ in }
    var onToggleTransliteration: () -> Void = {}
    var onCloseSubtitleBubble: () -> Void = {}

    // Font closures
    var onIncreaseSubtitleLinguistFont: () -> Void = {}
    var onDecreaseSubtitleLinguistFont: () -> Void = {}
    var onResetSubtitleFont: (() -> Void)?
    var onSetSubtitleFont: ((CGFloat) -> Void)?
    var onResetSubtitleBubbleFont: (() -> Void)?
    var onSetSubtitleBubbleFont: ((CGFloat) -> Void)?

    // Bookmark closures
    var onAddBookmark: (() -> Void)?
    var onJumpToBookmark: (PlaybackBookmarkEntry) -> Void = { _ in }
    var onRemoveBookmark: (PlaybackBookmarkEntry) -> Void = { _ in }

    // Linguist settings closures
    var onLookupLanguageChange: (String) -> Void = { _ in }
    var onLlmModelChange: (String) -> Void = { _ in }

    // UI closures
    var onToggleHeaderCollapsed: () -> Void = {}
    var onSelectSegment: ((String) -> Void)?
    var onUserInteraction: () -> Void = {}

    // MARK: - Protocol Implementation

    func handlePlayback(_ action: VideoPlaybackAction) {
        switch action {
        case .playPause:
            onPlayPause()
        case .skipForward:
            onSkipForward()
        case .skipBackward:
            onSkipBackward()
        case .seek(let time):
            onSeek(time)
        case .setPlaybackRate(let rate):
            onPlaybackRateChange(rate)
        case .skipSentence(let delta):
            onSkipSentence(delta)
        }
    }

    func handleSubtitle(_ action: VideoSubtitleAction) -> Bool {
        switch action {
        case .navigateWord(let delta):
            onNavigateSubtitleWord(delta)
            return true
        case .navigateTrack(let delta):
            return onNavigateSubtitleTrack(delta)
        case .lookup:
            onSubtitleLookup()
            return true
        case .tokenLookup(let ref):
            onSubtitleTokenLookup(ref)
            return true
        case .tokenSeek(let ref):
            onSubtitleTokenSeek(ref)
            return true
        case .updateSelectionRange(let range, let selection):
            onUpdateSubtitleSelectionRange(range, selection)
            return true
        case .interactionFrameChange(let frame):
            onSubtitleInteractionFrameChange(frame)
            return true
        case .toggleTransliteration:
            onToggleTransliteration()
            return true
        case .closeBubble:
            onCloseSubtitleBubble()
            return true
        }
    }

    func handleFont(_ action: VideoFontAction) {
        switch action {
        case .increaseSubtitleLinguistFont:
            onIncreaseSubtitleLinguistFont()
        case .decreaseSubtitleLinguistFont:
            onDecreaseSubtitleLinguistFont()
        case .resetSubtitleFont:
            onResetSubtitleFont?()
        case .setSubtitleFont(let scale):
            onSetSubtitleFont?(scale)
        case .resetSubtitleBubbleFont:
            onResetSubtitleBubbleFont?()
        case .setSubtitleBubbleFont(let scale):
            onSetSubtitleBubbleFont?(scale)
        }
    }

    func handleBookmark(_ action: VideoBookmarkAction) {
        switch action {
        case .add:
            onAddBookmark?()
        case .jumpTo(let entry):
            onJumpToBookmark(entry)
        case .remove(let entry):
            onRemoveBookmark(entry)
        }
    }

    func handleLinguistSettings(_ action: VideoLinguistSettingsAction) {
        switch action {
        case .setLookupLanguage(let language):
            onLookupLanguageChange(language)
        case .setLlmModel(let model):
            onLlmModelChange(model)
        }
    }

    func handleUI(_ action: VideoUIAction) {
        switch action {
        case .toggleHeaderCollapsed:
            onToggleHeaderCollapsed()
        case .selectSegment(let id):
            onSelectSegment?(id)
        case .userInteraction:
            onUserInteraction()
        }
    }
}
