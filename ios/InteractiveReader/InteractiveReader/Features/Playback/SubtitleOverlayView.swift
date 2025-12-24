import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

struct SubtitleOverlayView: View {
    let cues: [VideoSubtitleCue]
    let currentTime: Double
    let visibility: SubtitleVisibility

    var body: some View {
        if let cue = activeCue, let text = styledText(for: cue) {
            text
                .multilineTextAlignment(.center)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(.black.opacity(0.6), in: RoundedRectangle(cornerRadius: 12))
                .padding(.bottom, 24)
                .frame(maxWidth: .infinity)
                .transition(.opacity)
        }
    }

    private var activeCue: VideoSubtitleCue? {
        cues.last { currentTime >= $0.start && currentTime <= $0.end }
    }

    private func styledText(for cue: VideoSubtitleCue) -> Text? {
        let lines = visibleLines(for: cue)
        guard !lines.isEmpty else { return nil }
        if let attributed = buildAttributedText(for: lines) {
            return Text(attributed)
        }
        let joined = lines.map(\.text).joined(separator: "\n")
        return Text(joined)
            .font(.title3)
            .foregroundStyle(.white)
    }

    private func buildAttributedText(for lines: [VideoSubtitleLine]) -> AttributedString? {
        guard lines.contains(where: { $0.spans?.isEmpty == false }) else { return nil }
        var output = AttributedString()
        let baseSize = baseFontSize
        for (index, line) in lines.enumerated() {
            if index > 0 {
                output.append(AttributedString("\n"))
            }
            if let spans = line.spans, !spans.isEmpty {
                for span in spans {
                    var segment = AttributedString(span.text)
                    let color = span.colorHex.flatMap(Color.init(hex:)) ?? .white
                    let scaled = max(0.6, min(span.scale, 2.5))
                    let size = baseSize * scaled
                    let weight: Font.Weight = span.isBold ? .semibold : .regular
                    segment.font = .system(size: size, weight: weight)
                    segment.foregroundColor = color
                    output.append(segment)
                }
            } else {
                var segment = AttributedString(line.text)
                segment.font = .system(size: baseSize, weight: .regular)
                segment.foregroundColor = .white
                output.append(segment)
            }
        }
        return output
    }

    private func visibleLines(for cue: VideoSubtitleCue) -> [VideoSubtitleLine] {
        let lines = cue.lines.isEmpty
            ? [VideoSubtitleLine(text: cue.text, spans: cue.spans, kind: .translation)]
            : cue.lines
        return lines.filter { !($0.text.isEmpty) && visibility.allows($0.kind) }
    }

    private var baseFontSize: CGFloat {
        #if canImport(UIKit)
        return UIFont.preferredFont(forTextStyle: .title3).pointSize
        #else
        return 22
        #endif
    }
}
