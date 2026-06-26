import SwiftUI

enum TextPlayerTokenCoordinateSpace {
    static let name = "TextPlayerTokens"
}

struct TextPlayerTokenFrame: Equatable {
    let sentenceIndex: Int
    let sentenceNumber: Int?
    let variantKind: TextPlayerVariantKind
    let tokenIndex: Int
    let token: String
    let frame: CGRect
}

struct TextPlayerTokenFramePreferenceKey: PreferenceKey {
    static var defaultValue: [TextPlayerTokenFrame] = []

    static func reduce(value: inout [TextPlayerTokenFrame], nextValue: () -> [TextPlayerTokenFrame]) {
        value.append(contentsOf: nextValue())
    }
}

struct TextPlayerTapExclusionPreferenceKey: PreferenceKey {
    static var defaultValue: [CGRect] = []

    static func reduce(value: inout [CGRect], nextValue: () -> [CGRect]) {
        value.append(contentsOf: nextValue())
    }
}
