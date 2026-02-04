import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Shared Types

#if os(iOS)
/// Sanitize text for dictionary lookup by removing enclosing quotes
enum TextLookupSanitizer {
    /// Quote characters to strip (using Unicode scalars to avoid parser issues)
    static let quoteChars: Set<Character> = [
        "\"", "'", "`",                             // ASCII quotes
        "\u{201C}", "\u{201D}",                     // Curly double quotes " "
        "\u{2018}", "\u{2019}",                     // Curly single quotes ' '
        "\u{00AB}", "\u{00BB}",                     // Guillemets « »
        "\u{201E}", "\u{201F}",                     // German quotes „ ‟
        "\u{300C}", "\u{300D}",                     // CJK brackets 「  」
        "\u{300E}", "\u{300F}"                      // CJK double brackets 『 』
    ]

    static func sanitize(_ text: String) -> String {
        var result = text.trimmingCharacters(in: .whitespacesAndNewlines)

        // Strip leading quotes
        while let first = result.first, quoteChars.contains(first) {
            result.removeFirst()
        }

        // Strip trailing quotes
        while let last = result.last, quoteChars.contains(last) {
            result.removeLast()
        }

        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

/// A text view that renders text with tappable words for Look Up / Copy
/// Preserves original text layout including newlines
struct TappableWordText: View {
    let text: String
    let font: Font
    let color: Color

    var body: some View {
        // Split by newlines first to preserve paragraph structure
        let lines = text.components(separatedBy: .newlines)

        VStack(alignment: .leading, spacing: 4) {
            ForEach(Array(lines.enumerated()), id: \.offset) { lineIndex, line in
                if line.isEmpty {
                    // Empty line = paragraph break, render minimal height spacer
                    Text(" ")
                        .font(font)
                        .foregroundStyle(.clear)
                } else {
                    // Parse line into word and non-word segments
                    let segments = parseSegments(line)

                    // Render segments in a wrapping layout
                    WrappingHStack(horizontalSpacing: 0, verticalSpacing: 2) {
                        ForEach(Array(segments.enumerated()), id: \.offset) { _, segment in
                            if segment.isWord {
                                Text(segment.text)
                                    .font(font)
                                    .foregroundStyle(color)
                                    .contextMenu {
                                        let sanitized = TextLookupSanitizer.sanitize(segment.text)
                                        Button("Look Up") {
                                            DictionaryLookupPresenter.show(term: sanitized)
                                        }
                                        Button("Copy") {
                                            UIPasteboard.general.string = sanitized
                                        }
                                    }
                            } else {
                                Text(segment.text)
                                    .font(font)
                                    .foregroundStyle(color)
                            }
                        }
                    }
                }
            }
        }
    }

    private struct TextSegment {
        let text: String
        let isWord: Bool
    }

    private func parseSegments(_ text: String) -> [TextSegment] {
        var segments: [TextSegment] = []
        var current = ""
        var isCurrentWord = false

        for char in text {
            let charIsWord = char.isLetter || char.isNumber ||
                             TextLookupSanitizer.quoteChars.contains(char)

            if current.isEmpty {
                current.append(char)
                isCurrentWord = charIsWord
            } else if charIsWord == isCurrentWord {
                current.append(char)
            } else {
                segments.append(TextSegment(text: current, isWord: isCurrentWord))
                current = String(char)
                isCurrentWord = charIsWord
            }
        }

        if !current.isEmpty {
            segments.append(TextSegment(text: current, isWord: isCurrentWord))
        }

        return segments
    }
}

/// A simple wrapping HStack that flows content like text
struct WrappingHStack: Layout {
    var horizontalSpacing: CGFloat = 0
    var verticalSpacing: CGFloat = 4

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = layout(proposal: proposal, subviews: subviews)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = layout(proposal: proposal, subviews: subviews)

        for (index, position) in result.positions.enumerated() {
            subviews[index].place(
                at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y),
                proposal: .unspecified
            )
        }
    }

    private func layout(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, positions: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var lineHeight: CGFloat = 0
        var maxX: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)

            // Wrap to next line if needed (but not for first item on line)
            if x > 0 && x + size.width > maxWidth {
                x = 0
                y += lineHeight + verticalSpacing
                lineHeight = 0
            }

            positions.append(CGPoint(x: x, y: y))
            x += size.width + horizontalSpacing
            maxX = max(maxX, x - horizontalSpacing)
            lineHeight = max(lineHeight, size.height)
        }

        return (CGSize(width: maxX, height: y + lineHeight), positions)
    }
}

// MARK: - Structured Linguist Content View

/// View that renders a parsed LinguistLookupResult with proper formatting
struct StructuredLinguistContentView: View {
    let result: LinguistLookupResult
    let font: Font
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Definition (always shown)
            TappableWordText(text: result.definition, font: font, color: color)

            // Part of speech & pronunciation
            if let pos = result.partOfSpeech, !pos.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text(pos)
                        .font(font)
                        .italic()
                        .foregroundStyle(color.opacity(0.8))
                    if let pron = result.pronunciation, !pron.isEmpty {
                        Text("[\(pron)]")
                            .font(font)
                            .foregroundStyle(color.opacity(0.7))
                    }
                }
            } else if let pron = result.pronunciation, !pron.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text("[\(pron)]")
                        .font(font)
                        .foregroundStyle(color.opacity(0.7))
                }
            }

            // Etymology
            if let etymology = result.etymology, !etymology.isEmpty {
                HStack(alignment: .top, spacing: 4) {
                    Text("⟶")
                        .font(font)
                        .foregroundStyle(color.opacity(0.5))
                    TappableWordText(text: etymology, font: font, color: color.opacity(0.85))
                }
            }

            // Example
            if let example = result.example, !example.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .top, spacing: 4) {
                        Text("„")
                            .font(font)
                            .foregroundStyle(color.opacity(0.5))
                        VStack(alignment: .leading, spacing: 2) {
                            TappableWordText(text: example, font: font.italic(), color: color.opacity(0.85))
                            if let translit = result.exampleTransliteration, !translit.isEmpty {
                                Text("(\(translit))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.6))
                            }
                        }
                    }
                    if let translation = result.exampleTranslation, !translation.isEmpty {
                        HStack(alignment: .top, spacing: 4) {
                            Text("→")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            TappableWordText(text: translation, font: font, color: color.opacity(0.75))
                        }
                    }
                }
            }

            // Idioms (for sentences)
            if let idioms = result.idioms, !idioms.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Idioms:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(idioms, id: \.self) { idiom in
                        HStack(alignment: .top, spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            TappableWordText(text: idiom, font: font, color: color.opacity(0.9))
                        }
                    }
                }
            }

            // Related languages
            if let related = result.relatedLanguages, !related.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Related:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(related) { lang in
                        HStack(spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(lang.language + ":")
                                .font(font)
                                .foregroundStyle(color.opacity(0.7))
                            Text(lang.word)
                                .font(font)
                                .foregroundStyle(color)
                                .contextMenu {
                                    let sanitized = TextLookupSanitizer.sanitize(lang.word)
                                    Button("Look Up") {
                                        DictionaryLookupPresenter.show(term: sanitized)
                                    }
                                    Button("Copy") {
                                        UIPasteboard.general.string = sanitized
                                    }
                                }
                            if let trans = lang.transliteration, !trans.isEmpty {
                                Text("(\(trans))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.7))
                            }
                        }
                    }
                }
            }
        }
    }
}
#endif

#if os(tvOS)
/// tvOS version of structured content view (no tappable words or context menus)
struct StructuredLinguistContentView: View {
    let result: LinguistLookupResult
    let font: Font
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Definition (always shown)
            Text(result.definition)
                .font(font)
                .foregroundStyle(color)

            // Part of speech & pronunciation
            if let pos = result.partOfSpeech, !pos.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text(pos)
                        .font(font)
                        .italic()
                        .foregroundStyle(color.opacity(0.8))
                    if let pron = result.pronunciation, !pron.isEmpty {
                        Text("[\(pron)]")
                            .font(font)
                            .foregroundStyle(color.opacity(0.7))
                    }
                }
            } else if let pron = result.pronunciation, !pron.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text("[\(pron)]")
                        .font(font)
                        .foregroundStyle(color.opacity(0.7))
                }
            }

            // Etymology
            if let etymology = result.etymology, !etymology.isEmpty {
                HStack(alignment: .top, spacing: 4) {
                    Text("⟶")
                        .font(font)
                        .foregroundStyle(color.opacity(0.5))
                    Text(etymology)
                        .font(font)
                        .foregroundStyle(color.opacity(0.85))
                }
            }

            // Example
            if let example = result.example, !example.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .top, spacing: 4) {
                        Text("„")
                            .font(font)
                            .foregroundStyle(color.opacity(0.5))
                        VStack(alignment: .leading, spacing: 2) {
                            Text(example)
                                .font(font.italic())
                                .foregroundStyle(color.opacity(0.85))
                            if let translit = result.exampleTransliteration, !translit.isEmpty {
                                Text("(\(translit))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.6))
                            }
                        }
                    }
                    if let translation = result.exampleTranslation, !translation.isEmpty {
                        HStack(alignment: .top, spacing: 4) {
                            Text("→")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(translation)
                                .font(font)
                                .foregroundStyle(color.opacity(0.75))
                        }
                    }
                }
            }

            // Idioms (for sentences)
            if let idioms = result.idioms, !idioms.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Idioms:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(idioms, id: \.self) { idiom in
                        HStack(alignment: .top, spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(idiom)
                                .font(font)
                                .foregroundStyle(color.opacity(0.9))
                        }
                    }
                }
            }

            // Related languages
            if let related = result.relatedLanguages, !related.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Related:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(related) { lang in
                        HStack(spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(lang.language + ":")
                                .font(font)
                                .foregroundStyle(color.opacity(0.7))
                            Text(lang.word)
                                .font(font)
                                .foregroundStyle(color)
                            if let trans = lang.transliteration, !trans.isEmpty {
                                Text("(\(trans))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.7))
                            }
                        }
                    }
                }
            }
        }
    }
}
#endif

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

// MARK: - Main View

struct LinguistBubbleView: View {
    let state: LinguistBubbleState
    let configuration: LinguistBubbleConfiguration
    let actions: LinguistBubbleActions

    #if os(tvOS)
    /// Whether focus is enabled for this bubble
    var isFocusEnabled: Bool = true
    #endif

    #if os(iOS)
    @State private var magnifyStartScale: CGFloat?
    @State private var measuredBubbleWidth: CGFloat = 0
    /// Optional keyboard navigator for iPad focus management
    @ObservedObject var keyboardNavigator: iOSBubbleKeyboardNavigator = iOSBubbleKeyboardNavigator()
    /// Active picker for keyboard-triggered selection (iOS)
    @State private var iOSActivePicker: iOSBubblePicker?

    private enum iOSBubblePicker: Hashable {
        case language
        case model
        case voice
    }

    private var isPhone: Bool {
        UIDevice.current.userInterfaceIdiom == .phone
    }

    /// When the bubble is narrow (e.g. horizontal split with reduced width),
    /// collapse model and voice pills to icon-only.
    private var useCompactPills: Bool {
        // Threshold: below 300pt, show icons only
        measuredBubbleWidth > 0 && measuredBubbleWidth < 300
    }
    #endif

    #if os(tvOS)
    @FocusState private var focusedControl: BubbleHeaderControl?
    @State private var activePicker: BubblePicker?
    @State private var autoScaleFontScale: CGFloat = 1.0
    @State private var measuredContentHeight: CGFloat = 0
    @State private var lastContentLength: Int = 0

    private enum BubbleHeaderControl: Hashable {
        case language
        case model
        case voice
        case playFromNarration
        case decreaseFont
        case increaseFont
        case pin
        case layout
        case close
    }

    private enum BubblePicker: Hashable {
        case language
        case model
        case voice
    }
    #endif

    var body: some View {
        ZStack {
            bubbleBody
            #if os(tvOS)
            if activePicker != nil {
                pickerOverlay
            }
            #elseif os(iOS)
            if iOSActivePicker != nil {
                iOSPickerOverlay
            }
            #endif
        }
        #if os(tvOS)
        // In split mode, fill available space to maintain constant size during loading
        .frame(maxWidth: configuration.isSplitMode ? .infinity : nil,
               maxHeight: configuration.isSplitMode ? .infinity : nil,
               alignment: .top)
        #endif
        #if os(iOS)
        .onChange(of: keyboardNavigator.activationTrigger) { _, _ in
            // When Enter is pressed on a picker control, open the corresponding picker
            guard let control = keyboardNavigator.focusedControl else { return }
            switch control {
            case .language:
                iOSActivePicker = .language
            case .voice:
                iOSActivePicker = .voice
            case .model:
                iOSActivePicker = .model
            case .close:
                // Close is handled directly in handleBubbleKeyboardActivate
                break
            }
        }
        #endif
    }

    // MARK: - Bubble Body

    private var bubbleBody: some View {
        VStack(alignment: .leading, spacing: 10) {
            headerRow

            bubbleContent
                #if os(tvOS)
                // Smooth content transitions for loading states
                .animation(.easeInOut(duration: 0.2), value: state.status.isLoading)
                #endif
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        #if os(iOS)
        .background(
            GeometryReader { widthProxy in
                Color.clear.onChange(of: widthProxy.size.width) { _, newWidth in
                    measuredBubbleWidth = newWidth
                }
                .onAppear { measuredBubbleWidth = widthProxy.size.width }
            }
        )
        #endif
        #if os(tvOS)
        // In split mode, fill available height to prevent size changes during loading
        .frame(maxHeight: configuration.isSplitMode ? .infinity : nil, alignment: .top)
        .background(
            GeometryReader { contentProxy in
                Color.clear.preference(
                    key: LinguistBubbleContentHeightKey.self,
                    value: contentProxy.size.height
                )
            }
        )
        #endif
        .background(bubbleBackground)
        .overlay(
            RoundedRectangle(cornerRadius: bubbleCornerRadius)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: bubbleCornerRadius))
        .frame(maxWidth: bubbleWidth, alignment: .leading)
        .frame(maxWidth: .infinity, alignment: .center)
        #if os(tvOS)
        .focusEffectDisabled()
        .focusSection()
        .onAppear {
            if isFocusEnabled && focusedControl == nil {
                focusedControl = .language
            }
            // Initialize auto-scale if content length is available
            if configuration.autoScaleFontToFit {
                lastContentLength = (state.answer ?? "").count
            }
        }
        .onChange(of: isFocusEnabled) { _, enabled in
            if enabled {
                if focusedControl == nil {
                    focusedControl = .language
                }
            } else if focusedControl != nil {
                focusedControl = nil
            }
        }
        .onChange(of: activePicker) { _, newValue in
            if newValue == nil && isFocusEnabled && focusedControl == nil {
                focusedControl = .language
            }
        }
        .onChange(of: focusedControl) { _, newValue in
            if newValue != nil {
                actions.onBubbleFocus?()
            }
        }
        .onPreferenceChange(LinguistBubbleContentHeightKey.self) { height in
            guard configuration.autoScaleFontToFit else { return }
            measuredContentHeight = height
            recalculateAutoScale()
        }
        .onChange(of: state.answer) { _, newAnswer in
            guard configuration.autoScaleFontToFit else { return }
            let newLength = (newAnswer ?? "").count
            // Only recalculate if content length changed significantly
            if abs(newLength - lastContentLength) > 10 {
                lastContentLength = newLength
                // Reset scale to base and let measurement trigger recalculation
                autoScaleFontScale = 1.0
            }
        }
        .onChange(of: configuration.availableHeight) { _, _ in
            guard configuration.autoScaleFontToFit else { return }
            recalculateAutoScale()
        }
        #endif
        #if os(iOS)
        .applyMagnifyGesture(
            enabled: actions.onMagnify != nil,
            fontScale: configuration.fontScale,
            magnifyStartScale: $magnifyStartScale,
            onMagnify: actions.onMagnify
        )
        .gesture(
            DragGesture(minimumDistance: 30, coordinateSpace: .local)
                .onEnded { value in
                    let horizontalAmount = value.translation.width
                    let verticalAmount = value.translation.height
                    // Only handle horizontal swipes (ignore vertical)
                    guard abs(horizontalAmount) > abs(verticalAmount) else { return }
                    if horizontalAmount < 0 {
                        // Swipe left -> next token
                        actions.onNextToken?()
                    } else {
                        // Swipe right -> previous token
                        actions.onPreviousToken?()
                    }
                }
        )
        #endif
    }

    #if os(tvOS)
    /// Recalculate auto-scale factor to fill available height
    private func recalculateAutoScale() {
        guard configuration.autoScaleFontToFit,
              let availableHeight = configuration.availableHeight,
              measuredContentHeight > 0 else { return }

        // Calculate the ratio needed to fill available space
        // Add some padding tolerance (20px) to prevent overflow
        let targetHeight = availableHeight - 20
        let currentHeight = measuredContentHeight

        // Calculate new scale factor
        let ratio = targetHeight / currentHeight
        let newScale = autoScaleFontScale * ratio

        // Clamp to configured bounds
        let clampedScale = max(
            configuration.minAutoScaleFontScale,
            min(configuration.maxAutoScaleFontScale, newScale)
        )

        // Only update if change is significant (> 2%)
        if abs(clampedScale - autoScaleFontScale) > 0.02 {
            autoScaleFontScale = clampedScale
        }
    }

    /// Layout toggle button for tvOS (overlay/split mode)
    @ViewBuilder
    private var tvLayoutToggleButton: some View {
        if let onToggle = actions.onToggleLayoutDirection {
            bubbleControlItem(control: .layout, isEnabled: true, action: onToggle) {
                Image(systemName: "rectangle.split.2x1")
            }
            .accessibilityLabel("Toggle layout")
        }
    }

    /// Pin toggle button for tvOS (keeps bubble visible during playback in split mode)
    @ViewBuilder
    private var tvPinToggleButton: some View {
        if let onToggle = actions.onTogglePin {
            bubbleControlItem(control: .pin, isEnabled: true, action: onToggle) {
                Image(systemName: configuration.isPinned ? "pin.fill" : "pin")
                    .foregroundStyle(configuration.isPinned ? .yellow : .white)
            }
            .accessibilityLabel(configuration.isPinned ? "Unpin bubble" : "Pin bubble")
        }
    }

    /// tvOS split mode header: controls on top row, query below
    private var tvSplitModeHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                lookupLanguageMenu
                voiceMenu
                modelMenu
                tvPlayFromNarrationButton
                fontSizeControls
                Spacer(minLength: 4)
                tvPinToggleButton
                tvLayoutToggleButton
                closeButton
            }
            HStack(spacing: 4) {
                tvLookupSourceIndicator
                Text(state.query)
                    .font(queryFont)
                    .foregroundStyle(bubbleTextColor)
                    .lineLimit(3)
                    .minimumScaleFactor(0.7)
            }
        }
    }

    /// tvOS overlay mode header: query and controls side by side
    private var tvOverlayModeHeader: some View {
        HStack(spacing: 8) {
            tvLookupSourceIndicator
            Text(state.query)
                .font(queryFont)
                .foregroundStyle(bubbleTextColor)
                .lineLimit(2)
                .minimumScaleFactor(0.8)
            Spacer(minLength: 8)
            lookupLanguageMenu
            voiceMenu
            modelMenu
            tvPlayFromNarrationButton
            fontSizeControls
            tvPinToggleButton
            tvLayoutToggleButton
            closeButton
        }
    }

    /// Play from narration button for tvOS - shows when cached audio reference is available
    @ViewBuilder
    private var tvPlayFromNarrationButton: some View {
        if let onPlay = actions.onPlayFromNarration, state.cachedAudioRef != nil {
            bubbleControlItem(control: .playFromNarration, isEnabled: true, action: onPlay) {
                Image(systemName: "waveform")
                    .foregroundStyle(.cyan)
            }
            .accessibilityLabel("Play from narration")
        }
    }

    /// Source indicator for tvOS showing if lookup was from cache or live
    @ViewBuilder
    private var tvLookupSourceIndicator: some View {
        if state.status == .ready, let source = state.lookupSource {
            Text(source == .cache ? "⚡" : "☁")
                .font(.system(size: 16))
                .foregroundStyle(source == .cache ? .yellow : .cyan)
                .accessibilityLabel(source == .cache ? "Cached lookup" : "Live lookup")
        }
    }
    #endif

    // MARK: - Header Row (Query + Controls)

    @ViewBuilder
    private var headerRow: some View {
        #if os(tvOS)
        if configuration.isSplitMode {
            // Split mode: controls on top, query below for more space
            tvSplitModeHeader
        } else {
            // Overlay mode: query and controls side by side
            tvOverlayModeHeader
        }
        #elseif os(iOS)
        iOSHeaderRow
        #else
        HStack(spacing: 6) {
            Text(state.query)
                .font(queryFont)
                .foregroundStyle(bubbleTextColor)
                .lineLimit(2)
                .minimumScaleFactor(0.8)
            Spacer(minLength: 6)
            lookupLanguageMenu
            voiceMenu
            modelMenu
            closeButton
        }
        #endif
    }

    #if os(iOS)
    @ViewBuilder
    private var iOSHeaderRow: some View {
        if isPhone {
            // iPhone: Vertical layout - controls on top left, query below
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    lookupLanguageMenu
                    voiceMenu
                    modelMenu
                    playFromNarrationButton
                    Spacer()
                    closeButton
                }
                HStack(spacing: 4) {
                    lookupSourceIndicator
                    Text(state.query)
                        .font(queryFont)
                        .foregroundStyle(bubbleTextColor)
                        .lineLimit(2)
                        .minimumScaleFactor(0.8)
                        .contextMenu {
                            let sanitized = TextLookupSanitizer.sanitize(state.query)
                            Button("Look Up") {
                                DictionaryLookupPresenter.show(term: sanitized)
                            }
                            Button("Copy") {
                                UIPasteboard.general.string = sanitized
                            }
                        }
                }
            }
        } else {
            // iPad: Vertical layout - controls on top, query below (same as iPhone)
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    lookupLanguageMenu
                    voiceMenu
                    modelMenu
                    playFromNarrationButton
                    Spacer()
                    pinToggleButton
                    layoutToggleButton
                    closeButton
                }
                HStack(spacing: 4) {
                    lookupSourceIndicator
                    Text(state.query)
                        .font(queryFont)
                        .foregroundStyle(bubbleTextColor)
                        .lineLimit(2)
                        .minimumScaleFactor(0.8)
                        .contextMenu {
                            let sanitized = TextLookupSanitizer.sanitize(state.query)
                            Button("Look Up") {
                                DictionaryLookupPresenter.show(term: sanitized)
                            }
                            Button("Copy") {
                                UIPasteboard.general.string = sanitized
                            }
                        }
                }
            }
        }
    }

    /// Play from narration button - shows when cached audio reference is available
    @ViewBuilder
    private var playFromNarrationButton: some View {
        if let onPlay = actions.onPlayFromNarration, state.cachedAudioRef != nil {
            Button(action: onPlay) {
                Image(systemName: "waveform")
                    .font(bubbleIconFont)
                    .foregroundStyle(.cyan)
                    .padding(bubbleControlPadding)
                    .background(.black.opacity(0.3), in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Play from narration")
        }
    }

    /// Source indicator showing if lookup was from cache or live
    @ViewBuilder
    private var lookupSourceIndicator: some View {
        if state.status == .ready, let source = state.lookupSource {
            Text(source == .cache ? "⚡" : "☁")
                .font(.system(size: configuration.uiScale * 10))
                .foregroundStyle(source == .cache ? .yellow : .cyan)
                .padding(.horizontal, 4)
                .padding(.vertical, 2)
                .background(.black.opacity(0.3), in: Capsule())
                .accessibilityLabel(source == .cache ? "Cached lookup" : "Live lookup")
        }
    }

    /// Pin toggle button for iPad (keeps bubble visible during playback)
    @ViewBuilder
    private var pinToggleButton: some View {
        if let onToggle = actions.onTogglePin {
            Button(action: onToggle) {
                Image(systemName: configuration.isPinned ? "pin.fill" : "pin")
                    .font(bubbleIconFont)
                    .foregroundStyle(configuration.isPinned ? .yellow : .white)
                    .padding(bubbleControlPadding)
                    .background(.black.opacity(0.3), in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(configuration.isPinned ? "Unpin bubble" : "Pin bubble")
        }
    }

    /// Layout toggle button for iPad (vertical/horizontal split)
    @ViewBuilder
    private var layoutToggleButton: some View {
        if let onToggle = actions.onToggleLayoutDirection {
            Button(action: onToggle) {
                Image(systemName: "rectangle.split.2x1")
                    .font(bubbleIconFont)
                    .foregroundStyle(.white)
                    .padding(bubbleControlPadding)
                    .background(.black.opacity(0.3), in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Toggle layout direction")
        }
    }
    #endif

    // MARK: - Language Menu

    @ViewBuilder
    private var lookupLanguageMenu: some View {
        let entry = LanguageFlagResolver.flagEntry(for: configuration.lookupLanguage)
        #if os(tvOS)
        bubbleControlItem(control: .language, isEnabled: true, action: {
            activePicker = .language
        }) {
            Text(entry.emoji)
        }
        .accessibilityLabel("Lookup language")
        #else
        Menu {
            ForEach(configuration.lookupLanguageOptions, id: \.self) { language in
                let option = LanguageFlagResolver.flagEntry(for: language)
                Button {
                    actions.onLookupLanguageChange(option.label)
                } label: {
                    if option.label == entry.label {
                        Label {
                            Text("\(option.emoji) \(option.label)")
                                .font(bubbleMenuFont)
                        } icon: {
                            Image(systemName: "checkmark")
                                .font(bubbleMenuFont)
                        }
                    } else {
                        Text("\(option.emoji) \(option.label)")
                            .font(bubbleMenuFont)
                    }
                }
            }
        } label: {
            HStack(spacing: 3) {
                Text(entry.emoji)
                    .font(bubbleSelectorIconFont)
                Text(entry.shortLabel.uppercased())
                    .font(bubbleSelectorTextFont)
            }
            .foregroundStyle(.white)
            .padding(.horizontal, bubbleSelectorPaddingH)
            .padding(.vertical, bubbleSelectorPaddingV)
            .background(.black.opacity(0.3), in: Capsule())
            .overlay(
                Capsule().stroke(
                    isControlKeyboardFocused(.language) ? keyboardFocusBorderColor : Color.white.opacity(0.35),
                    lineWidth: isControlKeyboardFocused(.language) ? keyboardFocusBorderWidth : 1
                )
            )
            .contentShape(Rectangle())
        }
        .fixedSize()
        .accessibilityLabel("Lookup language")
        #endif
    }

    // MARK: - Model Menu

    @ViewBuilder
    private var modelMenu: some View {
        #if os(tvOS)
        bubbleControlItem(control: .model, isEnabled: true, action: {
            activePicker = .model
        }) {
            Image(systemName: "brain")
        }
        .accessibilityLabel("Lookup model")
        #else
        Menu {
            ForEach(configuration.llmModelOptions, id: \.self) { model in
                Button {
                    actions.onLlmModelChange(model)
                } label: {
                    if model == configuration.llmModel {
                        Label(
                            title: {
                                Text(verbatim: model)
                                    .font(bubbleMenuFont)
                            },
                            icon: {
                                Image(systemName: "checkmark")
                                    .font(bubbleMenuFont)
                            }
                        )
                    } else {
                        Text(verbatim: model)
                            .font(bubbleMenuFont)
                    }
                }
            }
        } label: {
            HStack(spacing: 3) {
                Image(systemName: "brain")
                    .font(bubbleSelectorIconFont)
                if !useCompactPills {
                    Text(formatModelLabel(configuration.llmModel))
                        .font(bubbleSelectorTextFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                }
            }
            .foregroundStyle(.white)
            .padding(.horizontal, useCompactPills ? bubbleSelectorPaddingV : bubbleSelectorPaddingH)
            .padding(.vertical, bubbleSelectorPaddingV)
            .background(.black.opacity(0.3), in: Capsule())
            .overlay(
                Capsule().stroke(
                    isControlKeyboardFocused(.model) ? keyboardFocusBorderColor : Color.white.opacity(0.35),
                    lineWidth: isControlKeyboardFocused(.model) ? keyboardFocusBorderWidth : 1
                )
            )
            .contentShape(Rectangle())
        }
        .fixedSize()
        .accessibilityLabel("Lookup model")
        #endif
    }

    /// Format model name for compact display (e.g., "ollama_cloud:mistral-large-3:675b-cloud" → "mistral-large-3")
    private func formatModelLabel(_ model: String) -> String {
        // Split by colon: e.g., "ollama_cloud:mistral-large-3:675b-cloud"
        // parts[0] = provider, parts[1] = model name, parts[2] = size/variant
        let parts = model.split(separator: ":")
        if parts.count >= 3 {
            // Include model name and size: "mistral-large-3 (675b)"
            let modelName = String(parts[1])
            let sizeInfo = String(parts[2])
            // Extract just the size portion (e.g., "675b" from "675b-cloud")
            let sizePart = sizeInfo.split(separator: "-").first.map(String.init) ?? sizeInfo
            return "\(modelName) (\(sizePart))"
        } else if parts.count >= 2 {
            return String(parts[1])
        }
        // Fallback: take last path component or truncate
        if let lastPart = model.split(separator: "/").last {
            return String(lastPart)
        }
        return model
    }

    // MARK: - Voice Menu

    @ViewBuilder
    private var voiceMenu: some View {
        #if os(tvOS)
        if !configuration.ttsVoiceOptions.isEmpty {
            bubbleControlItem(control: .voice, isEnabled: true, action: {
                activePicker = .voice
            }) {
                Image(systemName: "speaker.wave.2.fill")
            }
            .accessibilityLabel("TTS voice")
        }
        #else
        if !configuration.ttsVoiceOptions.isEmpty {
            Menu {
                Button {
                    actions.onTtsVoiceChange?(nil)
                } label: {
                    if configuration.ttsVoice == nil {
                        Label("Auto", systemImage: "checkmark")
                            .font(bubbleMenuFont)
                    } else {
                        Text("Auto")
                            .font(bubbleMenuFont)
                    }
                }
                ForEach(configuration.ttsVoiceOptions, id: \.self) { voice in
                    Button {
                        actions.onTtsVoiceChange?(voice)
                    } label: {
                        if voice == configuration.ttsVoice {
                            Label(formatVoiceLabel(voice), systemImage: "checkmark")
                                .font(bubbleMenuFont)
                        } else {
                            Text(formatVoiceLabel(voice))
                                .font(bubbleMenuFont)
                        }
                    }
                }
            } label: {
                HStack(spacing: 3) {
                    Image(systemName: "speaker.wave.2.fill")
                        .font(bubbleSelectorIconFont)
                    if !useCompactPills, let voice = configuration.ttsVoice {
                        Text(formatVoiceLabel(voice))
                            .font(bubbleSelectorTextFont)
                            .lineLimit(1)
                            .minimumScaleFactor(0.7)
                    }
                }
                .foregroundStyle(.white)
                .padding(.horizontal, useCompactPills ? bubbleSelectorPaddingV : bubbleSelectorPaddingH)
                .padding(.vertical, bubbleSelectorPaddingV)
                .background(.black.opacity(0.3), in: Capsule())
                .overlay(
                    Capsule().stroke(
                        isControlKeyboardFocused(.voice) ? keyboardFocusBorderColor : Color.white.opacity(0.35),
                        lineWidth: isControlKeyboardFocused(.voice) ? keyboardFocusBorderWidth : 1
                    )
                )
                .contentShape(Rectangle())
            }
            .fixedSize()
            .accessibilityLabel("TTS voice")
        }
        #endif
    }

    /// Format voice name for display
    private func formatVoiceLabel(_ voice: String) -> String {
        // macOS voice format: "Name - locale"
        if voice.contains(" - ") {
            return String(voice.split(separator: " - ").first ?? Substring(voice))
        }
        // gTTS format: "gTTS-en"
        if voice.hasPrefix("gTTS-") {
            return "gTTS (\(voice.dropFirst(5)))"
        }
        // Piper format: "en_US-lessac-medium"
        let pattern = #"^[a-z]{2}_[A-Z]{2}-(.+)-(?:high|medium|low|x_low)$"#
        if let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive),
           let match = regex.firstMatch(in: voice, range: NSRange(voice.startIndex..., in: voice)),
           match.numberOfRanges > 1,
           let range = Range(match.range(at: 1), in: voice) {
            return String(voice[range])
        }
        return voice
    }

    // MARK: - Bubble Content

    @ViewBuilder
    private var bubbleContent: some View {
        switch state.status {
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .progressViewStyle(.circular)
                    .tint(.white)
                Text("Looking up...")
                    .font(bodyFont)
                    .foregroundStyle(.white.opacity(0.7))
            }
        case let .error(message):
            Text(message)
                .font(bodyFont)
                .foregroundStyle(.red)
        case .ready:
            if configuration.useCompactLayout {
                structuredOrFallbackContent
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ScrollView {
                    structuredOrFallbackContent
                        .frame(maxWidth: .infinity, alignment: .leading)
                        #if os(tvOS)
                        .padding(.bottom, 20) // Extra padding for scroll content
                        #endif
                }
                #if os(tvOS)
                .scrollIndicators(.visible)
                .scrollBounceBehavior(.basedOnSize)
                #endif
                .frame(maxHeight: bubbleMaxHeight)
            }
        }
    }

    #if os(iOS) || os(tvOS)
    /// Renders structured JSON content if available, otherwise falls back to plain text
    @ViewBuilder
    private var structuredOrFallbackContent: some View {
        if let parsed = state.parsedResult {
            StructuredLinguistContentView(
                result: parsed,
                font: bodyFont,
                color: bubbleTextColor
            )
        } else {
            // Fallback to plain text
            #if os(iOS)
            TappableWordText(
                text: state.answer ?? "",
                font: bodyFont,
                color: bubbleTextColor
            )
            #else
            Text(state.answer ?? "")
                .font(bodyFont)
                .foregroundStyle(bubbleTextColor)
            #endif
        }
    }
    #endif

    // MARK: - Font Size Controls (tvOS only, iOS uses pinch-to-resize)

    #if os(tvOS)
    private var fontSizeControls: some View {
        HStack(spacing: 6) {
            bubbleControlItem(control: .decreaseFont, isEnabled: configuration.canDecreaseFont, action: actions.onDecreaseFont) {
                Text("-")
            }
            bubbleControlItem(control: .increaseFont, isEnabled: configuration.canIncreaseFont, action: actions.onIncreaseFont) {
                Text("+")
            }
        }
    }
    #endif

    // MARK: - Close Button

    private var closeButton: some View {
        #if os(tvOS)
        bubbleControlItem(control: .close, isEnabled: true, action: actions.onClose) {
            Image(systemName: "xmark")
        }
        #else
        Button(action: actions.onClose) {
            Image(systemName: "xmark")
                .font(bubbleIconFont)
                .foregroundStyle(.white)
                .padding(bubbleControlPadding)
                .background(.black.opacity(0.3), in: Circle())
                .overlay(
                    Circle().stroke(
                        isControlKeyboardFocused(.close) ? keyboardFocusBorderColor : Color.clear,
                        lineWidth: isControlKeyboardFocused(.close) ? keyboardFocusBorderWidth : 0
                    )
                )
        }
        .buttonStyle(.plain)
        #endif
    }

    // MARK: - tvOS Picker

    #if os(tvOS)
    private struct BubblePickerOption: Identifiable {
        let id: String
        let title: String
        let value: String
        let isSelected: Bool
        let lineLimit: Int
    }

    private struct BubblePickerOptionRow: View {
        let option: BubblePickerOption

        var body: some View {
            HStack(spacing: 10) {
                Text(verbatim: option.title)
                    .lineLimit(option.lineLimit)
                Spacer(minLength: 12)
                if option.isSelected {
                    Image(systemName: "checkmark")
                        .foregroundStyle(.white)
                }
            }
            .font(.callout)
            .foregroundStyle(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.white.opacity(option.isSelected ? 0.25 : 0.12))
            )
        }
    }

    private struct BubblePickerOverlay: View {
        let title: String
        let options: [BubblePickerOption]
        let onSelectOption: (BubblePickerOption) -> Void
        let activePicker: Binding<BubblePicker?>
        @FocusState private var pickerFocus: String?

        var body: some View {
            ZStack {
                Color.black.opacity(0.55)
                    .ignoresSafeArea()
                VStack(spacing: 12) {
                    Text(title)
                        .font(.headline)
                        .foregroundStyle(.white)
                    ScrollView {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(options) { option in
                                Button {
                                    onSelectOption(option)
                                    activePicker.wrappedValue = nil
                                } label: {
                                    BubblePickerOptionRow(option: option)
                                }
                                .buttonStyle(.plain)
                                .focused($pickerFocus, equals: Optional(option.id))
                            }
                        }
                        .padding(.horizontal, 8)
                    }
                    Button("Close") {
                        activePicker.wrappedValue = nil
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(.black.opacity(0.4), in: Capsule())
                    .foregroundStyle(.white)
                }
                .padding(16)
                .frame(maxWidth: 520)
                .background(Color.black.opacity(0.85), in: RoundedRectangle(cornerRadius: 16))
            }
            .focusSection()
            .onExitCommand {
                activePicker.wrappedValue = nil
            }
            .onAppear {
                if pickerFocus == nil {
                    pickerFocus = options.first(where: { $0.isSelected })?.id ?? options.first?.id
                }
            }
        }
    }

    private func bubbleControlLabel(isFocused: Bool, @ViewBuilder content: () -> some View) -> some View {
        content()
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .foregroundStyle(.white)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isFocused ? Color.white.opacity(0.25) : Color.black.opacity(0.35))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isFocused ? Color.white.opacity(0.6) : .clear, lineWidth: 1)
            )
            .scaleEffect(isFocused ? 1.05 : 1.0)
            .animation(.easeInOut(duration: 0.15), value: isFocused)
    }

    private func bubbleControlItem(
        control: BubbleHeaderControl,
        isEnabled: Bool,
        action: @escaping () -> Void,
        @ViewBuilder label: () -> some View
    ) -> some View {
        let canFocus = isEnabled && activePicker == nil && isFocusEnabled
        return bubbleControlLabel(isFocused: focusedControl == control) {
            label()
        }
        .opacity(isEnabled ? 1 : 0.45)
        .contentShape(Rectangle())
        .focusable(canFocus)
        .focused($focusedControl, equals: control)
        .focusEffectDisabled()
        .onTapGesture {
            guard canFocus, focusedControl == control else { return }
            action()
        }
    }

    @ViewBuilder
    private var pickerOverlay: some View {
        if let activePicker {
            pickerOverlayContent(activePicker: activePicker)
        }
    }

    private func pickerOverlayContent(activePicker selection: BubblePicker) -> some View {
        let title: String
        let options: [BubblePickerOption]
        let onSelect: (BubblePickerOption) -> Void

        switch selection {
        case .language:
            title = "Lookup language"
            options = pickerOptions(for: .language)
            onSelect = { self.actions.onLookupLanguageChange($0.value) }
        case .model:
            title = "Lookup model"
            options = pickerOptions(for: .model)
            onSelect = { self.actions.onLlmModelChange($0.value) }
        case .voice:
            title = "TTS Voice"
            options = pickerOptions(for: .voice)
            onSelect = { self.actions.onTtsVoiceChange?($0.value.isEmpty ? nil : $0.value) }
        }

        return BubblePickerOverlay(
            title: title,
            options: options,
            onSelectOption: onSelect,
            activePicker: $activePicker
        )
    }

    private func pickerOptions(for picker: BubblePicker) -> [BubblePickerOption] {
        switch picker {
        case .language:
            return configuration.lookupLanguageOptions.map { option in
                let entry = LanguageFlagResolver.flagEntry(for: option)
                let label = entry.label
                return BubblePickerOption(
                    id: option,
                    title: "\(entry.emoji) \(label)",
                    value: label,
                    isSelected: label == configuration.lookupLanguage,
                    lineLimit: 1
                )
            }
        case .model:
            return configuration.llmModelOptions.map { model in
                BubblePickerOption(
                    id: model,
                    title: model,
                    value: model,
                    isSelected: model == configuration.llmModel,
                    lineLimit: 2
                )
            }
        case .voice:
            var options: [BubblePickerOption] = [
                BubblePickerOption(
                    id: "auto",
                    title: "Auto",
                    value: "",
                    isSelected: configuration.ttsVoice == nil,
                    lineLimit: 1
                )
            ]
            options += configuration.ttsVoiceOptions.map { voice in
                BubblePickerOption(
                    id: voice,
                    title: formatVoiceLabel(voice),
                    value: voice,
                    isSelected: voice == configuration.ttsVoice,
                    lineLimit: 1
                )
            }
            return options
        }
    }
    #endif

    // MARK: - iOS Picker Overlay

    #if os(iOS)
    @ViewBuilder
    private var iOSPickerOverlay: some View {
        if let picker = iOSActivePicker {
            iOSPickerSheet(for: picker)
        }
    }

    @ViewBuilder
    private func iOSPickerSheet(for picker: iOSBubblePicker) -> some View {
        let pickerData = iOSPickerData(for: picker)
        iOSPickerContent(
            title: pickerData.title,
            options: pickerData.options,
            onSelect: pickerData.onSelect,
            onDismiss: { iOSActivePicker = nil }
        )
    }

    private func iOSPickerData(for picker: iOSBubblePicker) -> (title: String, options: [iOSPickerOption], onSelect: (iOSPickerOption) -> Void) {
        switch picker {
        case .language:
            let langOptions = configuration.lookupLanguageOptions.map { option in
                let entry = LanguageFlagResolver.flagEntry(for: option)
                return iOSPickerOption(
                    id: option,
                    title: "\(entry.emoji) \(entry.label)",
                    value: entry.label,
                    isSelected: entry.label == configuration.lookupLanguage
                )
            }
            return (
                title: "Lookup Language",
                options: langOptions,
                onSelect: { self.actions.onLookupLanguageChange($0.value) }
            )
        case .model:
            let modelOptions = configuration.llmModelOptions.map { model in
                iOSPickerOption(
                    id: model,
                    title: formatModelLabel(model),
                    value: model,
                    isSelected: model == configuration.llmModel
                )
            }
            return (
                title: "Lookup Model",
                options: modelOptions,
                onSelect: { self.actions.onLlmModelChange($0.value) }
            )
        case .voice:
            var voiceOptions: [iOSPickerOption] = [
                iOSPickerOption(
                    id: "auto",
                    title: "Auto",
                    value: "",
                    isSelected: configuration.ttsVoice == nil
                )
            ]
            voiceOptions += configuration.ttsVoiceOptions.map { voice in
                iOSPickerOption(
                    id: voice,
                    title: formatVoiceLabel(voice),
                    value: voice,
                    isSelected: voice == configuration.ttsVoice
                )
            }
            return (
                title: "TTS Voice",
                options: voiceOptions,
                onSelect: { self.actions.onTtsVoiceChange?($0.value.isEmpty ? nil : $0.value) }
            )
        }
    }

    private struct iOSPickerOption: Identifiable {
        let id: String
        let title: String
        let value: String
        let isSelected: Bool
    }

    @ViewBuilder
    private func iOSPickerContent(
        title: String,
        options: [iOSPickerOption],
        onSelect: @escaping (iOSPickerOption) -> Void,
        onDismiss: @escaping () -> Void
    ) -> some View {
        Color.black.opacity(0.4)
            .ignoresSafeArea()
            .onTapGesture {
                onDismiss()
            }

        VStack(spacing: 0) {
            // Header
            HStack {
                Text(title)
                    .font(.headline)
                    .foregroundStyle(.white)
                Spacer()
                Button(action: onDismiss) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title2)
                        .foregroundStyle(.white.opacity(0.7))
                }
                .buttonStyle(.plain)
            }
            .padding()
            .background(Color.black.opacity(0.8))

            // Options list
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 2) {
                        ForEach(options) { option in
                            Button {
                                onSelect(option)
                                onDismiss()
                            } label: {
                                HStack {
                                    Text(option.title)
                                        .font(.body)
                                        .foregroundStyle(.white)
                                        .lineLimit(2)
                                    Spacer()
                                    if option.isSelected {
                                        Image(systemName: "checkmark")
                                            .foregroundStyle(.cyan)
                                    }
                                }
                                .padding(.horizontal, 16)
                                .padding(.vertical, 12)
                                .background(option.isSelected ? Color.white.opacity(0.15) : Color.clear)
                            }
                            .buttonStyle(.plain)
                            .id(option.id)
                        }
                    }
                }
                .onAppear {
                    // Scroll to selected option
                    if let selected = options.first(where: { $0.isSelected }) {
                        proxy.scrollTo(selected.id, anchor: .center)
                    }
                }
            }
        }
        .frame(maxWidth: 400)
        .frame(maxHeight: 500)
        .background(Color(white: 0.15))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.5), radius: 20)
        .transition(.scale.combined(with: .opacity))
    }
    #endif

    // MARK: - Styling

    private var queryFont: Font {
        #if os(tvOS)
        if configuration.autoScaleFontToFit {
            return scaledFont(textStyle: .title3, weight: .semibold, autoScale: autoScaleFontScale)
        }
        #endif
        return scaledFont(textStyle: .title3, weight: .semibold)
    }

    private var bodyFont: Font {
        #if os(tvOS)
        if configuration.autoScaleFontToFit {
            return scaledFont(textStyle: .callout, weight: .regular, autoScale: autoScaleFontScale)
        }
        #endif
        return scaledFont(textStyle: .callout, weight: .regular)
    }

    private var bubbleControlFont: Font {
        scaledUiFont(textStyle: .caption1, weight: .semibold)
    }

    private var bubbleModelFont: Font {
        // Use larger font on iPad for better readability
        let textStyle: UIFont.TextStyle = configuration.uiScale > 1.2 ? .callout : .caption2
        return scaledUiFont(textStyle: textStyle, weight: .regular)
    }

    private var bubbleMenuFont: Font {
        scaledUiFont(textStyle: .callout, weight: .regular)
    }

    private var bubbleIconFont: Font {
        scaledUiFont(textStyle: .caption1, weight: .semibold)
    }

    private var bubbleControlPadding: CGFloat {
        6 * configuration.uiScale
    }

    // MARK: - Selector Button Styling (LLM & Voice pickers - 20% smaller on iPad)

    /// Scale factor for selector buttons (80% on iPad, 100% elsewhere)
    private var selectorScale: CGFloat {
        configuration.uiScale > 1.2 ? 0.8 : 1.0
    }

    private var bubbleSelectorIconFont: Font {
        #if os(iOS)
        let baseSize = UIFont.preferredFont(forTextStyle: .caption2).pointSize
        return .system(size: baseSize * configuration.uiScale * selectorScale, weight: .semibold)
        #else
        return bubbleIconFont
        #endif
    }

    private var bubbleSelectorTextFont: Font {
        #if os(iOS)
        let baseSize = UIFont.preferredFont(forTextStyle: .caption2).pointSize
        return .system(size: baseSize * configuration.uiScale * selectorScale, weight: .regular)
        #else
        return bubbleModelFont
        #endif
    }

    private var bubbleSelectorPaddingH: CGFloat {
        5 * configuration.uiScale * selectorScale
    }

    private var bubbleSelectorPaddingV: CGFloat {
        4 * configuration.uiScale * selectorScale
    }

    #if os(iOS)
    /// Check if a specific control is keyboard-focused
    private func isControlKeyboardFocused(_ control: iOSBubbleKeyboardControl) -> Bool {
        keyboardNavigator.isKeyboardFocusActive && keyboardNavigator.focusedControl == control
    }

    /// Border color for keyboard focus highlight
    private var keyboardFocusBorderColor: Color {
        Color.cyan.opacity(0.9)
    }

    /// Border width for keyboard focus highlight
    private var keyboardFocusBorderWidth: CGFloat {
        2 * selectorScale
    }
    #endif

    private func scaledFont(textStyle: UIFont.TextStyle, weight: Font.Weight, autoScale: CGFloat = 1.0) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * configuration.fontScale * autoScale, weight: weight)
        #else
        return .system(size: 16 * configuration.fontScale * autoScale, weight: weight)
        #endif
    }

    private func scaledUiFont(textStyle: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * configuration.uiScale, weight: weight)
        #else
        return .system(size: 16 * configuration.uiScale, weight: weight)
        #endif
    }

    private var bubbleBackground: Color {
        Color.black.opacity(0.75)
    }

    /// Text color for bubble content - always white since background is dark
    private var bubbleTextColor: Color {
        .white
    }

    private var bubbleCornerRadius: CGFloat {
        if configuration.edgeToEdgeStyle {
            return 0
        }
        #if os(tvOS)
        return 18
        #else
        return 14
        #endif
    }

    private var bubbleMaxHeight: CGFloat {
        // Account for header row (~50pt on tvOS) + padding (24pt total) + spacing (10pt)
        // when calculating available height for the scroll content
        let headerAndPaddingHeight: CGFloat = {
            #if os(tvOS)
            return 100 // header row height (~60) + padding (12*2) + spacing (10) + margin
            #else
            return 60 // smaller on iOS
            #endif
        }()

        #if os(tvOS)
        // On tvOS, use availableHeight from configuration if provided
        if let availableHeight = configuration.availableHeight {
            return max(availableHeight - headerAndPaddingHeight, 100)
        }
        return UIScreen.main.bounds.height * 0.7 // Allow larger bubbles on tvOS
        #else
        if let maxHeight = configuration.maxContentHeight {
            // Subtract header/padding space from total to get scroll content height
            return max(maxHeight - headerAndPaddingHeight, 80)
        }
        return 180
        #endif
    }

    private var bubbleWidth: CGFloat {
        #if os(iOS) || os(tvOS)
        #if os(tvOS)
        return UIScreen.main.bounds.width * 0.95
        #else
        return UIScreen.main.bounds.width * configuration.widthMultiplier
        #endif
        #else
        return 420
        #endif
    }
}

// MARK: - iOS Magnify Gesture Extension

#if os(iOS)
private extension View {
    @ViewBuilder
    func applyMagnifyGesture(
        enabled: Bool,
        fontScale: CGFloat,
        magnifyStartScale: Binding<CGFloat?>,
        onMagnify: ((CGFloat) -> Void)?
    ) -> some View {
        if enabled, let onMagnify {
            self.simultaneousGesture(
                MagnificationGesture()
                    .onChanged { value in
                        if magnifyStartScale.wrappedValue == nil {
                            magnifyStartScale.wrappedValue = fontScale
                        }
                        let startScale = magnifyStartScale.wrappedValue ?? fontScale
                        onMagnify(startScale * value)
                    }
                    .onEnded { _ in
                        magnifyStartScale.wrappedValue = nil
                    },
                including: .gesture
            )
        } else {
            self
        }
    }
}
#endif

// MARK: - Type Aliases for Backwards Compatibility

/// Backwards compatibility alias for MyLinguistBubbleStatus
typealias MyLinguistBubbleStatus = LinguistBubbleStatus

/// Backwards compatibility alias for VideoLinguistBubbleStatus
typealias VideoLinguistBubbleStatus = LinguistBubbleStatus

/// Backwards compatibility state for Interactive Player
struct MyLinguistBubbleState: Equatable {
    let query: String
    let status: LinguistBubbleStatus
    let answer: String?
    let model: String?
    var lookupSource: LinguistLookupSource? = nil
    /// Audio reference from lookup cache - allows playing word from narration audio
    var cachedAudioRef: LookupCacheAudioRef? = nil

    var asLinguistBubbleState: LinguistBubbleState {
        LinguistBubbleState(query: query, status: status, answer: answer, model: model, lookupSource: lookupSource, cachedAudioRef: cachedAudioRef)
    }
}

/// Backwards compatibility state for Video Player
struct VideoLinguistBubbleState: Equatable {
    let query: String
    let status: LinguistBubbleStatus
    let answer: String?
    let model: String?
    var lookupSource: LinguistLookupSource? = nil

    var asLinguistBubbleState: LinguistBubbleState {
        LinguistBubbleState(query: query, status: status, answer: answer, model: model, lookupSource: lookupSource)
    }
}

// MARK: - Backwards Compatible View Wrappers

/// Wrapper for Video Player that maintains the original API
struct VideoLinguistBubbleView: View {
    let bubble: VideoLinguistBubbleState
    let fontScale: CGFloat
    let canIncreaseFont: Bool
    let canDecreaseFont: Bool
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let onLookupLanguageChange: (String) -> Void
    let llmModel: String
    let llmModelOptions: [String]
    let onLlmModelChange: (String) -> Void
    var ttsVoice: String? = nil
    var ttsVoiceOptions: [String] = []
    var onTtsVoiceChange: ((String?) -> Void)? = nil
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onResetFont: (() -> Void)?
    let onClose: () -> Void
    let onMagnify: ((CGFloat) -> Void)?

    #if os(tvOS)
    let isFocusEnabled: Bool
    let onBubbleFocus: (() -> Void)?

    init(
        bubble: VideoLinguistBubbleState,
        fontScale: CGFloat,
        canIncreaseFont: Bool,
        canDecreaseFont: Bool,
        lookupLanguage: String,
        isFocusEnabled: Bool,
        onBubbleFocus: (() -> Void)?,
        lookupLanguageOptions: [String],
        onLookupLanguageChange: @escaping (String) -> Void,
        llmModel: String,
        llmModelOptions: [String],
        onLlmModelChange: @escaping (String) -> Void,
        ttsVoice: String? = nil,
        ttsVoiceOptions: [String] = [],
        onTtsVoiceChange: ((String?) -> Void)? = nil,
        onIncreaseFont: @escaping () -> Void,
        onDecreaseFont: @escaping () -> Void,
        onResetFont: (() -> Void)?,
        onClose: @escaping () -> Void,
        onMagnify: ((CGFloat) -> Void)?
    ) {
        self.bubble = bubble
        self.fontScale = fontScale
        self.canIncreaseFont = canIncreaseFont
        self.canDecreaseFont = canDecreaseFont
        self.lookupLanguage = lookupLanguage
        self.isFocusEnabled = isFocusEnabled
        self.onBubbleFocus = onBubbleFocus
        self.lookupLanguageOptions = lookupLanguageOptions
        self.onLookupLanguageChange = onLookupLanguageChange
        self.llmModel = llmModel
        self.llmModelOptions = llmModelOptions
        self.onLlmModelChange = onLlmModelChange
        self.ttsVoice = ttsVoice
        self.ttsVoiceOptions = ttsVoiceOptions
        self.onTtsVoiceChange = onTtsVoiceChange
        self.onIncreaseFont = onIncreaseFont
        self.onDecreaseFont = onDecreaseFont
        self.onResetFont = onResetFont
        self.onClose = onClose
        self.onMagnify = onMagnify
    }
    #endif

    private var bubbleConfiguration: LinguistBubbleConfiguration {
        var config = LinguistBubbleConfiguration(
            fontScale: fontScale,
            canIncreaseFont: canIncreaseFont,
            canDecreaseFont: canDecreaseFont,
            lookupLanguage: lookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            llmModel: llmModel,
            llmModelOptions: llmModelOptions
        )
        config.ttsVoice = ttsVoice
        config.ttsVoiceOptions = ttsVoiceOptions
        #if os(iOS)
        if UIDevice.current.userInterfaceIdiom == .pad {
            config.uiScale = 1.5
        }
        #endif
        return config
    }

    private var bubbleActions: LinguistBubbleActions {
        LinguistBubbleActions(
            onLookupLanguageChange: onLookupLanguageChange,
            onLlmModelChange: onLlmModelChange,
            onIncreaseFont: onIncreaseFont,
            onDecreaseFont: onDecreaseFont,
            onClose: onClose,
            onTtsVoiceChange: onTtsVoiceChange,
            onResetFont: onResetFont,
            onMagnify: onMagnify,
            onBubbleFocus: {
                #if os(tvOS)
                onBubbleFocus?()
                #endif
            }
        )
    }

    var body: some View {
        #if os(tvOS)
        LinguistBubbleView(
            state: bubble.asLinguistBubbleState,
            configuration: bubbleConfiguration,
            actions: bubbleActions,
            isFocusEnabled: isFocusEnabled
        )
        #else
        LinguistBubbleView(
            state: bubble.asLinguistBubbleState,
            configuration: bubbleConfiguration,
            actions: bubbleActions
        )
        #endif
    }
}
