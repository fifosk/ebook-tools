import SwiftUI

#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Bookmark Ribbon Pill View (Header Component)

/// A compact pill-styled button that displays a bookmark ribbon icon with an optional count badge.
/// Designed to be placed next to the search magnifier in the header.
struct BookmarkRibbonPillView: View {
    let bookmarkCount: Int
    let isTV: Bool
    let sizeScale: CGFloat
    let bookmarks: [PlaybackBookmarkEntry]
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void
    let onUserInteraction: () -> Void

    #if os(tvOS)
    var focusTarget: FocusState<VideoPlayerFocusTarget?>.Binding?
    var onMoveLeft: (() -> Void)?
    var onMoveRight: (() -> Void)?
    #endif

    var body: some View {
        let menu = Menu {
            menuContent
        } label: {
            pillLabel
        }
        #if os(tvOS)
        .buttonStyle(TVBookmarkPillButtonStyle())
        #else
        .buttonStyle(.plain)
        #endif
        .accessibilityLabel(accessibilityLabel)
        .accessibilityIdentifier("bookmarkRibbonPill")

        #if os(tvOS)
        if let focusTarget {
            menu
                .focused(focusTarget, equals: .control(.headerBookmark))
                .onMoveCommand(perform: handleMoveCommand)
        } else {
            menu
        }
        #else
        menu
        #endif
    }

    @ViewBuilder
    private var menuContent: some View {
        if let onAddBookmark {
            addBookmarkButton(onAddBookmark)
        }
        if bookmarks.isEmpty {
            Text("No bookmarks yet.")
                .foregroundStyle(.secondary)
        } else {
            Section("Jump") {
                ForEach(bookmarks) { bookmark in
                    jumpBookmarkButton(bookmark)
                }
            }
            Section("Remove") {
                ForEach(bookmarks) { bookmark in
                    removeBookmarkButton(bookmark)
                }
            }
        }
    }

    private func addBookmarkButton(_ action: @escaping () -> Void) -> some View {
        Button(action: { handleAddBookmark(action) }) {
            Label("Add Bookmark", systemImage: "bookmark.fill")
        }
    }

    private func jumpBookmarkButton(_ bookmark: PlaybackBookmarkEntry) -> some View {
        Button(bookmark.label) {
            handleJumpToBookmark(bookmark)
        }
    }

    private func removeBookmarkButton(_ bookmark: PlaybackBookmarkEntry) -> some View {
        Button(role: .destructive) {
            handleRemoveBookmark(bookmark)
        } label: {
            Text(bookmark.label)
        }
    }

    private var pillLabel: some View {
        HStack(spacing: iconSpacing) {
            Image(systemName: "bookmark.fill")
                .font(iconFont)
            if bookmarkCount > 0 {
                Text("\(bookmarkCount)")
                    .font(labelFont)
                    .monospacedDigit()
            }
        }
        .foregroundStyle(Color.white.opacity(0.85))
        .padding(.horizontal, paddingHorizontal)
        .padding(.vertical, paddingVertical)
        .background(
            Capsule()
                .fill(Color.black.opacity(0.55))
                .overlay(
                    Capsule().stroke(Color.white.opacity(0.22), lineWidth: 1)
                )
        )
    }

    private var iconSpacing: CGFloat {
        4 * sizeScale
    }

    private var paddingHorizontal: CGFloat {
        (isTV ? 12 : 8) * sizeScale
    }

    private var paddingVertical: CGFloat {
        (isTV ? 6 : 4) * sizeScale
    }

    private var iconFont: Font {
        scaledFont(style: isTV ? .callout : .caption1, weight: .semibold)
    }

    private var labelFont: Font {
        scaledFont(style: isTV ? .callout : .caption2, weight: .bold)
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }

    private var accessibilityLabel: String {
        if bookmarkCount > 0 {
            return "Bookmarks: \(bookmarkCount)"
        }
        return "Bookmarks"
    }

    #if os(tvOS)
    private func handleMoveCommand(_ direction: MoveCommandDirection) {
        guard focusTarget?.wrappedValue == .control(.headerBookmark) else { return }
        switch direction {
        case .left:
            onMoveLeft?()
        case .right:
            onMoveRight?()
        default:
            break
        }
    }
    #endif

    private func handleAddBookmark(_ action: () -> Void) {
        action()
        onUserInteraction()
    }

    private func handleJumpToBookmark(_ bookmark: PlaybackBookmarkEntry) {
        onJumpToBookmark(bookmark)
        onUserInteraction()
    }

    private func handleRemoveBookmark(_ bookmark: PlaybackBookmarkEntry) {
        onRemoveBookmark(bookmark)
        onUserInteraction()
    }
}

// MARK: - tvOS Button Style

#if os(tvOS)
struct TVBookmarkPillButtonStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        let scale: CGFloat = configuration.isPressed ? 0.95 : (isFocused ? 1.05 : 1.0)
        let brightness: Double = isFocused ? 0.1 : 0

        configuration.label
            .scaleEffect(scale)
            .brightness(brightness)
    }
}
#endif
