import SwiftUI

struct MediaDiagnosticsStripView: View {
    let diagnostics: PipelineMediaDiagnostics?
    var usesDarkBackground = false
    var showsHealthyDiagnostics = false

    private var columns: [GridItem] {
        #if os(tvOS)
        return [GridItem(.adaptive(minimum: 118, maximum: 180), spacing: 10)]
        #else
        return [GridItem(.adaptive(minimum: 82, maximum: 140), spacing: 8)]
        #endif
    }

    private var items: [MediaDiagnosticsItem] {
        guard let diagnostics else { return [] }
        let timingValue = diagnostics.chunkCount > 0
            ? "\(diagnostics.chunksWithTiming)/\(diagnostics.chunkCount)"
            : "\(diagnostics.chunksWithTiming)"
        var values = [
            MediaDiagnosticsItem(label: "Files", value: "\(diagnostics.mediaFileCount)", systemImage: "doc.on.doc"),
            MediaDiagnosticsItem(label: "Chunks", value: "\(diagnostics.chunkCount)", systemImage: "square.stack.3d.up"),
            MediaDiagnosticsItem(label: "Audio", value: "\(diagnostics.chunksWithAudio)", systemImage: "waveform"),
            MediaDiagnosticsItem(label: "Timing", value: timingValue, systemImage: "timer"),
            MediaDiagnosticsItem(label: "Images", value: "\(diagnostics.chunksWithImages)", systemImage: "photo")
        ]
        if diagnostics.hasGaps {
            values.append(
                MediaDiagnosticsItem(
                    label: "Gaps",
                    value: "\(diagnostics.missingCount + diagnostics.chunksWithoutFiles)",
                    systemImage: "exclamationmark.triangle",
                    isWarning: true
                )
            )
        }
        return values
    }

    var body: some View {
        if let diagnostics, shouldShowDiagnostics(for: diagnostics), !items.isEmpty {
            LazyVGrid(columns: columns, alignment: .leading, spacing: itemSpacing) {
                ForEach(items) { item in
                    MediaDiagnosticsMetricView(item: item, usesDarkBackground: usesDarkBackground)
                }
            }
            .padding(containerPadding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(containerBackground(hasGaps: diagnostics.hasGaps), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(containerBorder(hasGaps: diagnostics.hasGaps), lineWidth: 1)
            )
            .accessibilityElement(children: .combine)
            .accessibilityLabel(accessibilityLabel(for: diagnostics))
        }
    }

    private func shouldShowDiagnostics(for diagnostics: PipelineMediaDiagnostics) -> Bool {
        showsHealthyDiagnostics || diagnostics.hasGaps
    }

    private var containerPadding: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return 8
        #endif
    }

    private var itemSpacing: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 8
        #endif
    }

    private func containerBackground(hasGaps: Bool) -> Color {
        if hasGaps {
            return Color.orange.opacity(usesDarkBackground ? 0.18 : 0.1)
        }
        return usesDarkBackground ? Color.white.opacity(0.08) : Color.primary.opacity(0.04)
    }

    private func containerBorder(hasGaps: Bool) -> Color {
        if hasGaps {
            return Color.orange.opacity(0.45)
        }
        return usesDarkBackground ? Color.white.opacity(0.12) : Color.primary.opacity(0.08)
    }

    private func accessibilityLabel(for diagnostics: PipelineMediaDiagnostics) -> String {
        var parts = [
            "\(diagnostics.mediaFileCount) files",
            "\(diagnostics.chunkCount) chunks",
            "\(diagnostics.chunksWithAudio) audio chunks",
            "\(diagnostics.chunksWithTiming) timed chunks",
            "\(diagnostics.chunksWithImages) image chunks"
        ]
        if diagnostics.hasGaps {
            parts.append("\(diagnostics.missingCount + diagnostics.chunksWithoutFiles) media gaps")
        }
        return "Media diagnostics, " + parts.joined(separator: ", ")
    }
}

private struct MediaDiagnosticsItem: Identifiable {
    let label: String
    let value: String
    let systemImage: String
    var isWarning = false

    var id: String { label }
}

private struct MediaDiagnosticsMetricView: View {
    let item: MediaDiagnosticsItem
    let usesDarkBackground: Bool

    var body: some View {
        HStack(spacing: iconSpacing) {
            Image(systemName: item.systemImage)
                .font(iconFont)
                .foregroundStyle(iconColor)
                .frame(width: iconFrame, height: iconFrame)
            VStack(alignment: .leading, spacing: 2) {
                Text(item.label)
                    .font(labelFont)
                    .textCase(.uppercase)
                    .foregroundStyle(labelColor)
                    .lineLimit(1)
                Text(item.value)
                    .font(valueFont)
                    .monospacedDigit()
                    .foregroundStyle(valueColor)
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, horizontalPadding)
        .padding(.vertical, verticalPadding)
        .frame(maxWidth: .infinity, minHeight: minHeight, alignment: .leading)
        .background(itemBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(item.label): \(item.value)")
    }

    private var itemBackground: Color {
        if item.isWarning {
            return Color.orange.opacity(usesDarkBackground ? 0.24 : 0.14)
        }
        return usesDarkBackground ? Color.white.opacity(0.08) : Color.primary.opacity(0.05)
    }

    private var iconColor: Color {
        item.isWarning ? .orange : (usesDarkBackground ? .white.opacity(0.76) : .secondary)
    }

    private var labelColor: Color {
        item.isWarning ? .orange : (usesDarkBackground ? .white.opacity(0.58) : .secondary)
    }

    private var valueColor: Color {
        usesDarkBackground ? .white.opacity(0.92) : .primary
    }

    private var labelFont: Font {
        #if os(tvOS)
        return .caption
        #else
        return .caption2
        #endif
    }

    private var valueFont: Font {
        #if os(tvOS)
        return .headline
        #else
        return .subheadline.weight(.semibold)
        #endif
    }

    private var iconFont: Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        return .caption.weight(.semibold)
        #endif
    }

    private var iconFrame: CGFloat {
        #if os(tvOS)
        return 24
        #else
        return 18
        #endif
    }

    private var iconSpacing: CGFloat {
        #if os(tvOS)
        return 8
        #else
        return 6
        #endif
    }

    private var horizontalPadding: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return 8
        #endif
    }

    private var verticalPadding: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 7
        #endif
    }

    private var minHeight: CGFloat {
        #if os(tvOS)
        return 54
        #else
        return 42
        #endif
    }
}
