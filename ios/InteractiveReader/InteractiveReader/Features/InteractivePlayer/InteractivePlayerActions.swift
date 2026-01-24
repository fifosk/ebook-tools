import Foundation

// MARK: - Interactive Playback Actions

/// Actions for controlling interactive player playback
enum InteractivePlaybackAction {
    case togglePlayback
    case skipSentence(Int)
}

// MARK: - Transcript Actions

/// Actions for transcript navigation and interaction
enum TranscriptAction {
    case toggleTrack(TextPlayerVariantKind)
    case navigateTrack(Int)
    case lookup
    case lookupToken(sentenceIndex: Int, trackKind: TextPlayerVariantKind, tokenIndex: Int, text: String)
    case seekToken(sentenceIndex: Int, displayIndex: Int?, trackKind: TextPlayerVariantKind, tokenIndex: Int, startTime: Double?)
    case updateSelectionRange(TextPlayerWordSelectionRange, TextPlayerWordSelection)
    case closeBubble
}

// MARK: - Menu Actions

/// Actions for menu visibility
enum TranscriptMenuAction {
    case show
    case hide
}

// MARK: - Interactive Font Actions

/// Actions for adjusting font sizes in interactive player
enum InteractiveFontAction {
    case increaseLinguistFont
    case decreaseLinguistFont
    case setTrackFontScale(CGFloat)
    case setLinguistFontScale(CGFloat)
}

// MARK: - Action Handler Struct

/// Consolidated actions for InteractiveTranscriptView
struct InteractiveTranscriptActions {
    // Playback closures
    var onTogglePlayback: () -> Void = {}
    var onSkipSentence: (Int) -> Void = { _ in }

    // Transcript closures
    var onToggleTrack: (TextPlayerVariantKind) -> Void = { _ in }
    var onNavigateTrack: (Int) -> Void = { _ in }
    var onLookup: () -> Void = {}
    var onLookupToken: (Int, TextPlayerVariantKind, Int, String) -> Void = { _, _, _, _ in }
    var onSeekToken: (Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void = { _, _, _, _, _ in }
    var onUpdateSelectionRange: (TextPlayerWordSelectionRange, TextPlayerWordSelection) -> Void = { _, _ in }
    var onCloseBubble: () -> Void = {}

    // Menu closures
    var onShowMenu: () -> Void = {}
    var onHideMenu: () -> Void = {}

    // Font closures
    var onIncreaseLinguistFont: () -> Void = {}
    var onDecreaseLinguistFont: () -> Void = {}
    var onSetTrackFontScale: (CGFloat) -> Void = { _ in }
    var onSetLinguistFontScale: (CGFloat) -> Void = { _ in }

    // Linguist settings closures
    var onLookupLanguageChange: (String) -> Void = { _ in }
    var onLlmModelChange: (String) -> Void = { _ in }

    // MARK: - Action Handlers

    func handlePlayback(_ action: InteractivePlaybackAction) {
        switch action {
        case .togglePlayback:
            onTogglePlayback()
        case .skipSentence(let delta):
            onSkipSentence(delta)
        }
    }

    func handleTranscript(_ action: TranscriptAction) {
        switch action {
        case .toggleTrack(let kind):
            onToggleTrack(kind)
        case .navigateTrack(let delta):
            onNavigateTrack(delta)
        case .lookup:
            onLookup()
        case .lookupToken(let sentenceIndex, let trackKind, let tokenIndex, let text):
            onLookupToken(sentenceIndex, trackKind, tokenIndex, text)
        case .seekToken(let sentenceIndex, let displayIndex, let trackKind, let tokenIndex, let startTime):
            onSeekToken(sentenceIndex, displayIndex, trackKind, tokenIndex, startTime)
        case .updateSelectionRange(let range, let selection):
            onUpdateSelectionRange(range, selection)
        case .closeBubble:
            onCloseBubble()
        }
    }

    func handleMenu(_ action: TranscriptMenuAction) {
        switch action {
        case .show:
            onShowMenu()
        case .hide:
            onHideMenu()
        }
    }

    func handleFont(_ action: InteractiveFontAction) {
        switch action {
        case .increaseLinguistFont:
            onIncreaseLinguistFont()
        case .decreaseLinguistFont:
            onDecreaseLinguistFont()
        case .setTrackFontScale(let scale):
            onSetTrackFontScale(scale)
        case .setLinguistFontScale(let scale):
            onSetLinguistFontScale(scale)
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
}

// MARK: - Text Player Token Actions

/// Actions for TextPlayerFrame and TextPlayerSentenceView
enum TextPlayerTokenAction {
    case lookup(sentenceIndex: Int, trackKind: TextPlayerVariantKind, tokenIndex: Int, text: String)
    case seek(sentenceIndex: Int, displayIndex: Int?, trackKind: TextPlayerVariantKind, tokenIndex: Int, startTime: Double?)
    case toggleTrack(TextPlayerVariantKind)
    case tokenFramesChange([TextPlayerTokenFrame])
    case tapExclusionFramesChange([CGRect])
}

/// Consolidated actions for TextPlayerFrame
struct TextPlayerFrameActions {
    var onTokenLookup: ((Int, TextPlayerVariantKind, Int, String) -> Void)?
    var onTokenSeek: ((Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void)?
    var onToggleTrack: ((TextPlayerVariantKind) -> Void)?
    var onTokenFramesChange: (([TextPlayerTokenFrame]) -> Void)?
    var onTapExclusionFramesChange: (([CGRect]) -> Void)?

    func handle(_ action: TextPlayerTokenAction) {
        switch action {
        case .lookup(let sentenceIndex, let trackKind, let tokenIndex, let text):
            onTokenLookup?(sentenceIndex, trackKind, tokenIndex, text)
        case .seek(let sentenceIndex, let displayIndex, let trackKind, let tokenIndex, let startTime):
            onTokenSeek?(sentenceIndex, displayIndex, trackKind, tokenIndex, startTime)
        case .toggleTrack(let kind):
            onToggleTrack?(kind)
        case .tokenFramesChange(let frames):
            onTokenFramesChange?(frames)
        case .tapExclusionFramesChange(let frames):
            onTapExclusionFramesChange?(frames)
        }
    }
}
