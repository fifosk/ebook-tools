import SwiftUI
#if os(iOS)
import UIKit
#endif

// MARK: - Header And Controls

extension LinguistBubbleView {

    @ViewBuilder
    var headerRow: some View {
        #if os(tvOS)
        if configuration.isSplitMode {
            tvSplitModeHeader
        } else {
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

    // MARK: - Shared Selectors

    @ViewBuilder
    var lookupLanguageMenu: some View {
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

    @ViewBuilder
    var modelMenu: some View {
        #if os(tvOS)
        bubbleControlItem(control: .model, isEnabled: true, action: {
            activePicker = .model
        }) {
            Image(systemName: "brain")
        }
        .accessibilityLabel("Lookup model")
        #else
        Menu {
            ForEach(groupedLlmModelOptions) { group in
                Section(group.title) {
                    ForEach(group.models, id: \.self) { model in
                        Button {
                            actions.onLlmModelChange(model)
                        } label: {
                            if model == configuration.llmModel {
                                Label(
                                    title: {
                                        Text(verbatim: formatModelLabel(model))
                                            .font(bubbleMenuFont)
                                    },
                                    icon: {
                                        Image(systemName: "checkmark")
                                            .font(bubbleMenuFont)
                                    }
                                )
                            } else {
                                Text(verbatim: formatModelLabel(model))
                                    .font(bubbleMenuFont)
                            }
                        }
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

    @ViewBuilder
    var voiceMenu: some View {
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

    // MARK: - iOS Header

    #if os(iOS)
    @ViewBuilder
    var iOSHeaderRow: some View {
        if isPhone {
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
                    lookupQueryText
                }
            }
        } else {
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
                    lookupQueryText
                }
            }
        }
    }

    var lookupQueryText: some View {
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

    @ViewBuilder
    var playFromNarrationButton: some View {
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

    @ViewBuilder
    var lookupSourceIndicator: some View {
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

    @ViewBuilder
    var pinToggleButton: some View {
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

    @ViewBuilder
    var layoutToggleButton: some View {
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

    // MARK: - tvOS Header

    #if os(tvOS)
    var tvSplitModeHeader: some View {
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

    var tvOverlayModeHeader: some View {
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

    @ViewBuilder
    var tvPlayFromNarrationButton: some View {
        if let onPlay = actions.onPlayFromNarration, state.cachedAudioRef != nil {
            bubbleControlItem(control: .playFromNarration, isEnabled: true, action: onPlay) {
                Image(systemName: "waveform")
                    .foregroundStyle(.cyan)
            }
            .accessibilityLabel("Play from narration")
        }
    }

    @ViewBuilder
    var tvLookupSourceIndicator: some View {
        if state.status == .ready, let source = state.lookupSource {
            Text(source == .cache ? "⚡" : "☁")
                .font(.system(size: 16))
                .foregroundStyle(source == .cache ? .yellow : .cyan)
                .accessibilityLabel(source == .cache ? "Cached lookup" : "Live lookup")
        }
    }

    @ViewBuilder
    var tvLayoutToggleButton: some View {
        if let onToggle = actions.onToggleLayoutDirection {
            bubbleControlItem(control: .layout, isEnabled: true, action: onToggle) {
                Image(systemName: "rectangle.split.2x1")
            }
            .accessibilityLabel("Toggle layout")
        }
    }

    @ViewBuilder
    var tvPinToggleButton: some View {
        if let onToggle = actions.onTogglePin {
            bubbleControlItem(control: .pin, isEnabled: true, action: onToggle) {
                Image(systemName: configuration.isPinned ? "pin.fill" : "pin")
                    .foregroundStyle(configuration.isPinned ? .yellow : .white)
            }
            .accessibilityLabel(configuration.isPinned ? "Unpin bubble" : "Pin bubble")
        }
    }
    #endif
}
