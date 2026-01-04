import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct JobRowView: View {
    let job: PipelineStatusResponse
    let resumeStatus: LibraryRowView.ResumeStatus

    var body: some View {
        HStack(spacing: rowSpacing) {
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(iconColor.opacity(0.2))
                RoundedRectangle(cornerRadius: 10)
                    .stroke(iconColor.opacity(0.4), lineWidth: 1)
                Image(systemName: iconName)
                    .font(.system(size: iconSize, weight: .semibold))
                    .foregroundStyle(iconColor)
            }
            .frame(width: iconFrame, height: iconFrame)

            VStack(alignment: .leading, spacing: textSpacing) {
                Text(jobTitle)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(titleScaleFactor)
                    .truncationMode(.tail)
                HStack(spacing: 8) {
                    LanguageFlagPairView(flags: languageFlags)
                        .font(metaFont)
                    JobTypeGlyphBadge(glyph: jobTypeGlyph)
                        .font(metaFont)
                    Text(statusGlyph.icon)
                        .font(statusGlyphFont)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .foregroundStyle(statusColor)
                        .background(statusColor.opacity(0.18), in: Capsule())
                        .accessibilityLabel(statusGlyph.label)
                    Text(resumeStatus.label)
                        .font(metaFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .foregroundStyle(resumeStatus.foreground)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(resumeStatus.background, in: Capsule())
                }
                Text(jobIdLabel)
                    .font(metaFont)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                if let progressLabel {
                    Text(progressLabel)
                        .font(metaFont)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.75)
                }
                if let progressValue {
                    ProgressView(value: progressValue)
                        .tint(iconColor)
                }
            }

            Spacer()

            #if !os(tvOS)
            Image(systemName: "chevron.right")
                .foregroundStyle(.secondary)
            #endif
        }
        .padding(.vertical, rowPadding)
    }

    private var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: inputLanguage,
            translationLanguage: translationLanguage
        )
    }

    private var inputLanguage: String? {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0)
    }

    private var translationLanguage: String? {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0)
    }

    private var jobTitle: String {
        if let label = job.jobLabel?.nonEmptyValue {
            return label
        }
        if let title = job.result?.objectValue?["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        if let book = job.result?.objectValue?["book_metadata"]?.objectValue,
           let title = book["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        return "Job \(job.jobId)"
    }

    private var jobTypeGlyph: JobTypeGlyph {
        JobTypeGlyphResolver.glyph(for: job.jobType)
    }

    private var jobIdLabel: String {
        "ID: \(job.jobId)"
    }

    private var progressLabel: String? {
        guard job.isActiveForDisplay else { return nil }
        guard let snapshot = job.latestEvent?.snapshot else { return "Progress: preparing" }
        if let total = snapshot.total, total > 0 {
            let percent = Int((Double(snapshot.completed) / Double(total)) * 100)
            return "Progress \(snapshot.completed)/\(total) · \(percent)%"
        }
        return "Progress \(snapshot.completed)"
    }

    private var progressValue: Double? {
        guard job.isActiveForDisplay else { return nil }
        guard let snapshot = job.latestEvent?.snapshot else { return nil }
        guard let total = snapshot.total, total > 0 else { return nil }
        return Double(snapshot.completed) / Double(total)
    }

    private var statusGlyph: (icon: String, label: String) {
        switch job.displayStatus {
        case .pending:
            return ("⏳", "Pending")
        case .running:
            return ("▶️", "Running")
        case .pausing:
            return ("⏯️", "Pausing")
        case .paused:
            return ("⏸️", "Paused")
        case .completed:
            return ("✅", "Completed")
        case .failed:
            return ("❌", "Failed")
        case .cancelled:
            return ("🚫", "Cancelled")
        }
    }

    private var statusGlyphFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base * 2.0)
        #else
        return .system(size: 28)
        #endif
    }

    private var statusColor: Color {
        switch job.displayStatus {
        case .pending, .pausing:
            return .orange
        case .running:
            return .blue
        case .paused:
            return .yellow
        case .completed:
            return .green
        case .failed, .cancelled:
            return .red
        }
    }

    private var jobVariant: PlayerChannelVariant {
        let type = job.jobType.lowercased()
        if type.contains("youtube") {
            return .youtube
        }
        if type.contains("dub") {
            return .dub
        }
        if type.contains("subtitle") {
            return .subtitles
        }
        if type.contains("video") {
            return .video
        }
        if type.contains("nas") {
            return .nas
        }
        if type.contains("book") || type.contains("pipeline") {
            return .book
        }
        return .job
    }

    private var iconName: String {
        switch jobVariant {
        case .book:
            return "book.closed"
        case .subtitles:
            return "captions.bubble"
        case .video, .youtube:
            return "play.rectangle"
        case .nas:
            return "tray.2"
        case .dub:
            return "waveform"
        case .job:
            return "briefcase"
        }
    }

    private var iconColor: Color {
        switch jobVariant {
        case .book:
            return Color(red: 0.96, green: 0.62, blue: 0.04)
        case .subtitles:
            return Color(red: 0.34, green: 0.55, blue: 0.92)
        case .video, .youtube:
            return Color(red: 0.16, green: 0.77, blue: 0.45)
        case .nas:
            return Color(red: 0.5, green: 0.55, blue: 0.63)
        case .dub:
            return Color(red: 0.82, green: 0.4, blue: 0.92)
        case .job:
            return Color(red: 0.6, green: 0.65, blue: 0.7)
        }
    }

    private var iconFrame: CGFloat {
        #if os(tvOS)
        return 76
        #else
        return 48
        #endif
    }

    private var iconSize: CGFloat {
        #if os(tvOS)
        return 32
        #else
        return 20
        #endif
    }

    private var titleFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.headline)
        #else
        return .headline
        #endif
    }

    private var metaFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.caption1)
        #else
        return .caption
        #endif
    }

    private var titleLineLimit: Int {
        #if os(tvOS)
        return 1
        #else
        return 2
        #endif
    }

    private var titleScaleFactor: CGFloat {
        #if os(tvOS)
        return 0.9
        #else
        return 0.95
        #endif
    }

    private var rowSpacing: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return 10
        #endif
    }

    private var textSpacing: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 3
        #endif
    }

    private var rowPadding: CGFloat {
        #if os(tvOS)
        return 6
        #else
        return 5
        #endif
    }

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        let sources = [job.result?.objectValue, job.parameters?.objectValue].compactMap { $0 }
        for source in sources {
            if let found = metadataString(in: source, keys: keys, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataString(
        in metadata: [String: JSONValue],
        keys: [String],
        maxDepth: Int
    ) -> String? {
        for key in keys {
            if let found = metadataString(in: metadata, key: key, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataString(
        in metadata: [String: JSONValue],
        key: String,
        maxDepth: Int
    ) -> String? {
        if let value = metadata[key]?.stringValue {
            return value
        }
        guard maxDepth > 0 else { return nil }
        for value in metadata.values {
            if let nested = value.objectValue {
                if let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                    return found
                }
            }
            if case let .array(items) = value {
                for entry in items {
                    if let nested = entry.objectValue,
                       let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                        return found
                    }
                }
            }
        }
        return nil
    }

    #if os(tvOS)
    private func scaledTVOSFont(_ style: UIFont.TextStyle) -> Font {
        let size = UIFont.preferredFont(forTextStyle: style).pointSize * 0.5
        return .system(size: size)
    }
    #endif
}
