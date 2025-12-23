//
//  TextPlayerModels.swift
//  
//
//  Created to provide placeholder models to unblock the build.
//  These are minimal implementations that may be replaced by real implementations later.
//

import Foundation
import SwiftUI

public enum TextPlayerTimingTrack: Equatable {
    case mix
    case original
    case translation
}

public enum TextPlayerSentenceState: Equatable {
    case past
    case active
    case future
}

public struct TextPlayerVariantDisplay: Identifiable, Equatable {
    public enum Kind: CaseIterable {
        case original
        case translation
        case transliteration
    }
    
    public let id: String
    public let kind: Kind
    public let label: String
    public let tokens: [String]
    public let revealedCount: Int
    
    public init(id: String = UUID().uuidString,
                kind: Kind,
                label: String,
                tokens: [String],
                revealedCount: Int) {
        self.id = id
        self.kind = kind
        self.label = label
        self.tokens = tokens
        self.revealedCount = revealedCount
    }
}

public struct TextPlayerSentenceDisplay: Identifiable, Equatable {
    public let id: String
    public let variants: [TextPlayerVariantDisplay]
    public let state: TextPlayerSentenceState
    
    public init(id: String = UUID().uuidString,
                variants: [TextPlayerVariantDisplay],
                state: TextPlayerSentenceState) {
        self.id = id
        self.variants = variants
        self.state = state
    }
}

public struct TextPlayerTimeline {
    
    // MARK: - Nested Types
    
    public struct TimelineSentence {
        public let index: Int
        public let startTime: Double
        
        public init(index: Int, startTime: Double) {
            self.index = index
            self.startTime = startTime
        }
    }
    
    public struct TimelineDisplay {
        public let sentences: [TextPlayerSentenceDisplay]
        public let activeIndex: Int
        
        public init(sentences: [TextPlayerSentenceDisplay], activeIndex: Int) {
            self.sentences = sentences
            self.activeIndex = activeIndex
        }
    }
    
    // MARK: - Static Functions
    
    public static func buildTimelineSentences(
        sentences: [InteractiveChunk.Sentence],
        activeTimingTrack: TextPlayerTimingTrack,
        audioDuration: Double?,
        useCombinedPhases: Bool
    ) -> [TimelineSentence]? {
        // Minimal implementation returns nil
        return nil
    }
    
    public static func buildTimelineDisplay(
        timelineSentences: [TimelineSentence],
        chunkTime: Double,
        audioDuration: Double?,
        isVariantVisible: (TextPlayerVariantDisplay.Kind) -> Bool
    ) -> TimelineDisplay? {
        // Minimal implementation returns empty display with activeIndex 0
        return TimelineDisplay(sentences: [], activeIndex: 0)
    }
    
    public static func buildStaticDisplay(
        sentences: [InteractiveChunk.Sentence],
        isVariantVisible: (TextPlayerVariantDisplay.Kind) -> Bool
    ) -> [TextPlayerSentenceDisplay] {
        return sentences.map { sentence in
            var variants: [TextPlayerVariantDisplay] = []
            
            if isVariantVisible(.original), let original = sentence.original {
                variants.append(.init(
                    kind: .original,
                    label: "Original",
                    tokens: original.split(separator: " ").map(String.init),
                    revealedCount: 0
                ))
            }
            if isVariantVisible(.translation), let translation = sentence.translation {
                variants.append(.init(
                    kind: .translation,
                    label: "Translation",
                    tokens: translation.split(separator: " ").map(String.init),
                    revealedCount: 0
                ))
            }
            if isVariantVisible(.transliteration), let transliteration = sentence.transliteration {
                variants.append(.init(
                    kind: .transliteration,
                    label: "Transliteration",
                    tokens: transliteration.split(separator: " ").map(String.init),
                    revealedCount: 0
                ))
            }
            
            return TextPlayerSentenceDisplay(
                variants: variants,
                state: .future
            )
        }
    }
    
    public static func selectActiveSentence(
        from sentences: [TextPlayerSentenceDisplay]
    ) -> [TextPlayerSentenceDisplay] {
        // Minimal implementation returns input unchanged
        return sentences
    }
}
