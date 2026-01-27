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

    var body: some View {
        Menu {
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
    }

    @ViewBuilder
    private var menuContent: some View {
        if let onAddBookmark {
            Button {
                onAddBookmark()
                onUserInteraction()
            } label: {
                Label("Add Bookmark", systemImage: "bookmark.fill")
            }
        }
        if bookmarks.isEmpty {
            Text("No bookmarks yet.")
                .foregroundStyle(.secondary)
        } else {
            Section("Jump") {
                ForEach(bookmarks) { bookmark in
                    Button(bookmark.label) {
                        onJumpToBookmark(bookmark)
                        onUserInteraction()
                    }
                }
            }
            Section("Remove") {
                ForEach(bookmarks) { bookmark in
                    Button(role: .destructive) {
                        onRemoveBookmark(bookmark)
                        onUserInteraction()
                    } label: {
                        Text(bookmark.label)
                    }
                }
            }
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
            .animation(.easeInOut(duration: 0.15), value: scale)
    }
}
#endif
