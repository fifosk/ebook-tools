import Foundation

extension AppleBookCreateView {
    var availableInputLanguages: [AppleBookCreateLanguage] {
        AppleBookCreatePresentation.availableInputLanguages(from: viewModel.creationOptions)
    }

    var availableTargetLanguages: [AppleBookCreateLanguage] {
        AppleBookCreatePresentation.availableTargetLanguages(from: viewModel.creationOptions)
    }

    var availableVoices: [AppleBookCreateVoiceOption] {
        AppleBookCreatePresentation.availableVoices(
            from: viewModel.creationOptions,
            inventory: viewModel.voiceInventory,
            language: inputLanguage.backendValue,
            selected: voice
        )
    }

    var availableTargetVoices: [AppleBookCreateVoiceOption] {
        AppleBookCreatePresentation.availableVoices(
            from: viewModel.creationOptions,
            inventory: viewModel.voiceInventory,
            language: targetLanguage.backendValue,
            selected: targetVoice ?? voice
        )
    }

    var languageVoiceOptions: [String: [AppleBookCreateVoiceOption]] {
        AppleBookCreatePresentation.languageVoiceOptions(
            from: viewModel.creationOptions,
            inventory: viewModel.voiceInventory,
            languages: targetLanguagesForVoiceOverrides,
            selectedOverrides: languageVoiceOverrides,
            fallbackVoice: targetVoice ?? voice
        )
    }

    var targetLanguagesForVoiceOverrides: [String] {
        AppleBookCreatePresentation.targetLanguagesForVoiceOverrides(
            mode: creationMode,
            primary: targetLanguage.backendValue,
            additionalTargets: additionalTargetLanguages
        )
    }

    var availableSubtitleLlmModels: [String] {
        AppleBookCreatePresentation.availableSubtitleLlmModels(
            selected: subtitleLlmModel,
            inventory: viewModel.subtitleLlmModels
        )
    }

    var availableSubtitleTransliterationModels: [String] {
        AppleBookCreatePresentation.availableSubtitleTransliterationModels(
            selected: subtitleTransliterationModel,
            translationModel: subtitleLlmModel,
            inventory: viewModel.subtitleLlmModels
        )
    }

    var availableBookTransliterationModels: [String] {
        AppleBookCreatePresentation.availableSubtitleTransliterationModels(
            selected: bookTransliterationModel,
            translationModel: "",
            inventory: viewModel.subtitleLlmModels
        )
    }

    var formattedAssEmphasisScale: String {
        AppleBookCreatePresentation.formattedAssEmphasisScale(subtitleAssEmphasisScale)
    }

    var formattedYoutubeOriginalMixPercent: String {
        AppleBookCreatePresentation.formattedYoutubeOriginalMixPercent(youtubeOriginalMixPercent)
    }

    var formattedTempo: String {
        AppleBookCreatePresentation.clampTempo(tempo).formatted(.number.precision(.fractionLength(1)))
    }

    var estimatedAudioDurationLabel: String? {
        switch creationMode {
        case .generatedBook:
            return AppleBookCreatePresentation.estimatedAudioDurationLabel(sentenceCount: sentenceCount)
        case .narrateEbook:
            return AppleBookCreatePresentation.estimatedAudioDurationLabel(
                sentenceCount: AppleBookCreatePresentation.estimatedNarrateSentenceCount(
                    startSentence: sourceStartSentence,
                    endSentence: sourceEndSentence
                )
            )
        case .subtitleJob, .youtubeDub:
            return nil
        }
    }
}
