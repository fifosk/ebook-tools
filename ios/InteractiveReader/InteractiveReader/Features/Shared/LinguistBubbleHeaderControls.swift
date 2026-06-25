import SwiftUI

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
                Image(systemName: "slider.horizontal.3")
            }
            .accessibilityLabel("Pronunciation voice")
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
                    Image(systemName: "slider.horizontal.3")
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
            .accessibilityLabel("Pronunciation voice")
        }
        #endif
    }

}
