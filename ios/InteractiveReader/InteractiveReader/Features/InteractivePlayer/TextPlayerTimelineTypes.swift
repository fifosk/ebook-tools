import Foundation

// MARK: - Enums

enum TextPlayerTimingTrack {
    case mix
    case translation
    case original
}

enum TextPlayerVariantKind: String {
    case original
    case translation
    case transliteration
}

enum TextPlayerSentenceState {
    case past
    case active
    case future
}

// MARK: - Display Types

struct TextPlayerVariantDisplay: Identifiable {
    let id: String
    let label: String
    let tokens: [String]
    let revealedCount: Int
    let currentIndex: Int?
    let kind: TextPlayerVariantKind
    let seekTimes: [Double]?
}

struct TextPlayerSentenceDisplay: Identifiable {
    let id: String
    let index: Int
    let sentenceNumber: Int?
    let state: TextPlayerSentenceState
    let variants: [TextPlayerVariantDisplay]
}

// MARK: - Runtime Types

struct TimelineVariantRuntime {
    let tokens: [String]
    let revealTimes: [Double]
}

struct TimelineSentenceRuntime {
    let index: Int
    let sentenceNumber: Int?
    let startTime: Double
    let endTime: Double
    let variants: [TextPlayerVariantKind: TimelineVariantRuntime]
}

struct TimelineDisplay {
    let sentences: [TextPlayerSentenceDisplay]
    let activeIndex: Int
    let effectiveTime: Double
}
