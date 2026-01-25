import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - tvOS Button Style for Search Results

#if os(tvOS)
struct TVSearchResultCardStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isFocused ? Color.white.opacity(0.25) : Color.white.opacity(0.08))
            )
            .scaleEffect(configuration.isPressed ? 0.97 : (isFocused ? 1.03 : 1.0))
            .animation(.easeInOut(duration: 0.15), value: isFocused)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

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

// MARK: - Search Result Display Model

struct SearchResultDisplayModel: Identifiable {
    let id: String
    let result: MediaSearchResult
    let highlightedSnippet: AttributedString

    init(result: MediaSearchResult, query: String) {
        self.id = result.id
        self.result = result
        self.highlightedSnippet = Self.highlightSnippet(result.snippet, query: query)
    }

    private static func highlightSnippet(_ snippet: String, query: String) -> AttributedString {
        var attributed = AttributedString(snippet)
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !trimmedQuery.isEmpty else { return attributed }

        let lowerSnippet = snippet.lowercased()
        var searchRange = lowerSnippet.startIndex..<lowerSnippet.endIndex

        while let range = lowerSnippet.range(of: trimmedQuery, options: [], range: searchRange) {
            let start = lowerSnippet.distance(from: lowerSnippet.startIndex, to: range.lowerBound)
            let length = lowerSnippet.distance(from: range.lowerBound, to: range.upperBound)
            let attrStart = attributed.index(attributed.startIndex, offsetByCharacters: start)
            let attrEnd = attributed.index(attrStart, offsetByCharacters: length)
            attributed[attrStart..<attrEnd].backgroundColor = .yellow.opacity(0.3)
            attributed[attrStart..<attrEnd].foregroundColor = .primary
            searchRange = range.upperBound..<lowerSnippet.endIndex
        }
        return attributed
    }
}

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
        Button(action: {
            onTap()
        }) {
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

// MARK: - Search Results List

struct MediaSearchResultsListView: View {
    let results: [MediaSearchResult]
    let query: String
    let isTV: Bool
    let actionType: MediaSearchActionType
    let onSelect: (MediaSearchResult) -> Void
    let onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            headerView
            #if !os(tvOS)
            Divider()
                .background(Color.white.opacity(0.2))
            #endif
            ScrollView {
                #if os(tvOS)
                // tvOS: Use spaced cards that are easier to focus
                LazyVStack(alignment: .leading, spacing: 8) {
                    ForEach(displayModels) { model in
                        MediaSearchResultRowView(
                            model: model,
                            actionType: actionType,
                            isTV: isTV,
                            onSelect: { onSelect(model.result) }
                        )
                    }
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 8)
                #else
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(displayModels) { model in
                        MediaSearchResultRowView(
                            model: model,
                            actionType: actionType,
                            isTV: isTV,
                            onSelect: { onSelect(model.result) }
                        )
                        if model.id != displayModels.last?.id {
                            Divider()
                                .background(Color.white.opacity(0.1))
                                .padding(.horizontal, 12)
                        }
                    }
                }
                #endif
            }
            .frame(maxHeight: maxResultsHeight)
        }
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.black.opacity(0.85))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.white.opacity(0.2), lineWidth: 1)
                )
        )
        #if os(tvOS)
        .focusSection()
        #endif
    }

    private var headerView: some View {
        HStack {
            Text("\(results.count) result\(results.count == 1 ? "" : "s") for \"\(query)\"")
                .font(isTV ? .headline : .subheadline)
                .foregroundStyle(.white)
            Spacer()
            Button(action: onDismiss) {
                Image(systemName: "xmark")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.7))
                    .padding(6)
                    .background(Color.white.opacity(0.1), in: Circle())
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
    }

    private var displayModels: [SearchResultDisplayModel] {
        results.map { SearchResultDisplayModel(result: $0, query: query) }
    }

    private var maxResultsHeight: CGFloat {
        isTV ? 600 : 300
    }
}

// MARK: - Search Result Row

struct MediaSearchResultRowView: View {
    let model: SearchResultDisplayModel
    let actionType: MediaSearchActionType
    let isTV: Bool
    let onSelect: () -> Void

    var body: some View {
        #if os(tvOS)
        Button(action: onSelect) {
            tvRowContent
        }
        .buttonStyle(TVSearchResultCardStyle())
        #else
        Button(action: onSelect) {
            rowContent
        }
        .buttonStyle(.plain)
        #endif
    }

    #if os(tvOS)
    private var tvRowContent: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(model.highlightedSnippet)
                .font(.body)
                .lineLimit(3)
                .foregroundStyle(.white)
                .multilineTextAlignment(.leading)

            HStack(spacing: 8) {
                if let chunkInfo = chunkLabel {
                    Text(chunkInfo)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let sentence = sentenceLabel {
                    Text(sentence)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let time = timeLabel {
                    Text(time)
                        .font(.caption)
                        .foregroundStyle(.cyan)
                }
                Spacer()
                Text(actionType.buttonLabel)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.cyan)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    #endif

    private var rowContent: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .top, spacing: 8) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(model.highlightedSnippet)
                        .font(snippetFont)
                        .lineLimit(3)
                        .foregroundStyle(.white)
                    metadataView
                }
                Spacer(minLength: 8)
                actionButton
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .contentShape(Rectangle())
    }

    @ViewBuilder
    private var metadataView: some View {
        HStack(spacing: 6) {
            if let chunkInfo = chunkLabel {
                Text(chunkInfo)
                    .font(metaFont)
                    .foregroundStyle(.secondary)
            }
            if let sentenceInfo = sentenceLabel {
                Text(sentenceInfo)
                    .font(metaFont)
                    .foregroundStyle(.secondary)
            }
            if let timeInfo = timeLabel {
                Text(timeInfo)
                    .font(metaFont)
                    .foregroundStyle(.secondary)
            }
            if model.result.occurrenceCount > 1 {
                Text("\(model.result.occurrenceCount) matches")
                    .font(metaFont)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var actionButton: some View {
        HStack(spacing: 4) {
            Image(systemName: actionType.icon)
            Text(actionType.label)
        }
        .font(buttonFont)
        .foregroundStyle(.white)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            Capsule()
                .fill(Color.blue.opacity(0.6))
        )
    }

    private var chunkLabel: String? {
        guard let index = model.result.chunkIndex, let total = model.result.chunkTotal else {
            return nil
        }
        return "Chunk \(index + 1)/\(total)"
    }

    private var sentenceLabel: String? {
        guard let start = model.result.startSentence else { return nil }
        if let end = model.result.endSentence, end != start {
            return "Sentences \(start)-\(end)"
        }
        return "Sentence \(start)"
    }

    private var timeLabel: String? {
        guard let time = model.result.approximateTimeSeconds, time > 0 else { return nil }
        let minutes = Int(time) / 60
        let seconds = Int(time) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }

    private var snippetFont: Font {
        isTV ? .body : .subheadline
    }

    private var metaFont: Font {
        isTV ? .caption : .caption2
    }

    private var buttonFont: Font {
        isTV ? .caption : .caption2.weight(.semibold)
    }
}

// MARK: - Full Search Panel (Modal/Sheet)

struct MediaSearchPanelView: View {
    @Binding var query: String
    @Binding var state: MediaSearchState
    let jobId: String?
    let isTV: Bool
    let actionType: MediaSearchActionType
    let onSearch: (String) -> Void
    let onSelect: (MediaSearchResult) -> Void
    let onDismiss: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            MediaSearchInputView(
                query: $query,
                placeholder: "Search text...",
                isTV: isTV,
                onSubmit: { onSearch(query) },
                onClear: {
                    query = ""
                    state = .idle
                }
            )

            switch state {
            case .idle:
                Spacer()
                Text("Enter a search term to find text across all tracks")
                    .font(isTV ? .body : .subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Spacer()

            case .searching:
                Spacer()
                ProgressView()
                    .scaleEffect(isTV ? 1.5 : 1.0)
                Text("Searching...")
                    .font(isTV ? .body : .subheadline)
                    .foregroundStyle(.secondary)
                Spacer()

            case let .results(results):
                MediaSearchResultsListView(
                    results: results,
                    query: query,
                    isTV: isTV,
                    actionType: actionType,
                    onSelect: onSelect,
                    onDismiss: onDismiss
                )

            case let .empty(searchedQuery):
                Spacer()
                Image(systemName: "magnifyingglass")
                    .font(.largeTitle)
                    .foregroundStyle(.secondary)
                Text("No results found for \"\(searchedQuery)\"")
                    .font(isTV ? .body : .subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Spacer()

            case let .error(message):
                Spacer()
                Image(systemName: "exclamationmark.triangle")
                    .font(.largeTitle)
                    .foregroundStyle(.orange)
                Text(message)
                    .font(isTV ? .body : .subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Spacer()
            }
        }
        .padding(isTV ? 24 : 16)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black.opacity(0.9))
    }
}

// MARK: - Search Overlay (for Header Integration)

struct MediaSearchOverlayView: View {
    @Binding var isPresented: Bool
    @Binding var query: String
    @Binding var state: MediaSearchState
    let jobId: String?
    let isTV: Bool
    let sizeScale: CGFloat
    let actionType: MediaSearchActionType
    let onSearch: (String) -> Void
    let onSelect: (MediaSearchResult) -> Void

    #if os(tvOS)
    @FocusState private var isTextFieldFocused: Bool
    #endif

    var body: some View {
        if isPresented {
            VStack(alignment: .trailing, spacing: 8) {
                compactSearchField
                stateIndicatorView
                if case let .results(results) = state, !results.isEmpty {
                    MediaSearchResultsListView(
                        results: results,
                        query: query,
                        isTV: isTV,
                        actionType: actionType,
                        onSelect: { result in
                            onSelect(result)
                            isPresented = false
                        },
                        onDismiss: { isPresented = false }
                    )
                    .frame(maxWidth: overlayMaxWidth)
                }
            }
            .transition(.opacity.combined(with: .scale(scale: 0.95, anchor: .topTrailing)))
            #if os(tvOS)
            .onAppear {
                // Auto-focus the text field when overlay appears on tvOS
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                    isTextFieldFocused = true
                }
            }
            #endif
        }
    }

    @ViewBuilder
    private var stateIndicatorView: some View {
        switch state {
        case .idle:
            EmptyView()
        case .searching:
            EmptyView() // Progress indicator is shown inline
        case let .empty(searchedQuery):
            Text("No results for \"\(searchedQuery)\"")
                .font(isTV ? .caption : .caption2)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 10 * sizeScale)
                .padding(.vertical, 4 * sizeScale)
                .background(
                    Capsule()
                        .fill(Color.black.opacity(0.5))
                )
        case let .error(message):
            Text("Error: \(message)")
                .font(isTV ? .caption : .caption2)
                .foregroundStyle(.orange)
                .padding(.horizontal, 10 * sizeScale)
                .padding(.vertical, 4 * sizeScale)
                .background(
                    Capsule()
                        .fill(Color.black.opacity(0.5))
                )
        case .results:
            EmptyView() // Results list is shown below
        }
    }

    private var compactSearchField: some View {
        HStack(spacing: 6) {
            Image(systemName: "magnifyingglass")
                .font(iconFont)
                .foregroundStyle(.secondary)
            #if os(tvOS)
            TextField("Search...", text: $query)
                .textFieldStyle(.plain)
                .font(inputFont)
                .foregroundStyle(.white)
                .frame(minWidth: inputFieldWidth)
                .focused($isTextFieldFocused)
                .onSubmit { onSearch(query) }
            #else
            TextField("Search...", text: $query)
                .textFieldStyle(.plain)
                .font(inputFont)
                .foregroundStyle(.white)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
                .frame(width: inputFieldWidth)
                .onSubmit { onSearch(query) }
            #endif
            if case .searching = state {
                ProgressView()
                    .scaleEffect(0.6)
                    .tint(.white)
            } else if !query.isEmpty {
                Button(action: {
                    query = ""
                    state = .idle
                }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(iconFont)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            Button(action: { isPresented = false }) {
                Image(systemName: "xmark")
                    .font(iconFont)
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 10 * sizeScale)
        .padding(.vertical, 6 * sizeScale)
        .background(
            Capsule()
                .fill(Color.black.opacity(0.7))
                .overlay(
                    Capsule().stroke(Color.white.opacity(0.3), lineWidth: 1)
                )
        )
        #if os(tvOS)
        .focusSection()
        #endif
    }

    private var iconFont: Font {
        scaledFont(style: isTV ? .callout : .caption1, weight: .regular)
    }

    private var inputFont: Font {
        scaledFont(style: isTV ? .callout : .caption1, weight: .regular)
    }

    private var inputFieldWidth: CGFloat {
        (isTV ? 200 : 120) * sizeScale
    }

    private var overlayMaxWidth: CGFloat {
        isTV ? 500 : 350
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }
}

// MARK: - Search View Model

@MainActor
final class MediaSearchViewModel: ObservableObject {
    @Published var query: String = ""
    @Published var state: MediaSearchState = .idle
    @Published var isExpanded: Bool = false

    private var searchTask: Task<Void, Never>?
    private var debounceTask: Task<Void, Never>?
    private let debounceInterval: Duration = .milliseconds(300)

    var resultCount: Int {
        if case let .results(results) = state {
            return results.count
        }
        return 0
    }

    var isSearching: Bool {
        if case .searching = state {
            return true
        }
        return false
    }

    func search(jobId: String?, using client: APIClient) {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            state = .idle
            return
        }
        guard let jobId else {
            state = .error("No job ID available")
            return
        }

        searchTask?.cancel()
        state = .searching

        searchTask = Task {
            do {
                let response = try await client.searchMedia(jobId: jobId, query: trimmed)
                guard !Task.isCancelled else { return }
                if response.results.isEmpty {
                    // Check if count > 0 but results empty - indicates decoding issue
                    if response.count > 0 {
                        state = .error("Decode error: \(response.count) results expected but 0 decoded")
                    } else {
                        state = .empty(trimmed)
                    }
                } else {
                    state = .results(response.results)
                }
            } catch is CancellationError {
                // Ignore cancellation
            } catch {
                guard !Task.isCancelled else { return }
                state = .error(error.localizedDescription)
            }
        }
    }

    func debouncedSearch(jobId: String?, using client: APIClient) {
        debounceTask?.cancel()
        debounceTask = Task {
            do {
                try await Task.sleep(for: debounceInterval)
                guard !Task.isCancelled else { return }
                search(jobId: jobId, using: client)
            } catch {
                // Ignore cancellation
            }
        }
    }

    func clear() {
        searchTask?.cancel()
        debounceTask?.cancel()
        query = ""
        state = .idle
    }

    func dismiss() {
        isExpanded = false
    }

    func calculateTargetSentence(from result: MediaSearchResult) -> Int? {
        guard let startSentence = result.startSentence else { return nil }
        let endSentence = result.endSentence ?? startSentence
        let span = max(endSentence - startSentence, 0)

        if let ratio = result.offsetRatio, ratio.isFinite {
            let clampedRatio = min(max(ratio, 0), 1)
            return max(startSentence + Int(round(Double(span) * clampedRatio)), 1)
        }
        return max(startSentence, 1)
    }

    func calculateSeekTime(from result: MediaSearchResult) -> Double? {
        if let time = result.approximateTimeSeconds, time.isFinite, time >= 0 {
            return time
        }
        if let cueStart = result.cueStartSeconds, cueStart.isFinite, cueStart >= 0 {
            return cueStart
        }
        return nil
    }
}
