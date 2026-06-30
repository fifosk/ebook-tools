import Foundation

enum AppleCreateMode: String, CaseIterable, Identifiable {
    case generatedBook
    case narrateEbook
    case subtitleJob
    case youtubeDub

    var id: String { rawValue }

    var label: String {
        switch self {
        case .generatedBook:
            return "Generate"
        case .narrateEbook:
            return "Narrate EPUB"
        case .subtitleJob:
            return "Subtitles"
        case .youtubeDub:
            return "YouTube Dub"
        }
    }

    var creationTemplateMode: String {
        switch self {
        case .generatedBook:
            return "generated_book"
        case .narrateEbook:
            return "narrate_ebook"
        case .subtitleJob:
            return "subtitle_job"
        case .youtubeDub:
            return "youtube_dub"
        }
    }
}

struct AppleCreateTargetLanguageDefaults: Equatable {
    let primary: AppleBookCreateLanguage?
    let additionalTargets: String
}

struct AppleCreateLanguagePreferences: Codable, Equatable {
    let inputLanguage: String?
    let targetLanguages: [String]
    let enableLookupCache: Bool?
}

struct AppleCreateResolvedLanguagePreferences: Equatable {
    let inputLanguage: AppleBookCreateLanguage?
    let targetLanguage: AppleBookCreateLanguage?
    let additionalTargetLanguages: String?
    let enableLookupCache: Bool?
}

struct AppleCreateSubmitPresentation: Equatable {
    let title: String
    let systemImage: String
}

struct AppleCreateIntakePresentation: Equatable {
    let label: String
    let detailLines: [String]
}

struct AppleCreateSubmitState: Equatable {
    let hasConfiguration: Bool
    let mode: AppleCreateMode
    let topic: String
    let bookName: String
    let genre: String
    let hasNarrateLocalFile: Bool
    let sourcePath: String
    let sourceBaseOutput: String
    let hasSubtitleLocalFile: Bool
    let subtitleSourcePath: String
    let youtubeVideoPath: String
    let youtubeSubtitlePath: String
}

enum AppleYoutubeDubTargetHeight: Int, CaseIterable, Identifiable {
    case p320 = 320
    case p480 = 480
    case p720 = 720

    var id: Int { rawValue }
    var backendValue: Int { rawValue }

    var label: String {
        switch self {
        case .p320:
            return "320p"
        case .p480:
            return "480p"
        case .p720:
            return "720p"
        }
    }
}

enum AppleSubtitleOutputFormat: String, CaseIterable, Identifiable {
    case ass
    case srt

    var id: String { rawValue }

    var label: String {
        switch self {
        case .ass:
            return "ASS"
        case .srt:
            return "SRT"
        }
    }
}

enum AppleSubtitleTranslationProvider: String, CaseIterable, Identifiable {
    case llm
    case googleTranslate

    var id: String { rawValue }

    var backendValue: String {
        switch self {
        case .llm:
            return "llm"
        case .googleTranslate:
            return "googletrans"
        }
    }

    var label: String {
        switch self {
        case .llm:
            return "LLM"
        case .googleTranslate:
            return "Google Translate"
        }
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let dashed = normalized.replacingOccurrences(of: "_", with: "-")
        switch dashed {
        case "llm", "ollama", "default":
            self = .llm
        case "googletrans", "google", "googletranslate", "google-translate", "gtranslate", "gtrans":
            self = .googleTranslate
        default:
            return nil
        }
    }
}

enum AppleSubtitleTransliterationMode: String, CaseIterable, Identifiable {
    case `default`
    case python

    var id: String { rawValue }

    var backendValue: String {
        switch self {
        case .default:
            return "default"
        case .python:
            return "python"
        }
    }

    var label: String {
        switch self {
        case .default:
            return "Use selected LLM model"
        case .python:
            return "Python transliteration module"
        }
    }

    var allowsModelOverride: Bool {
        self != .python
    }

    init?(backendValue: String) {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: "_", with: "-")
        switch normalized {
        case "default", "llm", "ollama":
            self = .default
        case "python", "module", "python-module", "local-module":
            self = .python
        default:
            return nil
        }
    }
}

enum AppleSubtitleAssTypography {
    static let defaultFontSize = 56
    static let fontSizeRange = 12...120
    static let defaultEmphasisScale = 1.3
    static let emphasisScaleRange = 1.0...2.5
}

enum AppleSubtitleTuning {
    static let defaultWorkerCount = 10
    static let workerCountRange = 1...32
    static let defaultBatchSize = 20
    static let batchSizeRange = 1...500
    static let defaultTranslationBatchSize = 10
    static let translationBatchSizeRange = 1...50
}

enum AppleBookOutputChunking {
    static let defaultSentencesPerOutputFile = 10
    static let sentencesPerOutputFileRange = 1...100
}

enum AppleBookSentenceSplitterMode: String, CaseIterable, Identifiable {
    case regex
    case modern

    var id: String { rawValue }
    var backendValue: String { rawValue }

    var label: String {
        switch self {
        case .regex:
            return "Regex (stable)"
        case .modern:
            return "Modern (opt-in)"
        }
    }

    init(backendValue: String?) {
        let normalized = backendValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased() ?? ""
        switch normalized {
        case "modern":
            self = .modern
        default:
            self = .regex
        }
    }
}

struct AppleBookSentenceSplitterOption: Identifiable, Equatable {
    let mode: AppleBookSentenceSplitterMode
    let label: String

    var id: String { mode.id }

    static func options(
        from capabilities: BookCreationSentenceSplitterCapabilities?,
        selectedMode: AppleBookSentenceSplitterMode
    ) -> [AppleBookSentenceSplitterOption] {
        var options = capabilities?.supportedModes.compactMap { backendMode -> AppleBookSentenceSplitterOption? in
            guard let mode = recognizedMode(for: backendMode.id) else { return nil }
            let label = backendMode.label.trimmingCharacters(in: .whitespacesAndNewlines)
            return AppleBookSentenceSplitterOption(
                mode: mode,
                label: label.isEmpty ? mode.label : label
            )
        } ?? fallbackOptions

        options = deduplicated(options)
        if !options.contains(where: { $0.mode == selectedMode }) {
            options.append(AppleBookSentenceSplitterOption(mode: selectedMode, label: selectedMode.label))
        }
        return options
    }

    private static var fallbackOptions: [AppleBookSentenceSplitterOption] {
        AppleBookSentenceSplitterMode.allCases.map {
            AppleBookSentenceSplitterOption(mode: $0, label: $0.label)
        }
    }

    private static func deduplicated(_ options: [AppleBookSentenceSplitterOption]) -> [AppleBookSentenceSplitterOption] {
        var seen = Set<AppleBookSentenceSplitterMode>()
        var result: [AppleBookSentenceSplitterOption] = []
        for option in options {
            guard !seen.contains(option.mode) else { continue }
            seen.insert(option.mode)
            result.append(option)
        }
        return result.isEmpty ? fallbackOptions : result
    }

    private static func recognizedMode(for backendValue: String) -> AppleBookSentenceSplitterMode? {
        let normalized = backendValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return AppleBookSentenceSplitterMode.allCases.first { $0.backendValue == normalized }
    }
}
