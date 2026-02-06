import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

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
    @State var iOSActivePicker: iOSBubblePicker?

    enum iOSBubblePicker: Hashable {
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
    @FocusState var focusedControl: BubbleHeaderControl?
    @State var activePicker: BubblePicker?
    @State var autoScaleFontScale: CGFloat = 1.0
    @State private var measuredContentHeight: CGFloat = 0
    @State private var lastContentLength: Int = 0

    enum BubbleHeaderControl: Hashable {
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

    enum BubblePicker: Hashable {
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
    func formatModelLabel(_ model: String) -> String {
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
    func formatVoiceLabel(_ voice: String) -> String {
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
    /// Audio reference from lookup cache - allows playing word from narration audio
    var cachedAudioRef: LookupCacheAudioRef? = nil

    var asLinguistBubbleState: LinguistBubbleState {
        LinguistBubbleState(query: query, status: status, answer: answer, model: model, lookupSource: lookupSource, cachedAudioRef: cachedAudioRef)
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
