import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Bubble Label Formatting

extension LinguistBubbleView {

    /// A grouped section in the LLM model picker (one per provider/host).
    struct LlmModelOptionGroup: Identifiable {
        let id: String
        let title: String
        let models: [String]
    }

    /// Format model name for compact display.
    /// LM Studio identifiers carry a host suffix so the user can distinguish hosts at a glance.
    func formatModelLabel(_ model: String) -> String {
        let info = LinguistBubbleView.parseModelIdentifier(model)
        let baseLabel: String
        let trimmedRest = info.modelPart.isEmpty ? model : info.modelPart
        let parts = trimmedRest.split(separator: ":")
        if parts.count >= 2 {
            let modelName = String(parts[0])
            let sizeInfo = String(parts[1])
            let sizePart = sizeInfo.split(separator: "-").first.map(String.init) ?? sizeInfo
            baseLabel = "\(modelName) (\(sizePart))"
        } else if let lastPart = trimmedRest.split(separator: "/").last {
            baseLabel = String(lastPart)
        } else {
            baseLabel = trimmedRest
        }
        if let suffix = info.hostSuffix {
            return "\(baseLabel) · \(suffix)"
        }
        return baseLabel
    }

    /// Parse a `provider:model` identifier into provider tag, bare model name, and optional host short name.
    static func parseModelIdentifier(_ identifier: String) -> (
        provider: String?,
        modelPart: String,
        hostSuffix: String?
    ) {
        let trimmed = identifier.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let colon = trimmed.firstIndex(of: ":") else {
            return (nil, trimmed, nil)
        }
        let prefix = String(trimmed[..<colon]).lowercased()
        let rest = String(trimmed[trimmed.index(after: colon)...])
        switch prefix {
        case "ollama_cloud", "ollama-cloud":
            return ("ollama_cloud", rest, nil)
        case "ollama_local", "ollama-local":
            return ("ollama_local", rest, nil)
        case "lmstudio_macstudio", "lmstudio-macstudio":
            return ("lmstudio_macstudio", rest, "Mac Studio")
        case "lmstudio_macbook", "lmstudio-macbook",
             "lmstudio_macbookpro", "lmstudio-macbookpro",
             "lmstudio_macbook_pro", "lmstudio-macbook-pro":
            return ("lmstudio_macbook", rest, "MacBook")
        case "lmstudio", "lmstudio_local", "lmstudio-local":
            return ("lmstudio_macstudio", rest, "Mac Studio")
        default:
            return (nil, trimmed, nil)
        }
    }

    /// Group the flat `llmModelOptions` into ordered sections for the model picker.
    var groupedLlmModelOptions: [LlmModelOptionGroup] {
        var bucketsByTag: [String: [String]] = [:]
        let order = [
            "ollama_cloud",
            "ollama_local",
            "lmstudio_macstudio",
            "lmstudio_macbook",
            "other"
        ]
        let titles: [String: String] = [
            "ollama_cloud": "Ollama Cloud",
            "ollama_local": "Ollama Local",
            "lmstudio_macstudio": "LM Studio – Mac Studio",
            "lmstudio_macbook": "LM Studio – MacBook Pro",
            "other": "Other"
        ]
        for model in configuration.llmModelOptions {
            let info = LinguistBubbleView.parseModelIdentifier(model)
            let tag = info.provider ?? "other"
            bucketsByTag[tag, default: []].append(model)
        }
        return order.compactMap { tag in
            guard let models = bucketsByTag[tag], !models.isEmpty else { return nil }
            return LlmModelOptionGroup(
                id: tag,
                title: titles[tag] ?? tag,
                models: models
            )
        }
    }

    /// Format voice name for display.
    func formatVoiceLabel(_ voice: String) -> String {
        if voice.contains(" - ") {
            return String(voice.split(separator: " - ").first ?? Substring(voice))
        }
        if voice.hasPrefix("gTTS-") {
            return "gTTS (\(voice.dropFirst(5)))"
        }
        let pattern = #"^[a-z]{2}_[A-Z]{2}-(.+)-(?:high|medium|low|x_low)$"#
        if let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive),
           let match = regex.firstMatch(in: voice, range: NSRange(voice.startIndex..., in: voice)),
           match.numberOfRanges > 1,
           let range = Range(match.range(at: 1), in: voice) {
            return String(voice[range])
        }
        return voice
    }
}

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
