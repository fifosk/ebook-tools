import SwiftUI

struct MediaDiagnosticsStripView: View {
    let diagnostics: PipelineMediaDiagnostics?
    var usesDarkBackground = false

    var body: some View {
        if let diagnostics, diagnostics.hasGaps {
            HStack(alignment: .center, spacing: iconSpacing) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(iconFont)
                    .foregroundStyle(.orange)
                    .frame(width: iconFrame, height: iconFrame)

                VStack(alignment: .leading, spacing: 2) {
                    Text("Media needs attention")
                        .font(titleFont)
                        .foregroundStyle(titleColor)
                    Text("Playback may skip sections until missing media is repaired.")
                        .font(detailFont)
                        .foregroundStyle(detailColor)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(containerPadding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(containerBackground, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(containerBorder, lineWidth: 1)
            )
            .accessibilityElement(children: .combine)
            .accessibilityLabel(accessibilityLabel(for: diagnostics))
        }
    }

    private var containerPadding: CGFloat {
        #if os(tvOS)
        return 14
        #else
        return 10
        #endif
    }

    private var containerBackground: Color {
        Color.orange.opacity(usesDarkBackground ? 0.18 : 0.1)
    }

    private var containerBorder: Color {
        Color.orange.opacity(0.45)
    }

    private func accessibilityLabel(for diagnostics: PipelineMediaDiagnostics) -> String {
        var parts: [String] = []
        if diagnostics.chunksWithoutFiles > 0 {
            parts.append("chunks without files")
        }
        if diagnostics.chunksWithoutMetadata > 0 {
            parts.append("chunks without metadata")
        }
        if diagnostics.filesWithoutUrl > 0 {
            parts.append("files without playback URLs")
        }
        if diagnostics.filesWithoutSize > 0 {
            parts.append("files without size metadata")
        }
        let detail = parts.isEmpty ? "media gaps detected" : parts.joined(separator: ", ")
        return "Media needs attention, \(detail). Playback may skip sections until missing media is repaired."
    }

    private var titleFont: Font {
        #if os(tvOS)
        return .headline
        #else
        return .subheadline.weight(.semibold)
        #endif
    }

    private var detailFont: Font {
        #if os(tvOS)
        return .subheadline
        #else
        return .caption
        #endif
    }

    private var iconFont: Font {
        #if os(tvOS)
        return .title3.weight(.semibold)
        #else
        return .callout.weight(.semibold)
        #endif
    }

    private var iconFrame: CGFloat {
        #if os(tvOS)
        return 30
        #else
        return 22
        #endif
    }

    private var iconSpacing: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return 8
        #endif
    }

    private var titleColor: Color {
        usesDarkBackground ? .white.opacity(0.95) : .primary
    }

    private var detailColor: Color {
        usesDarkBackground ? .white.opacity(0.72) : .secondary
    }
}
