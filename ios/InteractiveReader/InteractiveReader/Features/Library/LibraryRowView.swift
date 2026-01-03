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
                    Text(item.language)
                        .font(metaFont)
                        .foregroundStyle(.secondary)
                    Text(itemTypeLabel)
                        .font(metaFont)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.accentColor.opacity(0.15), in: Capsule())
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
            Image(systemName: "chevron.right")
                .foregroundStyle(.secondary)
            #endif
        }
        .padding(.vertical, rowPadding)
    }

    private var itemTypeLabel: String {
        switch item.itemType {
        case "video":
            return "Video"
        case "narrated_subtitle":
            return "Subtitles"
        default:
            return "Book"
        }
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
                label: "Resume: none",
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
