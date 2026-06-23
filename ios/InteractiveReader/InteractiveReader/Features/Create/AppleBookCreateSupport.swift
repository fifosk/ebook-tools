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
}

struct AppleCreateSubmitPresentation: Equatable {
    let title: String
    let systemImage: String
}

enum AppleBookCreatePresentation {
    static func availableCreateModes(isTV: Bool) -> [AppleCreateMode] {
        isTV ? [.generatedBook] : AppleCreateMode.allCases
    }

    static func submitButtonPresentation(
        for mode: AppleCreateMode,
        isSubmitting: Bool
    ) -> AppleCreateSubmitPresentation {
        if isSubmitting {
            return AppleCreateSubmitPresentation(title: "Submitting", systemImage: "hourglass")
        }
        switch mode {
        case .generatedBook:
            return AppleCreateSubmitPresentation(title: "Generate Audiobook", systemImage: "sparkles")
        case .narrateEbook:
            return AppleCreateSubmitPresentation(title: "Narrate EPUB", systemImage: "book")
        case .subtitleJob:
            return AppleCreateSubmitPresentation(title: "Create Subtitles", systemImage: "captions.bubble")
        case .youtubeDub:
            return AppleCreateSubmitPresentation(title: "Create Dub", systemImage: "video")
        }
    }

    static func derivedBaseOutput(
        for mode: AppleCreateMode,
        topic: String,
        bookName: String,
        sourceBaseOutput: String,
        subtitleSourcePath: String,
        youtubeVideoPath: String
    ) -> String {
        switch mode {
        case .generatedBook:
            return deriveBaseOutputName(bookName.isEmpty ? topic : bookName)
        case .narrateEbook:
            return trimmed(sourceBaseOutput)
        case .subtitleJob:
            return deriveBaseOutputName(subtitleSourcePath)
        case .youtubeDub:
            return deriveBaseOutputName(youtubeVideoPath)
        }
    }

    static func subtitleModelLabel(_ model: String) -> String {
        let trimmedModel = trimmed(model)
        return trimmedModel.isEmpty ? "Backend default" : trimmedModel
    }

    static func subtitleTransliterationModelLabel(_ model: String) -> String {
        let trimmedModel = trimmed(model)
        return trimmedModel.isEmpty ? "Use translation model" : trimmedModel
    }

    static func deriveBaseOutputName(_ value: String) -> String {
        let trimmedValue = trimmed(value)
        let scalars = trimmedValue.unicodeScalars.map { scalar -> Character in
            CharacterSet.alphanumerics.contains(scalar) ? Character(scalar) : "-"
        }
        let collapsed = String(scalars)
            .split(separator: "-", omittingEmptySubsequences: true)
            .joined(separator: "-")
            .lowercased()
        return collapsed.nonEmptyValue ?? "generated-book"
    }

    private static func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
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
        switch normalized {
        case "llm":
            self = .llm
        case "googletrans", "google", "google_translate", "google-translate":
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
