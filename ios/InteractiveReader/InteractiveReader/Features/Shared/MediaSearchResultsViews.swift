import SwiftUI

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
#endif

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
                LazyVStack(alignment: .leading, spacing: 8) {
                    ForEach(displayModels) { model in
                        MediaSearchResultRowView(
                            model: model,
                            actionType: actionType,
                            isTV: isTV,
                            onSelect: onSelect
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
                            onSelect: onSelect
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

struct MediaSearchResultRowView: View {
    let model: SearchResultDisplayModel
    let actionType: MediaSearchActionType
    let isTV: Bool
    let onSelect: (MediaSearchResult) -> Void

    var body: some View {
        #if os(tvOS)
        Button(action: handleSelect) {
            tvRowContent
        }
        .buttonStyle(TVSearchResultCardStyle())
        .accessibilityIdentifier("mediaSearchResultRow.\(model.id)")
        #else
        Button(action: handleSelect) {
            rowContent
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("mediaSearchResultRow.\(model.id)")
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

    private func handleSelect() {
        onSelect(model.result)
    }
}
