import SwiftUI

struct LibraryPlaybackHeader: View {
    let item: LibraryItem
    let coverURL: URL?
    let itemTypeLabel: String
    let showImageReel: Bool
    let imageReelURLs: [URL]
    let coverWidth: CGFloat
    let coverHeight: CGFloat
    let titleFont: Font
    let authorFont: Font
    let metaFont: Font
    let titleLineLimit: Int
    let headerSpacing: CGFloat
    let headerTextSpacing: CGFloat

    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif

    private var showsImageReel: Bool {
        showImageReel && !imageReelURLs.isEmpty
    }

    var body: some View {
        #if os(tvOS)
        regularLayout
        #else
        if horizontalSizeClass == .regular {
            regularLayout
        } else {
            compactLayout
        }
        #endif
    }

    private var regularLayout: some View {
        HStack(alignment: .top, spacing: headerSpacing) {
            LibraryPlaybackHeaderInfo(
                item: item,
                coverURL: coverURL,
                itemTypeLabel: itemTypeLabel,
                coverWidth: coverWidth,
                coverHeight: coverHeight,
                titleFont: titleFont,
                authorFont: authorFont,
                metaFont: metaFont,
                titleLineLimit: titleLineLimit,
                headerSpacing: headerSpacing,
                headerTextSpacing: headerTextSpacing
            )
            if showsImageReel {
                Spacer(minLength: 12)
                LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            } else {
                Spacer()
            }
        }
    }

    private var compactLayout: some View {
        VStack(alignment: .leading, spacing: headerSpacing) {
            LibraryPlaybackHeaderInfo(
                item: item,
                coverURL: coverURL,
                itemTypeLabel: itemTypeLabel,
                coverWidth: coverWidth,
                coverHeight: coverHeight,
                titleFont: titleFont,
                authorFont: authorFont,
                metaFont: metaFont,
                titleLineLimit: titleLineLimit,
                headerSpacing: headerSpacing,
                headerTextSpacing: headerTextSpacing
            )
            if showsImageReel {
                LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}

private struct LibraryPlaybackHeaderInfo: View {
    let item: LibraryItem
    let coverURL: URL?
    let itemTypeLabel: String
    let coverWidth: CGFloat
    let coverHeight: CGFloat
    let titleFont: Font
    let authorFont: Font
    let metaFont: Font
    let titleLineLimit: Int
    let headerSpacing: CGFloat
    let headerTextSpacing: CGFloat

    var body: some View {
        HStack(alignment: .top, spacing: headerSpacing) {
            AsyncImage(url: coverURL) { phase in
                if let image = phase.image {
                    image.resizable().scaledToFill()
                } else {
                    Color.gray.opacity(0.2)
                }
            }
            .frame(width: coverWidth, height: coverHeight)
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
            )

            VStack(alignment: .leading, spacing: headerTextSpacing) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(0.9)
                    .truncationMode(.tail)
                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .font(authorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)
                Text(itemTypeLabel)
                    .font(metaFont)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.2), in: Capsule())
            }
        }
    }
}

struct LibraryPlaybackLoadingView: View {
    let usesDarkBackground: Bool

    var body: some View {
        VStack(spacing: 12) {
            ProgressView()
                .tint(usesDarkBackground ? .white : nil)
            Text("Loading media...")
                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }
}

struct LibraryPlaybackErrorView: View {
    let message: String
    let usesDarkBackground: Bool

    var body: some View {
        ContentUnavailableView {
            Label("Unable to load media", systemImage: "exclamationmark.triangle.fill")
        } description: {
            Text(message)
        }
        .foregroundStyle(usesDarkBackground ? .white : .primary)
    }
}

struct LibraryPlaybackUnavailableView: View {
    let usesDarkBackground: Bool

    var body: some View {
        ContentUnavailableView {
            Label("No playable media", systemImage: "play.slash")
        } description: {
            Text("This entry does not include a playable reader, audio, or video asset.")
        }
        .foregroundStyle(usesDarkBackground ? .white : .primary)
    }
}

private struct LibraryImageReel: View {
    let urls: [URL]
    let height: CGFloat

    private let spacing: CGFloat = 8
    private let maxImages = 7
    private let minImages = 1

    var body: some View {
        GeometryReader { proxy in
            let itemHeight = height
            let itemWidth = itemHeight * 0.78
            let maxVisible = max(
                minImages,
                min(maxImages, Int((proxy.size.width + spacing) / (itemWidth + spacing)))
            )
            let visible = Array(urls.prefix(maxVisible))
            HStack(spacing: spacing) {
                ForEach(visible.indices, id: \.self) { index in
                    AsyncImage(url: visible[index]) { phase in
                        if let image = phase.image {
                            image
                                .resizable()
                                .scaledToFill()
                        } else {
                            Color.gray.opacity(0.2)
                        }
                    }
                    .frame(width: itemWidth, height: itemHeight)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                    )
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .trailing)
        }
        .frame(height: height)
    }
}
