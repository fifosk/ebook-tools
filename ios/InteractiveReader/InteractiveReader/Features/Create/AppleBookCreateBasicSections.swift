import SwiftUI

struct AppleBookCreatePromptSection: View {
    @Binding var topic: String
    @Binding var bookName: String
    @Binding var genre: String
    @Binding var author: String

    var body: some View {
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
        }
    }
}

struct AppleBookCreateMetadataSection: View {
    let creationMode: AppleCreateMode
    @Binding var sourceBookTitle: String
    @Binding var sourceBookAuthor: String
    @Binding var sourceBookGenre: String
    @Binding var bookSummary: String
    @Binding var bookYear: String
    @Binding var bookIsbn: String
    @Binding var bookCoverFile: String

    var body: some View {
        Section(creationMode == .generatedBook ? "Source Book" : "Metadata") {
            if creationMode == .generatedBook || creationMode == .narrateEbook {
                TextField(
                    creationMode == .generatedBook ? "Source title" : "Title",
                    text: $sourceBookTitle
                )
                    .textInputAutocapitalization(.words)
                    .accessibilityIdentifier(
                        creationMode == .generatedBook
                            ? "createGeneratedSourceBookTitleField"
                            : "createNarrateBookTitleField"
                    )
                TextField(
                    creationMode == .generatedBook ? "Source author" : "Author",
                    text: $sourceBookAuthor
                )
                    .textInputAutocapitalization(.words)
                    .accessibilityIdentifier(
                        creationMode == .generatedBook
                            ? "createGeneratedSourceBookAuthorField"
                            : "createNarrateBookAuthorField"
                    )
                TextField(
                    creationMode == .generatedBook ? "Source genre" : "Genre",
                    text: $sourceBookGenre
                )
                    .textInputAutocapitalization(.words)
                    .accessibilityIdentifier(
                        creationMode == .generatedBook
                            ? "createGeneratedSourceBookGenreField"
                            : "createNarrateBookGenreField"
                    )
            }
            TextField(
                creationMode == .generatedBook ? "Source summary" : "Summary",
                text: $bookSummary,
                axis: .vertical
            )
                .lineLimit(2...5)
                .textInputAutocapitalization(.sentences)
                .accessibilityIdentifier("createBookSummaryField")
            TextField("Year", text: $bookYear)
                #if os(iOS)
                .keyboardType(.numberPad)
                #endif
                .accessibilityIdentifier("createBookYearField")
            TextField("ISBN", text: $bookIsbn)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createBookIsbnField")
            TextField("Cover file path", text: $bookCoverFile)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createBookCoverFileField")
        }
    }
}

struct AppleBookCreateJobTypeSection: View {
    @Binding var creationMode: AppleCreateMode
    let availableCreateModes: [AppleCreateMode]
    let showsInlineJobTypePicker: Bool

    var body: some View {
        if showsInlineJobTypePicker {
            Section("Job Type") {
                Picker("Job type", selection: $creationMode) {
                    ForEach(availableCreateModes) { mode in
                        Text(mode.label).tag(mode)
                    }
                }
                #if os(iOS)
                .pickerStyle(.segmented)
                #endif
                .accessibilityIdentifier("createJobTypePicker")
            }
        }
    }
}

struct AppleBookCreateJobSettingsSection: View {
    let creationMode: AppleCreateMode
    let sentenceBounds: BookCreationSentenceBounds
    @Binding var sentenceCount: Int
    @Binding var sourceBaseOutput: String
    @Binding var sourceStartSentence: String
    @Binding var sourceEndSentence: String
    let narrateSourcePath: String
    let narrateChapterOptions: [AppleCreateChapterOption]
    @Binding var selectedNarrateStartChapterID: String
    @Binding var selectedNarrateEndChapterID: String
    let isLoadingNarrateChapters: Bool
    let narrateChaptersErrorMessage: String?
    let onLoadNarrateChapters: () -> Void
    let onChapterRangeSelection: (_ startID: String, _ endID: String) -> Void

    var body: some View {
        if creationMode == .generatedBook {
            Section("Job Settings") {
                sentenceCountControl
            }
        } else if creationMode == .narrateEbook {
            Section("Job Settings") {
                TextField("Output path", text: $sourceBaseOutput)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("createNarrateOutputPathField")
                narrateChapterSettingsControls
                TextField("Start sentence", text: $sourceStartSentence)
                    #if os(iOS)
                    .keyboardType(.numberPad)
                    #endif
                    .accessibilityIdentifier("createNarrateStartSentenceField")
                TextField("End sentence", text: $sourceEndSentence)
                    #if os(iOS)
                    .keyboardType(.numbersAndPunctuation)
                    #endif
                    .accessibilityIdentifier("createNarrateEndSentenceField")
            }
        }
    }

    @ViewBuilder
    private var sentenceCountControl: some View {
        #if os(tvOS)
        AppleBookCreateDiscreteValueControl(
            value: $sentenceCount,
            clampedValue: sentenceCount,
            range: sentenceBounds.min...sentenceBounds.max,
            step: 5,
            title: "Sentences",
            decrementAccessibilityLabel: "Decrease sentences",
            incrementAccessibilityLabel: "Increase sentences"
        )
        .accessibilityIdentifier("createBookSentenceControl")
        #else
        Stepper(value: $sentenceCount, in: sentenceBounds.min...sentenceBounds.max, step: 5) {
            LabeledContent("Sentences", value: "\(sentenceCount)")
        }
        .accessibilityIdentifier("createBookSentenceStepper")
        #endif
    }

    @ViewBuilder
    private var narrateChapterSettingsControls: some View {
        Button(action: onLoadNarrateChapters) {
            Label(
                isLoadingNarrateChapters ? "Loading Chapters" : "Load Chapters",
                systemImage: "list.bullet.rectangle"
            )
        }
        .disabled(
            isLoadingNarrateChapters
                || narrateSourcePath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        )
        .accessibilityIdentifier("createNarrateLoadChaptersButton")

        if isLoadingNarrateChapters {
            ProgressView()
                .accessibilityIdentifier("createNarrateChaptersProgress")
        }

        if let narrateChaptersErrorMessage {
            Text(narrateChaptersErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createNarrateChaptersMessage")
        }

        if !narrateChapterOptions.isEmpty {
            Picker("Start chapter", selection: $selectedNarrateStartChapterID) {
                Text("Manual sentence range").tag("")
                ForEach(narrateChapterOptions) { chapter in
                    Text(chapter.pickerLabel).tag(chapter.id)
                }
            }
            .accessibilityIdentifier("createNarrateStartChapterPicker")
            .onChange(of: selectedNarrateStartChapterID) { _, newValue in
                onChapterRangeSelection(newValue, selectedNarrateEndChapterID)
            }

            if !selectedNarrateStartChapterID.isEmpty {
                Picker("End chapter", selection: $selectedNarrateEndChapterID) {
                    ForEach(narrateChapterOptions) { chapter in
                        Text(chapter.pickerLabel).tag(chapter.id)
                    }
                }
                .accessibilityIdentifier("createNarrateEndChapterPicker")
                .onChange(of: selectedNarrateEndChapterID) { _, newValue in
                    onChapterRangeSelection(selectedNarrateStartChapterID, newValue)
                }

                if let selection = AppleBookCreatePresentation.chapterRangeSelection(
                    chapters: narrateChapterOptions,
                    startChapterID: selectedNarrateStartChapterID,
                    endChapterID: selectedNarrateEndChapterID
                ) {
                    Text("\(selection.label) · \(selection.sentenceRangeLabel)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("createNarrateChapterRangeSummary")
                }
            }
        }
    }
}
