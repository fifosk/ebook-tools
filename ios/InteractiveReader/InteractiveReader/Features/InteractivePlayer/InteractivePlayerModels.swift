import Foundation

enum InteractivePlayerFocusArea: Hashable {
    case controls
    case transcript
}

struct InteractivePlayerHeaderInfo: Equatable {
    let title: String
    let author: String
    let itemTypeLabel: String
    let coverURL: URL?
    let secondaryCoverURL: URL?
    let languageFlags: [LanguageFlagEntry]
    let translationModel: String?
}

struct TextPlayerWordSelection: Equatable {
    let sentenceIndex: Int
    let variantKind: TextPlayerVariantKind
    let tokenIndex: Int
}

struct SentenceOption: Identifiable {
    let id: Int
    let label: String
    let startTime: Double?
}

struct SentenceRange: Equatable {
    let start: Int
    let end: Int
}
