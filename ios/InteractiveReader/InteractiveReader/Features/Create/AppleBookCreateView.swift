import SwiftUI

struct AppleBookCreateView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = AppleBookCreateViewModel()

    let sectionPicker: BrowseSectionPicker?
    let onJobSubmitted: (String) -> Void
    let onOpenJobs: (String) -> Void
    let usesDarkBackground: Bool

    @State private var topic = ""
    @State private var bookName = ""
    @State private var genre = ""
    @State private var author = "Me"
    @State private var sentenceCount = 30
    @State private var inputLanguage = AppleBookCreateLanguage.english
    @State private var targetLanguage = AppleBookCreateLanguage.arabic
    @State private var voice = AppleBookCreateVoice.gtts
    @State private var includeTransliteration = true
    @State private var enableLookupCache = true

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let sectionPicker {
                sectionPicker
            }

            List {
                promptSection
                narrationSection
                outputSection
                statusSection
                submitSection
            }
            #if os(tvOS)
            .listStyle(.plain)
            #else
            .listStyle(.insetGrouped)
            .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
            #endif
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
        .accessibilityIdentifier("appleBookCreateView")
    }

    private var promptSection: some View {
        Section("Book") {
            TextField("Topic", text: $topic)
                .textInputAutocapitalization(.sentences)
                .accessibilityIdentifier("createBookTopicField")
            TextField("Title", text: $bookName)
                .textInputAutocapitalization(.words)
                .accessibilityIdentifier("createBookTitleField")
            TextField("Genre", text: $genre)
                .textInputAutocapitalization(.words)
                .accessibilityIdentifier("createBookGenreField")
            TextField("Author", text: $author)
                .textInputAutocapitalization(.words)
                .accessibilityIdentifier("createBookAuthorField")
            sentenceCountControl
        }
    }

    @ViewBuilder
    private var sentenceCountControl: some View {
        #if os(tvOS)
        LabeledContent("Sentences") {
            HStack(spacing: 12) {
                Button {
                    sentenceCount = max(1, sentenceCount - 5)
                } label: {
                    Image(systemName: "minus")
                }
                .disabled(sentenceCount <= 1)
                .accessibilityLabel("Decrease sentences")

                Text("\(sentenceCount)")
                    .monospacedDigit()
                    .frame(minWidth: 48)

                Button {
                    sentenceCount = min(500, sentenceCount + 5)
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(sentenceCount >= 500)
                .accessibilityLabel("Increase sentences")
            }
        }
        .accessibilityIdentifier("createBookSentenceControl")
        #else
        Stepper(value: $sentenceCount, in: 1...500, step: 5) {
            LabeledContent("Sentences", value: "\(sentenceCount)")
        }
        .accessibilityIdentifier("createBookSentenceStepper")
        #endif
    }

    private var narrationSection: some View {
        Section("Narration") {
            Picker("Input", selection: $inputLanguage) {
                ForEach(AppleBookCreateLanguage.allCases) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookInputLanguagePicker")

            Picker("Target", selection: $targetLanguage) {
                ForEach(AppleBookCreateLanguage.allCases) { language in
                    Text(language.label).tag(language)
                }
            }
            .accessibilityIdentifier("createBookTargetLanguagePicker")

            Picker("Voice", selection: $voice) {
                ForEach(AppleBookCreateVoice.allCases) { option in
                    Text(option.label).tag(option)
                }
            }
            .accessibilityIdentifier("createBookVoicePicker")
        }
    }

    private var outputSection: some View {
        Section("Output") {
            LabeledContent("Path", value: derivedBaseOutput)
                .accessibilityIdentifier("createBookBaseOutputLabel")
            Toggle("Transliteration", isOn: $includeTransliteration)
                .accessibilityIdentifier("createBookTransliterationToggle")
            Toggle("Lookup Cache", isOn: $enableLookupCache)
                .accessibilityIdentifier("createBookLookupCacheToggle")
        }
    }

    @ViewBuilder
    private var statusSection: some View {
        if let errorMessage = viewModel.errorMessage {
            Section {
                Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .accessibilityIdentifier("createBookErrorLabel")
            }
        }

        if let submittedJobId = viewModel.submittedJobId {
            Section {
                Label("Job \(submittedJobId)", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .accessibilityIdentifier("createBookSubmittedJobLabel")
                Button {
                    onOpenJobs(submittedJobId)
                } label: {
                    Label("Open Jobs", systemImage: "tray.full")
                }
                .accessibilityIdentifier("createBookOpenJobsButton")
            }
        }
    }

    private var submitSection: some View {
        Section {
            Button {
                submit()
            } label: {
                if viewModel.isSubmitting {
                    Label("Submitting", systemImage: "hourglass")
                } else {
                    Label("Generate Audiobook", systemImage: "sparkles")
                }
            }
            .disabled(!canSubmit || viewModel.isSubmitting)
            .accessibilityIdentifier("createBookSubmitButton")
        }
    }

    private var canSubmit: Bool {
        !trimmed(topic).isEmpty
            && !trimmed(bookName).isEmpty
            && !trimmed(genre).isEmpty
            && appState.configuration != nil
    }

    private var derivedBaseOutput: String {
        Self.deriveBaseOutputName(bookName.isEmpty ? topic : bookName)
    }

    private func submit() {
        let draft = AppleBookCreateDraft(
            topic: trimmed(topic),
            bookName: trimmed(bookName),
            genre: trimmed(genre),
            author: trimmed(author).nonEmptyValue ?? "Me",
            sentenceCount: sentenceCount,
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            voice: voice.backendValue,
            baseOutput: derivedBaseOutput,
            includeTransliteration: includeTransliteration,
            enableLookupCache: enableLookupCache
        )

        Task {
            if let jobId = await viewModel.submit(draft, using: appState) {
                onJobSubmitted(jobId)
            }
        }
    }

    private func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func deriveBaseOutputName(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let scalars = trimmed.unicodeScalars.map { scalar -> Character in
            CharacterSet.alphanumerics.contains(scalar) ? Character(scalar) : "-"
        }
        let collapsed = String(scalars)
            .split(separator: "-", omittingEmptySubsequences: true)
            .joined(separator: "-")
            .lowercased()
        return collapsed.nonEmptyValue ?? "generated-book"
    }
}

@MainActor
final class AppleBookCreateViewModel: ObservableObject {
    @Published private(set) var isSubmitting = false
    @Published var errorMessage: String?
    @Published private(set) var submittedJobId: String?

    func submit(_ draft: AppleBookCreateDraft, using appState: AppState) async -> String? {
        guard let configuration = appState.configuration else {
            errorMessage = "API configuration is unavailable."
            return nil
        }

        isSubmitting = true
        errorMessage = nil
        submittedJobId = nil
        defer { isSubmitting = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.submitBookGenerationJob(Self.makeSubmission(from: draft))
            submittedJobId = response.jobId
            return response.jobId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    private static func makeSubmission(from draft: AppleBookCreateDraft) -> BookGenerationJobSubmission {
        let inputFile = "\(draft.baseOutput).epub"
        let input = PipelineInputPayload(
            inputFile: inputFile,
            baseOutputFile: draft.baseOutput,
            inputLanguage: draft.inputLanguage,
            targetLanguages: [draft.targetLanguage],
            sentencesPerOutputFile: 10,
            startSentence: 1,
            generateAudio: true,
            audioMode: "4",
            audioBitrateKbps: 96,
            writtenMode: "4",
            selectedVoice: draft.voice,
            outputHtml: false,
            outputPdf: false,
            addImages: false,
            includeTransliteration: draft.includeTransliteration,
            translationProvider: "llm",
            translationBatchSize: 10,
            transliterationMode: "default",
            enableLookupCache: draft.enableLookupCache,
            lookupCacheBatchSize: 10,
            tempo: 1.0,
            bookMetadata: [
                "title": .string(draft.bookName),
                "book_title": .string(draft.bookName),
                "author": .string(draft.author),
                "genre": .string(draft.genre),
                "job_label": .string(draft.bookName),
                "source": .string("apple")
            ]
        )
        let pipeline = PipelineRequestPayload(inputs: input, correlationId: "apple-create")
        return BookGenerationJobSubmission(
            generator: BookGenerationRequest(
                topic: draft.topic,
                bookName: draft.bookName,
                genre: draft.genre,
                author: draft.author,
                numSentences: draft.sentenceCount,
                inputLanguage: draft.inputLanguage,
                outputLanguage: draft.targetLanguage,
                voice: draft.voice
            ),
            pipeline: pipeline
        )
    }
}

struct AppleBookCreateDraft: Equatable {
    let topic: String
    let bookName: String
    let genre: String
    let author: String
    let sentenceCount: Int
    let inputLanguage: String
    let targetLanguage: String
    let voice: String
    let baseOutput: String
    let includeTransliteration: Bool
    let enableLookupCache: Bool
}

enum AppleBookCreateLanguage: String, CaseIterable, Identifiable {
    case english = "English"
    case arabic = "Arabic"
    case slovak = "Slovak"
    case spanish = "Spanish"
    case french = "French"
    case german = "German"

    var id: String { rawValue }
    var backendValue: String { rawValue }

    var label: String {
        switch self {
        case .english: return "English"
        case .arabic: return "Arabic"
        case .slovak: return "Slovak"
        case .spanish: return "Spanish"
        case .french: return "French"
        case .german: return "German"
        }
    }
}

enum AppleBookCreateVoice: String, CaseIterable, Identifiable {
    case gtts = "gTTS"
    case macos = "macOS"
    case edge = "edge-tts"

    var id: String { rawValue }
    var backendValue: String { rawValue }

    var label: String {
        switch self {
        case .gtts: return "gTTS"
        case .macos: return "macOS"
        case .edge: return "Edge TTS"
        }
    }
}
