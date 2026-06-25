import SwiftUI

struct JumpControlOverlayView: View {
    let chapters: [ChapterNavigationEntry]
    let currentSentence: Int
    let sentenceBounds: (start: Int?, end: Int?)
    let chapterLabel: (ChapterNavigationEntry, Int) -> String
    let onJumpToSentence: (Int) -> Void
    let onJumpToChapter: (ChapterNavigationEntry) -> Void

    @State private var inputSentence: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Jump To")
                .font(.subheadline.weight(.medium))

            JumpSentenceInputSection(
                inputSentence: $inputSentence,
                sentenceBounds: sentenceBounds,
                onJumpToSentence: onJumpToSentence
            )

            if !chapters.isEmpty {
                Divider()

                JumpChapterSection(
                    chapters: chapters,
                    currentSentence: currentSentence,
                    sentenceBounds: sentenceBounds,
                    chapterLabel: chapterLabel,
                    onJumpToChapter: onJumpToChapter
                )
            }
        }
        .padding(16)
        .onAppear {
            inputSentence = "\(currentSentence)"
        }
        #if os(iOS)
        .frame(width: isPad ? 340 : nil)
        .background {
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        }
        .foregroundStyle(.primary)
        #endif
    }

    private var isPad: Bool { PlatformAdapter.isPad }
}

private struct JumpSentenceInputSection: View {
    @Binding var inputSentence: String

    let sentenceBounds: (start: Int?, end: Int?)
    let onJumpToSentence: (Int) -> Void

    @FocusState private var isInputFocused: Bool

    private var inputSentenceNumber: Int? {
        guard let number = Int(sanitizedInputSentence), number > 0 else { return nil }
        return number
    }

    private var sanitizedInputSentence: String {
        inputSentence.filter(\.isNumber)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Sentence")
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack(spacing: 12) {
                sentenceField

                Button("Go", action: submitSentence)
                    .buttonStyle(.borderedProminent)
                    .disabled(inputSentenceNumber == nil)

                Spacer()

                if let start = sentenceBounds.start, let end = sentenceBounds.end {
                    Text("\(start)-\(end)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder
    private var sentenceField: some View {
        #if os(iOS)
        TextField("Enter #", text: $inputSentence)
            .keyboardType(.numberPad)
            .textFieldStyle(.roundedBorder)
            .frame(width: 100)
            .focused($isInputFocused)
            .onSubmit(submitSentence)
            .onChange(of: inputSentence) { _, newValue in
                let sanitized = newValue.filter(\.isNumber)
                if sanitized != newValue {
                    inputSentence = sanitized
                }
            }
            .toolbar {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") {
                        isInputFocused = false
                    }
                    Button("Go") {
                        submitSentence()
                    }
                    .disabled(inputSentenceNumber == nil)
                }
            }
        #else
        TextField("Enter #", text: $inputSentence)
            .frame(width: 100)
            .onSubmit(submitSentence)
        #endif
    }

    private func submitSentence() {
        guard let inputSentenceNumber else { return }
        isInputFocused = false
        onJumpToSentence(clampedSentence(inputSentenceNumber))
    }

    private func clampedSentence(_ sentence: Int) -> Int {
        var result = sentence
        if let start = sentenceBounds.start {
            result = max(start, result)
        }
        if let end = sentenceBounds.end {
            result = min(end, result)
        }
        return result
    }
}

private struct JumpChapterSection: View {
    let chapters: [ChapterNavigationEntry]
    let currentSentence: Int
    let sentenceBounds: (start: Int?, end: Int?)
    let chapterLabel: (ChapterNavigationEntry, Int) -> String
    let onJumpToChapter: (ChapterNavigationEntry) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Chapter")
                .font(.caption)
                .foregroundStyle(.secondary)

            #if os(iOS)
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 4) {
                    chapterRows
                }
            }
            .frame(maxHeight: 200)
            #else
            LazyVStack(alignment: .leading, spacing: 8) {
                chapterRows
            }
            #endif
        }
    }

    @ViewBuilder
    private var chapterRows: some View {
        ForEach(Array(chapters.enumerated()), id: \.element.id) { index, chapter in
            JumpChapterRow(
                title: chapterLabel(chapter, index),
                isActive: isActive(chapter),
                action: { onJumpToChapter(chapter) }
            )
        }
    }

    private func isActive(_ chapter: ChapterNavigationEntry) -> Bool {
        currentSentence >= chapter.startSentence &&
            currentSentence <= effectiveChapterEnd(for: chapter)
    }

    private func effectiveChapterEnd(for chapter: ChapterNavigationEntry) -> Int {
        if let end = chapter.endSentence {
            return max(end, chapter.startSentence)
        }
        if let boundsEnd = sentenceBounds.end {
            return max(boundsEnd, chapter.startSentence)
        }
        return chapter.startSentence
    }
}

private struct JumpChapterRow: View {
    let title: String
    let isActive: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Text(title)
                    .font(.subheadline)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                Spacer()

                if isActive {
                    Image(systemName: "checkmark")
                        .font(.caption)
                        .foregroundStyle(Color.accentColor)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background {
                RoundedRectangle(cornerRadius: 8)
                    .fill(isActive ? Color.accentColor.opacity(0.15) : Color.secondary.opacity(0.1))
            }
        }
        .buttonStyle(.plain)
    }
}
