import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct LibraryRowView: View {
    let item: LibraryItem
    let coverURL: URL?
    let resumeStatus: ResumeStatus

    var body: some View {
        HStack(spacing: rowSpacing) {
            AsyncImage(url: coverURL) { phase in
                if let image = phase.image {
                    image
                        .resizable()
                        .scaledToFill()
                } else if phase.error != nil {
                    Color.gray.opacity(0.2)
                } else {
                    ProgressView()
                }
            }
            .frame(width: coverWidth, height: coverHeight)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
            )

            VStack(alignment: .leading, spacing: textSpacing) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(titleScaleFactor)
                    .truncationMode(.tail)
                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .font(authorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)
                HStack(spacing: 8) {
                    LanguageFlagPairView(flags: languageFlags)
                        .font(metaFont)
                    JobTypeGlyphBadge(glyph: jobTypeGlyph)
                        .font(metaFont)
                    Text(resumeStatus.label)
                        .font(metaFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .foregroundStyle(resumeStatus.foreground)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(resumeStatus.background, in: Capsule())
                }
            }

            Spacer()

            #if !os(tvOS)
            OfflineSyncBadge(jobId: item.jobId, kind: .library, isEligible: true)
            Image(systemName: "chevron.right")
                .foregroundStyle(.secondary)
            #endif
        }
        .padding(.vertical, rowPadding)
    }

    private var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: originalLanguage,
            translationLanguage: translationLanguage
        )
    }

    private var originalLanguage: String? {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? item.language
    }

    private var translationLanguage: String? {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? item.language
    }

    private var jobTypeGlyph: JobTypeGlyph {
        let resolved = JobTypeGlyphResolver.glyph(for: jobTypeValue)
        if isTvSeries {
            return JobTypeGlyph(icon: "TV", label: "TV series", variant: .tv)
        }
        return resolved
    }

    private var jobTypeValue: String? {
        metadataString(for: ["job_type", "jobType", "type"], maxDepth: 2) ?? item.itemType
    }

    private var isTvSeries: Bool {
        guard let metadata = tvMetadata else { return false }
        if let kind = metadata["kind"]?.stringValue?.lowercased(),
           kind == "tv_episode" {
            return true
        }
        if metadata["show"]?.objectValue != nil || metadata["episode"]?.objectValue != nil {
            return true
        }
        return false
    }

    private var tvMetadata: [String: JSONValue]? {
        guard let metadata = item.metadata else { return nil }
        return extractTvMediaMetadata(from: metadata)
    }

    private var coverWidth: CGFloat {
        #if os(tvOS)
        return 88
        #else
        return 52
        #endif
    }

    private var coverHeight: CGFloat {
        #if os(tvOS)
        return 132
        #else
        return 72
        #endif
    }

    private var titleFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.headline)
        #else
        return .headline
        #endif
    }

    private var authorFont: Font {
        #if os(tvOS)
        return scaledTVOSFont(.subheadline)
        #else
        return .subheadline
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
        return 10
        #else
        return 12
        #endif
    }

    private var textSpacing: CGFloat {
        #if os(tvOS)
        return 3
        #else
        return 4
        #endif
    }

    private var rowPadding: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 6
        #endif
    }

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        guard let metadata = item.metadata else { return nil }
        return metadataString(in: metadata, keys: keys, maxDepth: maxDepth)
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

    private func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        let paths: [[String]] = [
            ["result", "youtube_dub", "media_metadata"],
            ["result", "subtitle", "metadata", "media_metadata"],
            ["request", "media_metadata"],
            ["media_metadata"]
        ]
        for path in paths {
            if let value = nestedValue(metadata, path: path)?.objectValue {
                return value
            }
        }
        return nil
    }

    private func nestedValue(_ source: [String: JSONValue], path: [String]) -> JSONValue? {
        var current: JSONValue = .object(source)
        for key in path {
            guard let object = current.objectValue, let next = object[key] else { return nil }
            current = next
        }
        return current
    }

    #if os(tvOS)
    private func scaledTVOSFont(_ style: UIFont.TextStyle) -> Font {
        let size = UIFont.preferredFont(forTextStyle: style).pointSize * 0.5
        return .system(size: size)
    }
    #endif
}

extension LibraryRowView {
    struct ResumeStatus: Equatable {
        let label: String
        let foreground: Color
        let background: Color

        static func none() -> ResumeStatus {
            ResumeStatus(
                label: "None",
                foreground: .secondary,
                background: Color.secondary.opacity(0.15)
            )
        }

        static func local(label: String) -> ResumeStatus {
            ResumeStatus(
                label: label,
                foreground: .orange,
                background: Color.orange.opacity(0.2)
            )
        }

        static func cloud(label: String) -> ResumeStatus {
            ResumeStatus(
                label: label,
                foreground: .blue,
                background: Color.blue.opacity(0.2)
            )
        }

        static func both(label: String) -> ResumeStatus {
            ResumeStatus(
                label: label,
                foreground: .green,
                background: Color.green.opacity(0.2)
            )
        }
    }
}
