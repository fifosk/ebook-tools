import Foundation

struct SubtitleVisibility: Hashable {
    var showOriginal: Bool = true
    var showTranslation: Bool = true
    var showTransliteration: Bool = true

    func allows(_ kind: VideoSubtitleLineKind) -> Bool {
        switch kind {
        case .original:
            return showOriginal
        case .translation:
            return showTranslation
        case .transliteration:
            return showTransliteration
        case .unknown:
            return showTranslation
        }
    }
}
