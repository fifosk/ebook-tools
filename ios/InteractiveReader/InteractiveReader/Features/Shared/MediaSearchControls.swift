import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - tvOS Button Style for Search Controls

#if os(tvOS)
struct TVSearchPillButtonStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : (isFocused ? 1.1 : 1.0))
            .brightness(isFocused ? 0.15 : 0)
            .animation(.easeInOut(duration: 0.15), value: isFocused)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}
#endif

// MARK: - Search State

enum MediaSearchState: Equatable {
    case idle
    case searching
    case results([MediaSearchResult])
    case empty(String)
    case error(String)

    static func == (lhs: MediaSearchState, rhs: MediaSearchState) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle), (.searching, .searching):
            return true
        case let (.results(lhsResults), .results(rhsResults)):
            return lhsResults.map(\.id) == rhsResults.map(\.id)
        case let (.empty(lhsQuery), .empty(rhsQuery)):
            return lhsQuery == rhsQuery
        case let (.error(lhsMsg), .error(rhsMsg)):
            return lhsMsg == rhsMsg
        default:
            return false
        }
    }
}

// MARK: - Search Action Type

enum MediaSearchActionType: String, Identifiable, CaseIterable {
    case jumpToSentence
    case seekToTime
    case openInReader

    var id: String { rawValue }

    var label: String {
        switch self {
        case .jumpToSentence:
            return "Jump to sentence"
        case .seekToTime:
            return "Seek to time"
        case .openInReader:
            return "Open in Reader"
        }
    }

    var icon: String {
        switch self {
        case .jumpToSentence:
            return "text.cursor"
        case .seekToTime:
            return "forward.end"
        case .openInReader:
            return "book"
        }
    }

    var buttonLabel: String {
        switch self {
        case .jumpToSentence:
            return "Jump"
        case .seekToTime:
            return "Seek"
        case .openInReader:
            return "Open"
        }
    }
}

// MARK: - Search Pill View (Header Component)

struct MediaSearchPillView: View {
    @Binding var isExpanded: Bool
    let resultCount: Int
    let isSearching: Bool
    let isTV: Bool
    let sizeScale: CGFloat
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: iconSpacing) {
                Image(systemName: "magnifyingglass")
                    .font(iconFont)
                if isSearching {
                    ProgressView()
                        .scaleEffect(progressScale)
                        .tint(.white)
                } else if resultCount > 0 {
                    Text("\(resultCount)")
                        .font(labelFont)
                        .monospacedDigit()
                }
            }
            .foregroundStyle(Color.white.opacity(0.85))
            .padding(.horizontal, paddingHorizontal)
            .padding(.vertical, paddingVertical)
            .background(
                Capsule()
                    .fill(Color.black.opacity(isExpanded ? 0.7 : 0.55))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(isExpanded ? 0.35 : 0.22), lineWidth: 1)
                    )
            )
        }
        #if os(tvOS)
        .buttonStyle(TVSearchPillButtonStyle())
        #else
        .buttonStyle(.plain)
        #endif
        .accessibilityLabel(accessibilityLabel)
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

    private var progressScale: CGFloat {
        isTV ? 0.8 : 0.6
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
        if isSearching {
            return "Searching"
        }
        if resultCount > 0 {
            return "Search: \(resultCount) results"
        }
        return "Search"
    }
}

// MARK: - Search Input Field

struct MediaSearchInputView: View {
    @Binding var query: String
    let placeholder: String
    let isTV: Bool
    let onSubmit: () -> Void
    let onClear: () -> Void

    #if os(tvOS)
    @FocusState private var isFocused: Bool
    #endif

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.secondary)
            #if os(tvOS)
            TextField(placeholder, text: $query)
                .textFieldStyle(.plain)
                .focused($isFocused)
                .onSubmit(onSubmit)
            #else
            TextField(placeholder, text: $query)
                .textFieldStyle(.plain)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
                .onSubmit(onSubmit)
            #endif
            if !query.isEmpty {
                Button(action: onClear) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, isTV ? 12 : 8)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.black.opacity(0.3))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.white.opacity(0.2), lineWidth: 1)
                )
        )
    }
}
