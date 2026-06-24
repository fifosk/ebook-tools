import Foundation
import SwiftUI

struct AppleBookCreateNarrationSection: View {
    let creationMode: AppleCreateMode
    @Binding var inputLanguage: AppleBookCreateLanguage
    @Binding var targetLanguage: AppleBookCreateLanguage
    @Binding var additionalTargetLanguages: String
    @Binding var voice: AppleBookCreateVoiceOption
    @Binding var targetVoice: AppleBookCreateVoiceOption?
    @Binding var languageVoiceOverrides: [String: String]
    let availableInputLanguages: [AppleBookCreateLanguage]
    let availableTargetLanguages: [AppleBookCreateLanguage]
    let availableVoices: [AppleBookCreateVoiceOption]
    let availableTargetVoices: [AppleBookCreateVoiceOption]
    let languageVoiceOptions: [String: [AppleBookCreateVoiceOption]]
    let targetLanguagesForVoiceOverrides: [String]
    let isLoadingVoiceInventory: Bool
    let voiceInventoryErrorMessage: String?
    let voicePreviewStates: [String: AppleVoicePreviewState]
    let voicePreviewErrorMessages: [String: String]
    let onRefreshVoiceInventory: () -> Void
    let onPreviewVoice: (String, String, AppleBookCreateVoiceOption) -> Void

    var body: some View {
        Section(creationMode == .subtitleJob ? "Languages" : "Narration") {
            #if os(tvOS)
            Picker("Input", selection: $inputLanguage) {
                ForEach(availableInputLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookInputLanguagePicker")

            Picker("Target", selection: $targetLanguage) {
                ForEach(availableTargetLanguages) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookTargetLanguagePicker")
            #else
            AppleBookCreateLanguageSelector(
                title: "Input",
                selection: $inputLanguage,
                options: availableInputLanguages,
                accessibilityIdentifier: "createBookInputLanguagePicker"
            )

            AppleBookCreateLanguageSelector(
                title: "Target",
                selection: $targetLanguage,
                options: availableTargetLanguages,
                accessibilityIdentifier: "createBookTargetLanguagePicker"
            )
            #endif

            if creationMode == .generatedBook || creationMode == .narrateEbook {
                TextField("Additional targets", text: $additionalTargetLanguages)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createBookAdditionalTargetLanguagesField")
            }

            if creationMode != .subtitleJob {
                Picker("Voice", selection: $voice) {
                    ForEach(availableVoices) { option in
                        Text(option.label).tag(option)
                    }
                }
                .accessibilityIdentifier("createBookVoicePicker")

                voicePreviewControl(
                    language: inputLanguage.backendValue,
                    label: inputLanguage.label,
                    selectedVoice: voice,
                    buttonIdentifier: "createBookVoicePreviewButton",
                    errorIdentifier: "createBookVoicePreviewErrorLabel"
                )

                if creationMode == .generatedBook || creationMode == .narrateEbook {
                    Picker("Target voice", selection: $targetVoice) {
                        Text("Same as voice").tag(nil as AppleBookCreateVoiceOption?)
                        ForEach(availableTargetVoices) { option in
                            Text(option.label).tag(Optional(option))
                        }
                    }
                    .accessibilityIdentifier("createBookTargetVoicePicker")

                    voicePreviewControl(
                        language: targetLanguage.backendValue,
                        label: targetLanguage.label,
                        selectedVoice: targetVoice ?? voice,
                        buttonIdentifier: "createBookTargetVoicePreviewButton",
                        errorIdentifier: "createBookTargetVoicePreviewErrorLabel"
                    )

                    if !targetLanguagesForVoiceOverrides.isEmpty {
                        ForEach(targetLanguagesForVoiceOverrides, id: \.self) { language in
                            let options = languageVoiceOptions[language] ?? availableTargetVoices
                            let selectedOverride = languageVoiceOverrides[language]
                                .flatMap(AppleBookCreateVoiceOption.init(backendValue:)) ?? targetVoice ?? voice
                            Picker(
                                "\(language) voice",
                                selection: voiceOverrideBinding(for: language)
                            ) {
                                Text("Default").tag("")
                                ForEach(options) { option in
                                    Text(option.label).tag(option.backendValue)
                                }
                            }
                            .accessibilityIdentifier("createBookVoiceOverridePicker-\(language)")

                            voicePreviewControl(
                                language: language,
                                label: language,
                                selectedVoice: selectedOverride,
                                buttonIdentifier: "createBookVoiceOverridePreviewButton-\(language)",
                                errorIdentifier: "createBookVoiceOverridePreviewErrorLabel-\(language)"
                            )
                        }
                    }
                }

                voiceInventoryStatusControl
            }
        }
    }

    @ViewBuilder
    private var voiceInventoryStatusControl: some View {
        if isLoadingVoiceInventory {
            Label("Loading voice inventory", systemImage: "arrow.triangle.2.circlepath")
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createBookVoiceInventoryLoadingLabel")
        } else if let voiceInventoryErrorMessage {
            Text(voiceInventoryErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createBookVoiceInventoryErrorLabel")
            Button(action: onRefreshVoiceInventory) {
                Label("Retry Voices", systemImage: "arrow.clockwise")
            }
            .accessibilityIdentifier("createBookVoiceInventoryRetryButton")
        }
    }

    private func voicePreviewControl(
        language: String,
        label: String,
        selectedVoice: AppleBookCreateVoiceOption,
        buttonIdentifier: String,
        errorIdentifier: String
    ) -> some View {
        let key = AppleBookCreatePresentation.voicePreviewKey(language: language)
        let state = voicePreviewStates[key] ?? .idle
        return VStack(alignment: .leading, spacing: 6) {
            HStack {
                Button {
                    onPreviewVoice(language, label, selectedVoice)
                } label: {
                    Label(voicePreviewTitle(for: state), systemImage: voicePreviewSystemImage(for: state))
                }
                .disabled(state == .loading)
                .accessibilityIdentifier(buttonIdentifier)

                if state == .loading {
                    ProgressView()
                        .accessibilityIdentifier("\(buttonIdentifier)-progress")
                }
            }

            if let message = voicePreviewErrorMessages[key] {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier(errorIdentifier)
            }
        }
    }

    private func voicePreviewTitle(for state: AppleVoicePreviewState) -> String {
        switch state {
        case .idle:
            return "Preview Voice"
        case .loading:
            return "Loading Preview"
        case .playing:
            return "Playing Preview"
        }
    }

    private func voicePreviewSystemImage(for state: AppleVoicePreviewState) -> String {
        switch state {
        case .idle:
            return "play.circle"
        case .loading:
            return "hourglass"
        case .playing:
            return "speaker.wave.2"
        }
    }

    private func voiceOverrideBinding(for language: String) -> Binding<String> {
        Binding(
            get: {
                languageVoiceOverrides[language] ?? ""
            },
            set: { newValue in
                let normalizedValue = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                if normalizedValue.isEmpty {
                    languageVoiceOverrides.removeValue(forKey: language)
                } else {
                    languageVoiceOverrides[language] = normalizedValue
                }
            }
        )
    }
}
