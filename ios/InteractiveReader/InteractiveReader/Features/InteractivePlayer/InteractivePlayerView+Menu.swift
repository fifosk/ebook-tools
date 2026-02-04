import SwiftUI

extension InteractivePlayerView {
    var menuDragHandle: some View {
        #if os(tvOS)
        EmptyView()
        #else
        Capsule()
            .fill(Color.white.opacity(0.25))
            .frame(width: 36, height: 4)
            .frame(maxWidth: .infinity)
            .padding(.top, 2)
            .contentShape(Rectangle())
        #endif
    }

    func menuHeader(info: InteractivePlayerHeaderInfo, reelURLs: [URL]) -> some View {
        HStack(alignment: .top, spacing: 12) {
            if let coverURL = info.coverURL {
                AsyncImage(url: coverURL) { phase in
                    if let image = phase.image {
                        image.resizable().scaledToFill()
                    } else {
                        Color.gray.opacity(0.2)
                    }
                }
                .frame(width: menuCoverWidth, height: menuCoverHeight)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                )
            }
            VStack(alignment: .leading, spacing: 6) {
                Text(info.title.isEmpty ? "Untitled" : info.title)
                    .font(menuTitleFont)
                    .lineLimit(2)
                    .minimumScaleFactor(0.85)
                Text(info.author.isEmpty ? "Unknown author" : info.author)
                    .font(menuAuthorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)
                Text(info.itemTypeLabel)
                    .font(menuMetaFont)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.2), in: Capsule())
            }
            if !reelURLs.isEmpty {
                Spacer(minLength: 12)
                InteractivePlayerImageReel(urls: reelURLs, height: menuCoverHeight)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }

    var menuCoverWidth: CGFloat {
        #if os(tvOS)
        return 96
        #else
        return 64
        #endif
    }

    var menuCoverHeight: CGFloat {
        #if os(tvOS)
        return 144
        #else
        return 96
        #endif
    }

    var menuTitleFont: Font {
        #if os(tvOS)
        return .title2
        #else
        return .title3
        #endif
    }

    var menuAuthorFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .callout
        #endif
    }

    var menuMetaFont: Font {
        #if os(tvOS)
        return .caption2
        #else
        return .caption
        #endif
    }

    @ViewBuilder
    var menuBackground: some View {
        #if os(tvOS)
        Color.black.opacity(0.78)
        #else
        Rectangle()
            .fill(.ultraThinMaterial)
        #endif
    }

    func imageReelURLs(for chunk: InteractiveChunk) -> [URL] {
        guard let showImageReel, showImageReel.wrappedValue else { return [] }
        guard hasImageReel(for: chunk) else { return [] }
        var urls: [URL] = []
        var seen: Set<String> = []
        for sentence in chunk.sentences {
            guard let path = resolveSentenceImagePath(sentence: sentence, chunk: chunk) else { continue }
            guard !seen.contains(path) else { continue }
            seen.insert(path)
            if let url = viewModel.resolvePath(path) {
                urls.append(url)
            }
            if urls.count >= 7 {
                break
            }
        }
        return urls
    }

    func resolveSentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String? {
        if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue {
            return path
        }
        guard let rangeFragment = chunk.rangeFragment?.nonEmptyValue else { return nil }
        let sentenceNumber = sentence.displayIndex ?? sentence.id
        guard sentenceNumber > 0 else { return nil }
        let padded = String(format: "%05d", sentenceNumber)
        return "media/images/\(rangeFragment)/sentence_\(padded).png"
    }

    @ViewBuilder
    func controlBar(_ chunk: InteractiveChunk) -> some View {
        let playbackTime = viewModel.playbackTime(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .center, spacing: 12) {
                chapterPicker()
                sentencePicker(for: chunk)
                textTrackPicker(for: chunk)
                audioPicker(for: chunk)
                readingBedPicker()
                speedPicker()
                settingsMenu()
                bookmarkMenu(for: chunk)
                #if os(tvOS)
                trackFontControls
                #endif
            }
            #if os(tvOS)
            .transaction { transaction in
                transaction.disablesAnimations = true
            }
            #endif
            if let range = chunk.rangeDescription {
                Text(range)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            if showsScrubber {
                PlaybackScrubberView(
                    coordinator: audioCoordinator,
                    currentTime: playbackTime,
                    duration: playbackDuration,
                    scrubbedTime: $scrubbedTime,
                    onSeek: { target in
                        viewModel.seekPlayback(to: target, in: chunk)
                    }
                )
            }
        }
    }

    #if os(tvOS)
    var trackFontControls: some View {
        let canDecrease = trackFontScale > trackFontScaleMin + 0.001
        let canIncrease = trackFontScale < trackFontScaleMax - 0.001
        return VStack(alignment: .leading, spacing: 4) {
            Text("Text Size")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 6) {
                Button(action: { adjustTrackFontScale(by: -trackFontScaleStep) }) {
                    Text("A-")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 4)
                        .background(.black.opacity(0.3), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(!canDecrease)
                .focused($focusedArea, equals: .controls)

                Button(action: { adjustTrackFontScale(by: trackFontScaleStep) }) {
                    Text("A+")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 4)
                        .background(.black.opacity(0.3), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(!canIncrease)
                .focused($focusedArea, equals: .controls)
            }
        }
    }
    #endif

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
            set: { newValue in
                guard let target = entries.first(where: { $0.id == newValue }) else { return }
                selectedSentenceID = target.startSentence
                viewModel.jumpToSentence(target.startSentence, autoPlay: audioCoordinator.isPlaying)
            }
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
                        Button(option.label) {
                            viewModel.selectAudioTrack(id: option.id)
                        }
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
                    Button {
                        audioCoordinator.setPlaybackRate(rate)
                    } label: {
                        if isCurrentRate(rate) {
                            Label(playbackRateLabel(rate), systemImage: "checkmark")
                        } else {
                            Text(playbackRateLabel(rate))
                        }
                    }
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
                    Button {
                        if useAppleMusicForBed { switchToBuiltInBed() }
                        viewModel.selectReadingBed(id: nil)
                    } label: {
                        if !useAppleMusicForBed && viewModel.selectedReadingBedID == nil {
                            Label("Default", systemImage: "checkmark")
                        } else {
                            Text("Default")
                        }
                    }
                    ForEach(viewModel.readingBedCatalog?.beds ?? []) { bed in
                        let label = bed.label.isEmpty ? bed.id : bed.label
                        Button {
                            if useAppleMusicForBed { switchToBuiltInBed() }
                            viewModel.selectReadingBed(id: bed.id)
                        } label: {
                            if !useAppleMusicForBed && bed.id == viewModel.selectedReadingBedID {
                                Label(label, systemImage: "checkmark")
                            } else {
                                Text(label)
                            }
                        }
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
                    Button(role: .destructive) {
                        TtsVoicePreferencesManager.shared.clearAllVoices()
                        // Also clear the legacy stored voice
                        storedTtsVoice = ""
                    } label: {
                        Label("Reset Voice Settings", systemImage: "speaker.wave.2.circle")
                    }
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
}
