import SwiftUI

struct LibraryRowView: View {
    let item: LibraryItem
    let coverURL: URL?

    var body: some View {
        HStack(spacing: 12) {
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

            VStack(alignment: .leading, spacing: 4) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                    .lineLimit(2)
                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                HStack(spacing: 8) {
                    Text(item.language)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(itemTypeLabel)
                        .font(.caption)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.accentColor.opacity(0.15), in: Capsule())
                }
            }

            Spacer()

            #if !os(tvOS)
            Image(systemName: "chevron.right")
                .foregroundStyle(.secondary)
            #endif
        }
        .padding(.vertical, 6)
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
        return 120
        #else
        return 52
        #endif
    }

    private var coverHeight: CGFloat {
        #if os(tvOS)
        return 180
        #else
        return 72
        #endif
    }

    private var titleFont: Font {
        #if os(tvOS)
        return .title3
        #else
        return .headline
        #endif
    }
}
