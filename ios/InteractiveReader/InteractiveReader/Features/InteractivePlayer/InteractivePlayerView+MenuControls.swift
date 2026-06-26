import SwiftUI

extension InteractivePlayerView {
    func menuLabel(_ text: String, leadingSystemImage: String? = nil) -> some View {
        HStack(spacing: 6) {
            if let leadingSystemImage {
                Image(systemName: leadingSystemImage)
                    .font(.caption2)
            }
            Text(text)
                .font(.callout)
                .lineLimit(1)
                .truncationMode(.tail)
                .minimumScaleFactor(0.85)
            Image(systemName: "chevron.down")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
    }

    var scopedChapterEntries: [ChapterNavigationEntry] {
        let chapters = viewModel.chapterEntries
        guard !chapters.isEmpty else { return [] }
        let bounds = jobSentenceBounds
        return chapters.filter { chapter in
            let end = effectiveChapterEnd(for: chapter, boundsEnd: bounds.end)
            if let startBound = bounds.start, end < startBound {
                return false
            }
            if let endBound = bounds.end, chapter.startSentence > endBound {
                return false
            }
            return true
        }
    }

    var selectedChapterRange: SentenceRange? {
        let chapters = scopedChapterEntries
        guard let chapter = activeChapter(in: chapters) else { return nil }
        return chapterRange(for: chapter, bounds: jobSentenceBounds)
    }

    var jobSentenceBounds: (start: Int?, end: Int?) {
        guard let context = viewModel.jobContext else { return (nil, nil) }
        var minValue: Int?
        var maxValue: Int?
        for chunk in context.chunks {
            if let start = chunk.startSentence {
                var end = chunk.endSentence ?? start
                if chunk.endSentence == nil {
                    let derivedEnd = chunk.sentences
                        .map { $0.displayIndex ?? $0.id }
                        .max() ?? start
                    end = max(end, derivedEnd)
                }
                minValue = min(minValue ?? start, start)
                maxValue = max(maxValue ?? end, end)
                continue
            }
            for sentence in chunk.sentences {
                let id = sentence.displayIndex ?? sentence.id
                guard id > 0 else { continue }
                minValue = min(minValue ?? id, id)
                maxValue = max(maxValue ?? id, id)
            }
        }
        return (minValue, maxValue)
    }

    func chapterBinding(entries: [ChapterNavigationEntry]) -> Binding<String> {
        Binding(
            get: {
                activeChapter(in: entries)?.id ?? entries.first?.id ?? ""
            },
            set: { selectChapter($0, from: entries) }
        )
    }

    func chapterLabel(_ chapter: ChapterNavigationEntry, index: Int) -> String {
        let title = chapter.title.nonEmptyValue ?? "Chapter \(index + 1)"
        let range = chapterRangeLabel(for: chapter)
        if range.isEmpty {
            return title
        }
        return "\(title) • \(range)"
    }

    func chapterRangeLabel(for chapter: ChapterNavigationEntry) -> String {
        if let end = chapter.endSentence {
            if end > chapter.startSentence {
                return "\(chapter.startSentence)-\(end)"
            }
            return "\(chapter.startSentence)"
        }
        return "\(chapter.startSentence)+"
    }

    func activeChapter(in chapters: [ChapterNavigationEntry]) -> ChapterNavigationEntry? {
        guard !chapters.isEmpty else { return nil }
        guard let sentenceID = selectedSentenceID else { return chapters.first }
        let boundsEnd = jobSentenceBounds.end
        for chapter in chapters {
            let end = effectiveChapterEnd(for: chapter, boundsEnd: boundsEnd)
            if sentenceID >= chapter.startSentence && sentenceID <= end {
                return chapter
            }
        }
        return chapters.first
    }

    func chapterRange(
        for chapter: ChapterNavigationEntry,
        bounds: (start: Int?, end: Int?)
    ) -> SentenceRange? {
        let effectiveEnd = effectiveChapterEnd(for: chapter, boundsEnd: bounds.end)
        let start = max(chapter.startSentence, bounds.start ?? chapter.startSentence)
        let end = min(effectiveEnd, bounds.end ?? effectiveEnd)
        guard end >= start else { return nil }
        return SentenceRange(start: start, end: end)
    }

    func effectiveChapterEnd(for chapter: ChapterNavigationEntry, boundsEnd: Int?) -> Int {
        if let end = chapter.endSentence {
            return max(end, chapter.startSentence)
        }
        if let boundsEnd {
            return max(boundsEnd, chapter.startSentence)
        }
        return chapter.startSentence
    }

    @ViewBuilder
    func chapterPicker() -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Chapter")
                .font(.caption)
                .foregroundStyle(.secondary)
            let chapters = scopedChapterEntries
            if chapters.isEmpty {
                Picker("Chapter", selection: viewModel.chunkBinding()) {
                    let chunks = viewModel.jobContext?.chunks ?? []
                    ForEach(Array(chunks.enumerated()), id: \.element.id) { index, chunk in
                        Text("Chapter \(index + 1)").tag(chunk.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
            } else {
                Picker("Chapter", selection: chapterBinding(entries: chapters)) {
                    ForEach(Array(chapters.enumerated()), id: \.element.id) { index, chapter in
                        Text(chapterLabel(chapter, index: index)).tag(chapter.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    @ViewBuilder
    func sentencePicker(for chunk: InteractiveChunk) -> some View {
        let chapterRange = selectedChapterRange
        let entries = sentenceEntries(for: chunk, chapterRange: chapterRange)
        VStack(alignment: .leading, spacing: 4) {
            Text("Sentence")
                .font(.caption)
                .foregroundStyle(.secondary)
            if entries.isEmpty {
                Text("No sentences")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                Picker("Sentence", selection: sentenceBinding(entries: entries, chunk: chunk, chapterRange: chapterRange)) {
                    ForEach(entries) { entry in
                        Text(entry.label).tag(entry.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    @ViewBuilder
    func textTrackPicker(for chunk: InteractiveChunk) -> some View {
        let available = availableTracks(for: chunk)
        let showImageToggle = hasImageReel(for: chunk) && showImageReel != nil
        VStack(alignment: .leading, spacing: 4) {
            Text("Text")
                .font(.caption)
                .foregroundStyle(.secondary)
            Menu {
                ForEach(available, id: \.self) { kind in
                    trackToggle(label: trackLabel(kind), kind: kind)
                }
                if showImageToggle {
                    imageReelToggle()
                }
            } label: {
                menuLabel(textTrackSummary(for: chunk))
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    @ViewBuilder
    func audioPicker(for chunk: InteractiveChunk) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Audio")
                .font(.caption)
                .foregroundStyle(.secondary)
            if !chunk.audioOptions.isEmpty {
                #if os(tvOS)
                Menu {
                    ForEach(chunk.audioOptions) { option in
                        audioTrackButton(option)
                    }
                } label: {
                    menuLabel(selectedAudioLabel(for: chunk))
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused($focusedArea, equals: .controls)
                #else
                Picker("Audio track", selection: viewModel.audioTrackBinding(defaultID: chunk.audioOptions.first?.id)) {
                    ForEach(chunk.audioOptions) { option in
                        Text(option.label).tag(option.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
                #endif
            } else {
                Text("No audio")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    func selectedAudioLabel(for chunk: InteractiveChunk) -> String {
        guard let selectedID = viewModel.selectedAudioTrackID else {
            return chunk.audioOptions.first?.label ?? "Audio Mode"
        }
        return chunk.audioOptions.first(where: { $0.id == selectedID })?.label ?? "Audio Mode"
    }

    @ViewBuilder
    func speedPicker() -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Speed")
                .font(.caption)
                .foregroundStyle(.secondary)
            Menu {
                ForEach(playbackRates, id: \.self) { rate in
                    playbackRateButton(rate)
                }
            } label: {
                menuLabel(playbackRateLabel(audioCoordinator.playbackRate))
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    private var showReadingBedPicker: Bool {
        viewModel.readingBedURL != nil
    }

    @ViewBuilder
    func readingBedPicker() -> some View {
        if showReadingBedPicker {
            let bedLabel = selectedReadingBedLabel
            VStack(alignment: .leading, spacing: 4) {
                Text("Reading Bed")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Menu {
                    Button(action: toggleReadingBed) {
                        if readingBedEnabled {
                            Label("Music On", systemImage: "checkmark")
                        } else {
                            Text("Music Off")
                        }
                    }
                    Divider()
                    // Built-in reading bed options
                    defaultReadingBedButton()
                    ForEach(viewModel.readingBedCatalog?.beds ?? []) { bed in
                        readingBedButton(bed)
                    }
                } label: {
                    menuLabel(
                        readingBedSummary(label: bedLabel),
                        leadingSystemImage: readingBedEnabled ? "music.note.list" : "music.note"
                    )
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    @ViewBuilder
    func settingsMenu() -> some View {
        let hasVoiceOverrides = !TtsVoicePreferencesManager.shared.allVoices().isEmpty
        VStack(alignment: .leading, spacing: 4) {
            Text("Settings")
                .font(.caption)
                .foregroundStyle(.secondary)
            Menu {
                if hasVoiceOverrides {
                    resetVoiceSettingsButton()
                    Text("Clears custom TTS voice selections for all languages")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                } else {
                    Text("No custom voice settings")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            } label: {
                menuLabel("Settings", leadingSystemImage: "gearshape")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    func audioTrackButton(_ option: InteractiveChunk.AudioOption) -> some View {
        Button(option.label) {
            selectAudioTrack(option)
        }
    }

    func playbackRateButton(_ rate: Double) -> some View {
        Button {
            selectPlaybackRate(rate)
        } label: {
            playbackRateMenuLabel(rate)
        }
    }

    @ViewBuilder
    func playbackRateMenuLabel(_ rate: Double) -> some View {
        if isCurrentRate(rate) {
            Label(playbackRateLabel(rate), systemImage: "checkmark")
        } else {
            Text(playbackRateLabel(rate))
        }
    }

    func defaultReadingBedButton() -> some View {
        Button {
            selectDefaultReadingBed()
        } label: {
            if !useAppleMusicForBed && viewModel.selectedReadingBedID == nil {
                Label("Default", systemImage: "checkmark")
            } else {
                Text("Default")
            }
        }
    }

    func readingBedButton(_ bed: ReadingBedEntry) -> some View {
        Button {
            selectReadingBed(bed)
        } label: {
            if !useAppleMusicForBed && bed.id == viewModel.selectedReadingBedID {
                Label(readingBedMenuLabel(for: bed), systemImage: "checkmark")
            } else {
                Text(readingBedMenuLabel(for: bed))
            }
        }
    }

    func readingBedMenuLabel(for bed: ReadingBedEntry) -> String {
        bed.label.isEmpty ? bed.id : bed.label
    }

    func resetVoiceSettingsButton() -> some View {
        Button(role: .destructive, action: resetVoiceSettings) {
            Label("Reset Voice Settings", systemImage: "speaker.wave.2.circle")
        }
    }

    func seekPlayback(to target: TimeInterval, in chunk: InteractiveChunk) {
        viewModel.seekPlayback(to: target, in: chunk)
    }

    #if os(tvOS)
    func decreaseTrackFontScale() {
        adjustTrackFontScale(by: -trackFontScaleStep)
    }

    func increaseTrackFontScale() {
        adjustTrackFontScale(by: trackFontScaleStep)
    }
    #endif

    func selectChapter(_ chapterID: String, from entries: [ChapterNavigationEntry]) {
        guard let target = entries.first(where: { $0.id == chapterID }) else { return }
        prepareExplicitSentenceJump(to: target.startSentence)
        viewModel.jumpToSentence(target.startSentence, autoPlay: audioCoordinator.isPlaying)
    }

    func selectAudioTrack(_ option: InteractiveChunk.AudioOption) {
        viewModel.selectAudioTrack(id: option.id)
    }

    func selectPlaybackRate(_ rate: Double) {
        audioCoordinator.setPlaybackRate(rate)
    }

    func selectDefaultReadingBed() {
        if useAppleMusicForBed { switchToBuiltInBed() }
        viewModel.selectReadingBed(id: nil)
    }

    func selectReadingBed(_ bed: ReadingBedEntry) {
        if useAppleMusicForBed { switchToBuiltInBed() }
        viewModel.selectReadingBed(id: bed.id)
    }

    func resetVoiceSettings() {
        TtsVoicePreferencesManager.shared.clearAllVoices()
        storedTtsVoice = ""
    }
}
