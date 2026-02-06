import SwiftUI

// MARK: - Picker UI

extension LinguistBubbleView {

    // MARK: - tvOS Picker

    #if os(tvOS)
    struct BubblePickerOption: Identifiable {
        let id: String
        let title: String
        let value: String
        let isSelected: Bool
        let lineLimit: Int
    }

    struct BubblePickerOptionRow: View {
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

    struct BubblePickerOverlay: View {
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

    func bubbleControlLabel(isFocused: Bool, @ViewBuilder content: () -> some View) -> some View {
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

    func bubbleControlItem(
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
    var pickerOverlay: some View {
        if let activePicker {
            pickerOverlayContent(activePicker: activePicker)
        }
    }

    func pickerOverlayContent(activePicker selection: BubblePicker) -> some View {
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
    var iOSPickerOverlay: some View {
        if let picker = iOSActivePicker {
            iOSPickerSheet(for: picker)
        }
    }

    @ViewBuilder
    func iOSPickerSheet(for picker: iOSBubblePicker) -> some View {
        let pickerData = iOSPickerData(for: picker)
        iOSPickerContent(
            title: pickerData.title,
            options: pickerData.options,
            onSelect: pickerData.onSelect,
            onDismiss: { iOSActivePicker = nil }
        )
    }

    func iOSPickerData(for picker: iOSBubblePicker) -> (title: String, options: [iOSPickerOption], onSelect: (iOSPickerOption) -> Void) {
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

    struct iOSPickerOption: Identifiable {
        let id: String
        let title: String
        let value: String
        let isSelected: Bool
    }

    @ViewBuilder
    func iOSPickerContent(
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
}
