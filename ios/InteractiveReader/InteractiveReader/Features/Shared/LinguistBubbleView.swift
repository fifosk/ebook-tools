import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Shared Types

/// Status of a linguist lookup operation
enum LinguistBubbleStatus: Equatable {
    case loading
    case ready
    case error(String)
}

/// State for a linguist bubble - represents the current lookup
struct LinguistBubbleState: Equatable {
    let query: String
    let status: LinguistBubbleStatus
    let answer: String?
    let model: String?
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
}

/// Actions that can be performed on the linguist bubble
struct LinguistBubbleActions {
    let onLookupLanguageChange: (String) -> Void
    let onLlmModelChange: (String) -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onClose: () -> Void

    /// Optional reset font action (shown as separate button if provided)
    var onResetFont: (() -> Void)? = nil

    /// Optional magnify gesture handler (iOS only)
    var onMagnify: ((CGFloat) -> Void)? = nil

    /// Optional callback when bubble gains focus (tvOS only)
    var onBubbleFocus: (() -> Void)? = nil
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
    #endif

    #if os(tvOS)
    @FocusState private var focusedControl: BubbleHeaderControl?
    @State private var activePicker: BubblePicker?

    private enum BubbleHeaderControl: Hashable {
        case language
        case model
        case decreaseFont
        case increaseFont
        case close
    }

    private enum BubblePicker: Hashable {
        case language
        case model
    }
    #endif

    var body: some View {
        ZStack {
            bubbleBody
            #if os(tvOS)
            if activePicker != nil {
                pickerOverlay
            }
            #endif
        }
    }

    // MARK: - Bubble Body

    private var bubbleBody: some View {
        VStack(alignment: .leading, spacing: 10) {
            headerControls

            Text(state.query)
                .font(queryFont)
                .lineLimit(2)
                .minimumScaleFactor(0.8)
                #if os(iOS)
                .textSelection(.enabled)
                #endif

            bubbleContent
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
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
        #endif
        #if os(iOS)
        .applyMagnifyGesture(
            enabled: actions.onMagnify != nil,
            fontScale: configuration.fontScale,
            magnifyStartScale: $magnifyStartScale,
            onMagnify: actions.onMagnify
        )
        #endif
    }

    // MARK: - Header Controls

    private var headerControls: some View {
        #if os(tvOS)
        HStack(spacing: 8) {
            lookupLanguageMenu
            modelMenu
            fontSizeControls
            closeButton
        }
        #else
        HStack(spacing: 8) {
            if !configuration.hideTitle {
                Text("MyLinguist")
                    .font(.headline)
            }
            Spacer(minLength: 8)
            lookupLanguageMenu
            modelMenu
            fontSizeControls
            if let onResetFont = actions.onResetFont {
                Button(action: onResetFont) {
                    Image(systemName: "arrow.counterclockwise")
                        .font(bubbleControlFont)
                        .padding(bubbleControlPadding)
                        .background(.black.opacity(0.3), in: Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Reset size")
            }
            closeButton
        }
        #endif
    }

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
            Text(entry.emoji)
                .font(bubbleIconFont)
                .padding(bubbleControlPadding)
                .background(.black.opacity(0.3), in: Capsule())
        }
        .buttonStyle(.plain)
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
            Text(verbatim: configuration.llmModel)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
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
            Text(verbatim: configuration.llmModel)
                .font(bubbleModelFont)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .padding(.horizontal, bubbleControlPadding * 1.4)
                .padding(.vertical, bubbleControlPadding * 0.7)
                .background(.black.opacity(0.3), in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Lookup model")
        #endif
    }

    // MARK: - Bubble Content

    @ViewBuilder
    private var bubbleContent: some View {
        switch state.status {
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .progressViewStyle(.circular)
                Text("Looking up...")
                    .font(bodyFont)
                    .foregroundStyle(.secondary)
            }
        case let .error(message):
            Text(message)
                .font(bodyFont)
                .foregroundStyle(.red)
        case .ready:
            if configuration.useCompactLayout {
                Text(state.answer ?? "")
                    .font(bodyFont)
                    .foregroundStyle(.primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    #if os(iOS)
                    .textSelection(.enabled)
                    #endif
            } else {
                ScrollView {
                    Text(state.answer ?? "")
                        .font(bodyFont)
                        .foregroundStyle(.primary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        #if os(iOS)
                        .textSelection(.enabled)
                        #endif
                }
                .frame(maxHeight: bubbleMaxHeight)
            }
        }
    }

    // MARK: - Font Size Controls

    private var fontSizeControls: some View {
        #if os(tvOS)
        HStack(spacing: 6) {
            bubbleControlItem(control: .decreaseFont, isEnabled: configuration.canDecreaseFont, action: actions.onDecreaseFont) {
                Text("A-")
            }
            bubbleControlItem(control: .increaseFont, isEnabled: configuration.canIncreaseFont, action: actions.onIncreaseFont) {
                Text("A+")
            }
        }
        #else
        HStack(spacing: 4) {
            Button(action: actions.onDecreaseFont) {
                Text("A-")
                    .font(bubbleControlFont)
                    .padding(.horizontal, bubbleControlPadding)
                    .padding(.vertical, bubbleControlPadding * 0.7)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!configuration.canDecreaseFont)
            Button(action: actions.onIncreaseFont) {
                Text("A+")
                    .font(bubbleControlFont)
                    .padding(.horizontal, bubbleControlPadding)
                    .padding(.vertical, bubbleControlPadding * 0.7)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!configuration.canIncreaseFont)
        }
        #endif
    }

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
                .padding(bubbleControlPadding)
                .background(.black.opacity(0.3), in: Circle())
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
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .foregroundStyle(.white)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isFocused ? Color.white.opacity(0.25) : Color.black.opacity(0.35))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isFocused ? Color.white.opacity(0.8) : .clear, lineWidth: 1)
            )
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

    @ViewBuilder
    private func pickerOverlayContent(activePicker selection: BubblePicker) -> some View {
        let isLanguage = selection == .language
        let title = isLanguage ? "Lookup language" : "Lookup model"
        let options = pickerOptions(isLanguage: isLanguage)
        BubblePickerOverlay(
            title: title,
            options: options,
            onSelectOption: { option in
                if isLanguage {
                    actions.onLookupLanguageChange(option.value)
                } else {
                    actions.onLlmModelChange(option.value)
                }
            },
            activePicker: $activePicker
        )
    }

    private func pickerOptions(isLanguage: Bool) -> [BubblePickerOption] {
        if isLanguage {
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
        }
        return configuration.llmModelOptions.map { model in
            BubblePickerOption(
                id: model,
                title: model,
                value: model,
                isSelected: model == configuration.llmModel,
                lineLimit: 2
            )
        }
    }
    #endif

    // MARK: - Styling

    private var queryFont: Font {
        scaledFont(textStyle: .title3, weight: .semibold)
    }

    private var bodyFont: Font {
        scaledFont(textStyle: .callout, weight: .regular)
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

    private func scaledFont(textStyle: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * configuration.fontScale, weight: weight)
        #else
        return .system(size: 16 * configuration.fontScale, weight: weight)
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
        if let maxHeight = configuration.maxContentHeight {
            return maxHeight
        }
        #if os(tvOS)
        return UIScreen.main.bounds.height * 0.5
        #else
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

    var asLinguistBubbleState: LinguistBubbleState {
        LinguistBubbleState(query: query, status: status, answer: answer, model: model)
    }
}

/// Backwards compatibility state for Video Player
struct VideoLinguistBubbleState: Equatable {
    let query: String
    let status: LinguistBubbleStatus
    let answer: String?
    let model: String?

    var asLinguistBubbleState: LinguistBubbleState {
        LinguistBubbleState(query: query, status: status, answer: answer, model: model)
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
