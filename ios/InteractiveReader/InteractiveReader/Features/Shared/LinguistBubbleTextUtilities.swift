import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Shared Types

#if os(iOS)
/// Sanitize text for dictionary lookup by removing enclosing quotes
enum TextLookupSanitizer {
    /// Quote characters to strip (using Unicode scalars to avoid parser issues)
    static let quoteChars: Set<Character> = [
        "\"", "'", "`",                             // ASCII quotes
        "\u{201C}", "\u{201D}",                     // Curly double quotes " "
        "\u{2018}", "\u{2019}",                     // Curly single quotes ' '
        "\u{00AB}", "\u{00BB}",                     // Guillemets « »
        "\u{201E}", "\u{201F}",                     // German quotes „ ‟
        "\u{300C}", "\u{300D}",                     // CJK brackets 「  」
        "\u{300E}", "\u{300F}"                      // CJK double brackets 『 』
    ]

    static func sanitize(_ text: String) -> String {
        var result = text.trimmingCharacters(in: .whitespacesAndNewlines)

        // Strip leading quotes
        while let first = result.first, quoteChars.contains(first) {
            result.removeFirst()
        }

        // Strip trailing quotes
        while let last = result.last, quoteChars.contains(last) {
            result.removeLast()
        }

        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

/// A text view that renders text with tappable words for Look Up / Copy
/// Preserves original text layout including newlines
struct TappableWordText: View {
    let text: String
    let font: Font
    let color: Color

    var body: some View {
        // Split by newlines first to preserve paragraph structure
        let lines = text.components(separatedBy: .newlines)

        VStack(alignment: .leading, spacing: 4) {
            ForEach(Array(lines.enumerated()), id: \.offset) { lineIndex, line in
                if line.isEmpty {
                    // Empty line = paragraph break, render minimal height spacer
                    Text(" ")
                        .font(font)
                        .foregroundStyle(.clear)
                } else {
                    // Parse line into word and non-word segments
                    let segments = parseSegments(line)

                    // Render segments in a wrapping layout
                    WrappingHStack(horizontalSpacing: 0, verticalSpacing: 2) {
                        ForEach(Array(segments.enumerated()), id: \.offset) { _, segment in
                            if segment.isWord {
                                Text(segment.text)
                                    .font(font)
                                    .foregroundStyle(color)
                                    .contextMenu {
                                        let sanitized = TextLookupSanitizer.sanitize(segment.text)
                                        Button("Look Up") {
                                            DictionaryLookupPresenter.show(term: sanitized)
                                        }
                                        Button("Copy") {
                                            UIPasteboard.general.string = sanitized
                                        }
                                    }
                            } else {
                                Text(segment.text)
                                    .font(font)
                                    .foregroundStyle(color)
                            }
                        }
                    }
                }
            }
        }
    }

    private struct TextSegment {
        let text: String
        let isWord: Bool
    }

    private func parseSegments(_ text: String) -> [TextSegment] {
        var segments: [TextSegment] = []
        var current = ""
        var isCurrentWord = false

        for char in text {
            let charIsWord = char.isLetter || char.isNumber ||
                             TextLookupSanitizer.quoteChars.contains(char)

            if current.isEmpty {
                current.append(char)
                isCurrentWord = charIsWord
            } else if charIsWord == isCurrentWord {
                current.append(char)
            } else {
                segments.append(TextSegment(text: current, isWord: isCurrentWord))
                current = String(char)
                isCurrentWord = charIsWord
            }
        }

        if !current.isEmpty {
            segments.append(TextSegment(text: current, isWord: isCurrentWord))
        }

        return segments
    }
}

/// A simple wrapping HStack that flows content like text
struct WrappingHStack: Layout {
    var horizontalSpacing: CGFloat = 0
    var verticalSpacing: CGFloat = 4

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = layout(proposal: proposal, subviews: subviews)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = layout(proposal: proposal, subviews: subviews)

        for (index, position) in result.positions.enumerated() {
            subviews[index].place(
                at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y),
                proposal: .unspecified
            )
        }
    }

    private func layout(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, positions: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var lineHeight: CGFloat = 0
        var maxX: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)

            // Wrap to next line if needed (but not for first item on line)
            if x > 0 && x + size.width > maxWidth {
                x = 0
                y += lineHeight + verticalSpacing
                lineHeight = 0
            }

            positions.append(CGPoint(x: x, y: y))
            x += size.width + horizontalSpacing
            maxX = max(maxX, x - horizontalSpacing)
            lineHeight = max(lineHeight, size.height)
        }

        return (CGSize(width: maxX, height: y + lineHeight), positions)
    }
}

#endif
