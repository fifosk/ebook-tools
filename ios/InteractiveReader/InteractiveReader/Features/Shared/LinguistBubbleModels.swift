import SwiftUI

/// Preference key for measuring bubble content height (tvOS auto-scaling)
struct LinguistBubbleContentHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

/// Status of a linguist lookup operation
enum LinguistBubbleStatus: Equatable {
    case loading
    case ready
    case error(String)

    var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }
}

/// Source of a lookup result (cache or live LLM call)
enum LinguistLookupSource: String, Equatable {
    case cache
    case live
}

/// State for a linguist bubble - represents the current lookup
struct LinguistBubbleState: Equatable {
    let query: String
    let status: LinguistBubbleStatus
    let answer: String?
    let model: String?
    let lookupSource: LinguistLookupSource?
    /// Audio reference from lookup cache - allows playing word from narration audio
    let cachedAudioRef: LookupCacheAudioRef?

    init(query: String, status: LinguistBubbleStatus, answer: String?, model: String?, lookupSource: LinguistLookupSource? = nil, cachedAudioRef: LookupCacheAudioRef? = nil) {
        self.query = query
        self.status = status
        self.answer = answer
        self.model = model
        self.lookupSource = lookupSource
        self.cachedAudioRef = cachedAudioRef
    }

    /// Parsed structured result (if JSON parsing succeeded)
    var parsedResult: LinguistLookupResult? {
        guard let answer else { return nil }
        return LinguistLookupResult.parse(from: answer)
    }
}

/// Configuration for LinguistBubbleView appearance and behavior
struct LinguistBubbleConfiguration {
    /// Font scale multiplier
    let fontScale: CGFloat

    /// Whether font can be increased
    let canIncreaseFont: Bool

    /// Whether font can be decreased
    let canDecreaseFont: Bool

    /// Current lookup language
    let lookupLanguage: String

    /// Available language options
    let lookupLanguageOptions: [String]

    /// Current LLM model
    let llmModel: String

    /// Available LLM model options
    let llmModelOptions: [String]

    /// Current TTS voice (nil means auto)
    var ttsVoice: String? = nil

    /// Available TTS voice options
    var ttsVoiceOptions: [String] = []

    /// UI scale factor (e.g., 2.0 for iPad)
    var uiScale: CGFloat = 1.0

    /// Whether to use compact layout (no ScrollView) for answer
    var useCompactLayout: Bool = false

    /// Maximum height for answer content
    var maxContentHeight: CGFloat? = nil

    /// Width multiplier for bubble (relative to screen width)
    var widthMultiplier: CGFloat = 0.66

    /// Whether to hide the "MyLinguist" title in header
    var hideTitle: Bool = false

    /// Whether to use edge-to-edge styling (no corner radius, no side margins)
    var edgeToEdgeStyle: Bool = false

    /// (tvOS) Whether to auto-scale font to fill available space
    var autoScaleFontToFit: Bool = false

    /// (tvOS) Available height for the entire bubble (used for auto-scaling)
    var availableHeight: CGFloat? = nil

    /// (tvOS) Minimum font scale for auto-scaling
    var minAutoScaleFontScale: CGFloat = 0.7

    /// (tvOS) Maximum font scale for auto-scaling
    var maxAutoScaleFontScale: CGFloat = 1.5

    /// (tvOS) Whether the bubble is displayed in split mode (side-by-side with tracks)
    var isSplitMode: Bool = false

    /// (iPad) Whether the bubble is pinned (stays visible during playback)
    var isPinned: Bool = false
}

/// Actions that can be performed on the linguist bubble
struct LinguistBubbleActions {
    let onLookupLanguageChange: (String) -> Void
    let onLlmModelChange: (String) -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onClose: () -> Void

    /// Optional TTS voice change handler
    var onTtsVoiceChange: ((String?) -> Void)? = nil

    /// Optional reset font action (shown as separate button if provided)
    var onResetFont: (() -> Void)? = nil

    /// Optional magnify gesture handler (iOS only)
    var onMagnify: ((CGFloat) -> Void)? = nil

    /// Optional callback when bubble gains focus (tvOS only)
    var onBubbleFocus: (() -> Void)? = nil

    /// Optional callback when keyboard navigation leaves bubble focus (iOS only)
    var onExitBubbleFocus: (() -> Void)? = nil

    /// Optional callback to navigate to previous token (iOS swipe right)
    var onPreviousToken: (() -> Void)? = nil

    /// Optional callback to navigate to next token (iOS swipe left)
    var onNextToken: (() -> Void)? = nil

    /// Optional callback to toggle layout direction (iPad only)
    var onToggleLayoutDirection: (() -> Void)? = nil

    /// Optional callback to toggle pin state (iPad only)
    var onTogglePin: (() -> Void)? = nil

    /// Optional callback to play word from narration audio (seeks audio player to cached timing)
    var onPlayFromNarration: (() -> Void)? = nil
}

// MARK: - iPad Split Layout

/// Layout direction for iPad split view
enum iPadBubbleSplitDirection {
    case vertical   // tracks on top, bubble below (default)
    case horizontal // tracks on right, bubble on left (like iPhone landscape)
}

// MARK: - iOS Keyboard Navigation

/// Controls that can be focused via keyboard navigation on iPad
enum iOSBubbleKeyboardControl: Int, CaseIterable {
    case language
    case voice
    case model
    case close

    var next: iOSBubbleKeyboardControl {
        let all = Self.allCases
        guard let idx = all.firstIndex(of: self) else { return self }
        let nextIdx = (idx + 1) % all.count
        return all[nextIdx]
    }

    var previous: iOSBubbleKeyboardControl {
        let all = Self.allCases
        guard let idx = all.firstIndex(of: self) else { return self }
        let prevIdx = (idx - 1 + all.count) % all.count
        return all[prevIdx]
    }
}

/// Coordinator for iPad keyboard navigation in bubble
final class iOSBubbleKeyboardNavigator: ObservableObject {
    @Published var focusedControl: iOSBubbleKeyboardControl?
    @Published var isKeyboardFocusActive: Bool = false
    /// Incremented when Enter is pressed to trigger activation
    @Published var activationTrigger: Int = 0

    func enterFocus() {
        isKeyboardFocusActive = true
        focusedControl = .language
    }

    func exitFocus() {
        isKeyboardFocusActive = false
        focusedControl = nil
    }

    func navigateLeft() {
        guard isKeyboardFocusActive else { return }
        focusedControl = focusedControl?.previous ?? .language
    }

    func navigateRight() {
        guard isKeyboardFocusActive else { return }
        focusedControl = focusedControl?.next ?? .language
    }

    /// Triggers activation of the currently focused control
    func activateCurrentControl() {
        guard isKeyboardFocusActive, focusedControl != nil else { return }
        activationTrigger += 1
    }
}

// MARK: - tvOS Focus Protocol

/// Protocol for external focus management on tvOS
protocol LinguistBubbleFocusDelegate {
    func bubbleDidGainFocus()
}
