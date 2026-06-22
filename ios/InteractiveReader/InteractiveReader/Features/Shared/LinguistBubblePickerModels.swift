// MARK: - Picker Models

extension LinguistBubbleView {

    #if os(tvOS)
    struct BubblePickerOption: Identifiable {
        let id: String
        let title: String
        let value: String
        let isSelected: Bool
        let lineLimit: Int
    }

    func pickerOptions(for picker: BubblePicker) -> [BubblePickerOption] {
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
            return groupedLlmModelOptions.flatMap { group in
                group.models.map { model in
                    BubblePickerOption(
                        id: model,
                        title: "\(group.title) — \(formatModelLabel(model))",
                        value: model,
                        isSelected: model == configuration.llmModel,
                        lineLimit: 2
                    )
                }
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

    #if os(iOS)
    struct iOSPickerOption: Identifiable {
        let id: String
        let title: String
        let value: String
        let isSelected: Bool
    }

    func iOSPickerData(for picker: iOSBubblePicker) -> (
        title: String,
        options: [iOSPickerOption],
        onSelect: (iOSPickerOption) -> Void
    ) {
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
            let modelOptions = groupedLlmModelOptions.flatMap { group in
                group.models.map { model in
                    iOSPickerOption(
                        id: model,
                        title: "\(group.title) — \(formatModelLabel(model))",
                        value: model,
                        isSelected: model == configuration.llmModel
                    )
                }
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
    #endif
}
