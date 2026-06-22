import SwiftUI

struct VideoPlayerBookmarkMenu: View {
    let bookmarks: [PlaybackBookmarkEntry]
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void
    let onUserInteraction: () -> Void

    #if os(tvOS)
    let isFocused: Bool
    let isDisabled: Bool
    #endif

    var body: some View {
        Menu {
            menuContent
        } label: {
            menuLabel
        }
        #if os(tvOS)
        .disabled(isDisabled)
        #endif
    }

    @ViewBuilder
    private var menuContent: some View {
        Button("Add Bookmark", action: addBookmark)
        if bookmarks.isEmpty {
            Text("No bookmarks yet.")
                .foregroundStyle(.secondary)
        } else {
            Section("Jump") {
                ForEach(bookmarks) { bookmark in
                    Button(bookmark.label) { jumpToBookmark(bookmark) }
                }
            }
            Section("Remove") {
                ForEach(bookmarks) { bookmark in
                    Button(role: .destructive) {
                        removeBookmark(bookmark)
                    } label: {
                        Text(bookmark.label)
                    }
                }
            }
        }
    }

    private var menuLabel: some View {
        #if os(tvOS)
        VideoPlayerControlLabel(
            systemName: "bookmark",
            label: "Bookmarks",
            font: .callout.weight(.semibold),
            isFocused: isFocused
        )
        #else
        Label("Bookmarks", systemImage: "bookmark")
            .labelStyle(.titleAndIcon)
            .font(.caption)
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
            .foregroundStyle(.white)
        #endif
    }

    private func addBookmark() {
        onAddBookmark?()
        onUserInteraction()
    }

    private func jumpToBookmark(_ bookmark: PlaybackBookmarkEntry) {
        onJumpToBookmark(bookmark)
        onUserInteraction()
    }

    private func removeBookmark(_ bookmark: PlaybackBookmarkEntry) {
        onRemoveBookmark(bookmark)
        onUserInteraction()
    }
}
