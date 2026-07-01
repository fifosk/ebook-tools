import Darwin
import Foundation

enum SequenceTrack: String {
    case original
    case translation
}

enum TextPlayerTimingTrack: Equatable {
    case mix
    case translation
    case original
}

enum TextPlayerVariantKind: String, Hashable {
    case original
    case translation
    case transliteration
}

@MainActor
final class SequencePlaybackController {
    var isEnabled: Bool
    var currentSentenceIndex: Int?

    init(isEnabled: Bool = false, currentSentenceIndex: Int? = nil) {
        self.isEnabled = isEnabled
        self.currentSentenceIndex = currentSentenceIndex
    }
}

struct InteractiveChunk: Identifiable {
    struct Sentence: Identifiable {
        let id: Int
        let displayIndex: Int?
        let startGate: Double?
        let originalStartGate: Double?

        init(
            id: Int,
            displayIndex: Int?,
            startGate: Double? = nil,
            originalStartGate: Double? = nil
        ) {
            self.id = id
            self.displayIndex = displayIndex
            self.startGate = startGate
            self.originalStartGate = originalStartGate
        }
    }

    struct AudioOption: Identifiable {
        enum Kind: String {
            case combined
            case translation
            case original
            case other
        }

        let id: String
        let label: String
        let kind: Kind
        let streamURLs: [URL]
        let timingURL: URL?
        let duration: Double?
        let fileDurations: [Double]?

        var primaryURL: URL {
            streamURLs[0]
        }
    }

    let id: String
    let startSentence: Int?
    let sentences: [Sentence]
    let audioOptions: [AudioOption]
}

struct PendingSentenceJump {
    let chunkID: String
    let sentenceNumber: Int
}

struct RecentSingleTrackSentenceAnchor: Equatable {
    let chunkID: String
    let sentenceNumber: Int
}

enum SingleTrackNavigationTarget: Equatable, CustomStringConvertible {
    case sentence(chunkID: String, localIndex: Int, startTime: Double)
    case chunkStart(chunkID: String)
    case chunkEnd(chunkID: String)

    var description: String {
        switch self {
        case .sentence(let chunkID, let localIndex, let startTime):
            return "sentence(\(chunkID), \(localIndex), \(startTime))"
        case .chunkStart(let chunkID):
            return "chunkStart(\(chunkID))"
        case .chunkEnd(let chunkID):
            return "chunkEnd(\(chunkID))"
        }
    }
}

@MainActor
private func fail(_ message: String) -> Never {
    fputs("Playback mode switch integration check failed: \(message)\n", stderr)
    exit(1)
}

@MainActor
private func requireEqual<T: Equatable>(_ actual: T, _ expected: T, _ message: String) {
    if actual != expected {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

@MainActor
private func requireNil<T>(_ actual: T?, _ message: String) {
    if actual != nil {
        fail("\(message). Expected nil.")
    }
}

@MainActor
private func requireInstruction(
    _ instruction: ResolvedAudioInstruction?,
    optionID expectedID: String,
    timing expectedTiming: TextPlayerTimingTrack,
    _ message: String
) {
    guard case .singleOption(let option, let timing)? = instruction else {
        fail("\(message). Expected single option instruction.")
    }
    requireEqual(option.id, expectedID, "\(message) option id")
    requireEqual(timing, expectedTiming, "\(message) timing")
}

@MainActor
private func requireSequenceInstruction(
    _ instruction: ResolvedAudioInstruction?,
    optionID expectedID: String,
    _ message: String
) {
    guard case .sequence(let option)? = instruction else {
        fail("\(message). Expected sequence instruction.")
    }
    requireEqual(option.id, expectedID, "\(message) option id")
}

@MainActor
private func requireSingleURLInstruction(
    _ instruction: ResolvedAudioInstruction?,
    url expectedURL: URL,
    timing expectedTiming: TextPlayerTimingTrack,
    _ message: String
) {
    guard case .singleURL(let url, let timing)? = instruction else {
        fail("\(message). Expected single URL instruction.")
    }
    requireEqual(url, expectedURL, "\(message) URL")
    requireEqual(timing, expectedTiming, "\(message) timing")
}

private func audioOption(
    _ id: String,
    kind: InteractiveChunk.AudioOption.Kind,
    urls: [URL]
) -> InteractiveChunk.AudioOption {
    InteractiveChunk.AudioOption(
        id: id,
        label: id,
        kind: kind,
        streamURLs: urls,
        timingURL: nil,
        duration: nil,
        fileDurations: nil
    )
}

private func activeSentenceIndex(
    in chunk: InteractiveChunk,
    at time: Double,
    track: SequenceTrack
) -> Int? {
    for (index, sentence) in chunk.sentences.enumerated() {
        let start = track == .translation ? sentence.startGate : sentence.originalStartGate
        let nextStart: Double? = {
            let nextIndex = index + 1
            guard chunk.sentences.indices.contains(nextIndex) else { return nil }
            let next = chunk.sentences[nextIndex]
            return track == .translation ? next.startGate : next.originalStartGate
        }()
        guard let start else { continue }
        if let nextStart {
            if time >= start && time < nextStart {
                return index
            }
        } else if time >= start {
            return index
        }
    }
    return nil
}

private func startTime(
    in chunk: InteractiveChunk,
    at index: Int,
    track: SequenceTrack
) -> Double? {
    guard chunk.sentences.indices.contains(index) else { return nil }
    let sentence = chunk.sentences[index]
    return track == .translation ? sentence.startGate : sentence.originalStartGate
}

@MainActor
private func singleTrackNavigationTarget(
    chunks: [InteractiveChunk],
    currentChunkID: String,
    currentTime: Double,
    track: SequenceTrack,
    forward: Bool,
    anchorSentenceNumber: Int? = nil
) -> SingleTrackNavigationTarget? {
    guard let chunkIndex = chunks.firstIndex(where: { $0.id == currentChunkID }) else { return nil }
    let chunk = chunks[chunkIndex]
    let activeIndex = anchorSentenceNumber.flatMap { sentenceNumber in
        SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber)
    } ?? activeSentenceIndex(in: chunk, at: currentTime, track: track)

    guard let activeIndex else { return nil }
    let targetIndex = forward ? activeIndex + 1 : activeIndex - 1
    if chunk.sentences.indices.contains(targetIndex),
       let start = startTime(in: chunk, at: targetIndex, track: track) {
        return .sentence(chunkID: chunk.id, localIndex: targetIndex, startTime: start)
    }
    if forward {
        let nextIndex = chunkIndex + 1
        guard chunks.indices.contains(nextIndex) else { return nil }
        return .chunkStart(chunkID: chunks[nextIndex].id)
    }
    let previousIndex = chunkIndex - 1
    guard chunks.indices.contains(previousIndex) else { return nil }
    return .chunkEnd(chunkID: chunks[previousIndex].id)
}

@MainActor
private func singleTrackTimeSeekAnchor(
    time: Double,
    sentenceNumber: Int?,
    in chunk: InteractiveChunk,
    activeTimingTrack: TextPlayerTimingTrack
) -> Int? {
    if let sentenceNumber,
       SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) != nil {
        return sentenceNumber
    }
    return SentencePositionProvider.sentenceNumber(
        in: chunk,
        atTime: time,
        activeTimingTrack: activeTimingTrack
    )
}

@MainActor
private func recentSingleTrackAnchorDisplaySentence(
    anchor: inout RecentSingleTrackSentenceAnchor?,
    in chunk: InteractiveChunk,
    highlightingTime: Double,
    currentChunkAudioIsActive: Bool,
    track: SequenceTrack
) -> Int? {
    guard let currentAnchor = anchor, currentAnchor.chunkID == chunk.id else { return nil }
    guard currentChunkAudioIsActive else { return currentAnchor.sentenceNumber }
    guard let targetIndex = SentencePositionProvider.sentenceIndex(
        in: chunk,
        matching: currentAnchor.sentenceNumber
    ),
    let start = startTime(in: chunk, at: targetIndex, track: track) else {
        return currentAnchor.sentenceNumber
    }
    let tolerance = 0.18
    if chunk.sentences.indices.contains(targetIndex + 1),
       let nextStart = startTime(in: chunk, at: targetIndex + 1, track: track),
       nextStart > start {
        if highlightingTime >= start - tolerance && highlightingTime < nextStart + tolerance {
            anchor = nil
            return nil
        }
        return currentAnchor.sentenceNumber
    }
    if highlightingTime >= start - tolerance && highlightingTime <= start + 2.5 {
        anchor = nil
        return nil
    }
    return currentAnchor.sentenceNumber
}

@MainActor
private func singleTrackSentenceNumber(in chunk: InteractiveChunk, targetIndex: Int) -> Int? {
    if targetIndex >= 0,
       chunk.sentences.indices.contains(targetIndex) {
        return SentencePositionProvider.sentenceNumber(in: chunk, at: targetIndex)
    }
    if targetIndex < 0 {
        if !chunk.sentences.isEmpty {
            return SentencePositionProvider.sentenceNumber(
                in: chunk,
                at: max(0, chunk.sentences.count - 1)
            )
        }
        return chunk.startSentence
    }
    guard let start = chunk.startSentence else { return nil }
    return start + targetIndex
}

@MainActor
private func rememberSingleTrackBatchStartAnchorIfNeeded(
    for chunk: InteractiveChunk,
    targetSentenceIndex: Int?,
    autoPlay: Bool,
    isPlaybackRequested: Bool,
    manager: AudioModeManager,
    anchor: inout RecentSingleTrackSentenceAnchor?
) {
    guard !manager.isSequenceMode else { return }
    let inferredTargetIndex: Int? = {
        if let targetSentenceIndex {
            return targetSentenceIndex
        }
        if autoPlay || isPlaybackRequested {
            return 0
        }
        return nil
    }()
    guard let targetIndex = inferredTargetIndex,
          let sentenceNumber = singleTrackSentenceNumber(in: chunk, targetIndex: targetIndex) else {
        return
    }
    anchor = .init(chunkID: chunk.id, sentenceNumber: sentenceNumber)
}

@MainActor
private func usesCombinedQueue(
    isSequenceModeActive: Bool,
    audioModeManager: AudioModeManager?,
    selectedOption: InteractiveChunk.AudioOption?
) -> Bool {
    if isSequenceModeActive {
        return true
    }
    if let audioModeManager, !audioModeManager.isSequenceMode {
        return false
    }
    guard let selectedOption else { return false }
    return selectedOption.kind == .combined && selectedOption.streamURLs.count > 1
}

@MainActor
private func prepareResumeSingleTrack(
    _ track: SequenceTrack?,
    manager: AudioModeManager,
    pendingResumeTrack: inout SequenceTrack?
) {
    pendingResumeTrack = track
    guard let track else { return }
    manager.setTracks(
        original: track == .original,
        translation: track == .translation
    )
}

@MainActor
private func applyPendingResumeSingleTrackIfNeeded(
    for chunk: InteractiveChunk,
    availableTracks: Set<TextPlayerVariantKind>,
    manager: AudioModeManager,
    pendingResumeTrack: inout SequenceTrack?,
    visibleTracks: inout Set<TextPlayerVariantKind>,
    selectedAudioTrackID: inout String?
) -> Bool {
    guard let resumeTrack = pendingResumeTrack else { return false }
    pendingResumeTrack = nil

    let desiredTextTrack: TextPlayerVariantKind = resumeTrack == .original ? .original : .translation
    guard availableTracks.contains(desiredTextTrack) || chunkSupportsAudioTrack(resumeTrack, in: chunk) else { return false }

    visibleTracks = [desiredTextTrack]
    manager.setTracks(
        original: resumeTrack == .original,
        translation: resumeTrack == .translation
    )
    selectedAudioTrackID = manager.resolvePreferredTrackID(for: chunk)
    return true
}

@MainActor
private func preserveSingleTrackModeIfNeeded(
    for chunk: InteractiveChunk,
    availableTracks: Set<TextPlayerVariantKind>,
    manager: AudioModeManager,
    visibleTracks: inout Set<TextPlayerVariantKind>,
    hasCustomTrackSelection: inout Bool,
    selectedAudioTrackID: inout String?
) -> Bool {
    guard case .singleTrack(let track) = manager.currentMode else { return false }

    let desiredTextTrack: TextPlayerVariantKind = track == .original ? .original : .translation
    guard availableTracks.contains(desiredTextTrack) || chunkSupportsAudioTrack(track, in: chunk) else { return false }

    visibleTracks = [desiredTextTrack]
    hasCustomTrackSelection = true
    manager.setTracks(
        original: track == .original,
        translation: track == .translation
    )
    selectedAudioTrackID = manager.resolvePreferredTrackID(for: chunk)
    return true
}

private func chunkSupportsAudioTrack(_ track: SequenceTrack, in chunk: InteractiveChunk) -> Bool {
    let dedicatedKind: InteractiveChunk.AudioOption.Kind = track == .original ? .original : .translation
    if chunk.audioOptions.contains(where: { $0.kind == dedicatedKind }) {
        return true
    }
    return chunk.audioOptions.contains { option in
        guard option.kind == .combined else { return false }
        return !option.streamURLs.isEmpty
    }
}

@MainActor
private func synchronizeSelectedAudioTrackWithCurrentMode(
    for chunk: InteractiveChunk,
    manager: AudioModeManager,
    selectedAudioTrackID: inout String?,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?,
    sequenceAudioMode: inout AudioMode
) {
    guard let targetID = manager.resolvePreferredTrackID(for: chunk),
          let targetOption = chunk.audioOptions.first(where: { $0.id == targetID }) else {
        return
    }
    selectedAudioTrackID = targetID
    switch manager.currentMode {
    case .sequence:
        preferredAudioKind = targetOption.kind == .combined ? .combined : targetOption.kind
    case .singleTrack(.original):
        preferredAudioKind = .original
    case .singleTrack(.translation):
        preferredAudioKind = .translation
    }
    sequenceAudioMode = manager.currentMode
}

@MainActor
private func requestedSingleTrackMode(
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?
) -> SequenceTrack? {
    if let manager {
        if case .singleTrack(let track) = manager.currentMode {
            return track
        }
        return nil
    }
    if case .singleTrack(let track) = sequenceAudioMode {
        return track
    }
    switch preferredAudioKind {
    case .original:
        return .original
    case .translation:
        return .translation
    case .combined, .other, .none:
        return nil
    }
}

@MainActor
private func applySingleTrackSelection(
    _ track: SequenceTrack,
    for chunk: InteractiveChunk,
    manager: AudioModeManager?,
    sequenceAudioMode: inout AudioMode,
    selectedAudioTrackID: inout String?,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?
) {
    if let manager {
        manager.setTracks(
            original: track == .original,
            translation: track == .translation
        )
        sequenceAudioMode = manager.currentMode
        synchronizeSelectedAudioTrackWithCurrentMode(
            for: chunk,
            manager: manager,
            selectedAudioTrackID: &selectedAudioTrackID,
            preferredAudioKind: &preferredAudioKind,
            sequenceAudioMode: &sequenceAudioMode
        )
        if chunk.audioOptions.contains(where: { $0.id == selectedAudioTrackID }) {
            return
        }
    } else {
        sequenceAudioMode = .singleTrack(track)
    }

    preferredAudioKind = track == .original ? .original : .translation
    selectedAudioTrackID = preferredSingleTrackAudioOption(for: track, in: chunk)?.id
}

private func preferredSingleTrackAudioOption(
    for track: SequenceTrack,
    in chunk: InteractiveChunk
) -> InteractiveChunk.AudioOption? {
    let dedicatedKind: InteractiveChunk.AudioOption.Kind = track == .original ? .original : .translation
    if let dedicated = chunk.audioOptions.first(where: { $0.kind == dedicatedKind }) {
        return dedicated
    }
    if let combined = chunk.audioOptions.first(where: { $0.kind == .combined }) {
        return combined
    }
    return chunk.audioOptions.first
}

@MainActor
private func isSequenceModeActive(
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    selectedAudioTrackID: String?,
    chunk: InteractiveChunk,
    sequenceEnabled: Bool
) -> Bool {
    guard manager?.isSequenceMode != false else {
        return false
    }
    if case .singleTrack = sequenceAudioMode {
        return false
    }
    guard let selectedAudioTrackID,
          let track = chunk.audioOptions.first(where: { $0.id == selectedAudioTrackID }) else {
        return false
    }
    return track.kind == .combined && sequenceEnabled
}

@MainActor
private func effectiveSelectedAudioOption(
    for chunk: InteractiveChunk,
    manager: AudioModeManager,
    selectedAudioTrackID: String?
) -> InteractiveChunk.AudioOption? {
    if case .singleTrack = manager.currentMode,
       let targetID = manager.resolvePreferredTrackID(for: chunk),
       let target = chunk.audioOptions.first(where: { $0.id == targetID }) {
        return target
    }
    guard let selectedAudioTrackID else {
        return chunk.audioOptions.first
    }
    return chunk.audioOptions.first(where: { $0.id == selectedAudioTrackID }) ?? chunk.audioOptions.first
}

@MainActor
private func effectiveSelectedAudioKind(
    for chunk: InteractiveChunk,
    manager: AudioModeManager,
    selectedAudioTrackID: String?
) -> InteractiveChunk.AudioOption.Kind? {
    switch manager.currentMode {
    case .singleTrack(.original):
        if chunkSupportsAudioTrack(.original, in: chunk) {
            return .original
        }
    case .singleTrack(.translation):
        if chunkSupportsAudioTrack(.translation, in: chunk) {
            return .translation
        }
    case .sequence:
        break
    }
    guard let option = effectiveSelectedAudioOption(
        for: chunk,
        manager: manager,
        selectedAudioTrackID: selectedAudioTrackID
    ) else {
        return nil
    }
    if option.kind == .combined {
        return manager.currentMode == .sequence ? .combined : nil
    }
    return option.kind
}

@MainActor
private func runChecks() {
    let originalURL = URL(string: "https://example.invalid/original.m4a")!
    let translationURL = URL(string: "https://example.invalid/translation.m4a")!
    let chunk = InteractiveChunk(
        id: "chapter-1",
        startSentence: nil,
        sentences: [
            .init(id: 0, displayIndex: 100),
            .init(id: 1, displayIndex: nil),
            .init(id: 2, displayIndex: 102),
            .init(id: 3, displayIndex: 103)
        ],
        audioOptions: [
            audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
            audioOption("original", kind: .original, urls: [originalURL]),
            audioOption("translation", kind: .translation, urls: [translationURL])
        ]
    )

    let sequenceController = SequencePlaybackController(isEnabled: true, currentSentenceIndex: 14)
    let manager = AudioModeManager()
    var modeEvents: [(AudioMode, Int?)] = []
    manager.onModeChange = { mode, sentenceIndex in
        modeEvents.append((mode, sentenceIndex))
    }

    let sequenceProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { 6 },
        timeBasedIndex: { 5 }
    )
    manager.toggle(.original, preservingPosition: sequenceProvider.index)
    requireEqual(modeEvents.count, 1, "Track toggle should emit one mode event")
    requireEqual(modeEvents[0].0, .singleTrack(.translation), "Original toggle should switch to translation-only")
    requireEqual(modeEvents[0].1, 14, "Sequence-controller position should be preserved")
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "translation", "Translation-only mode should prefer translation")
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "translation",
        timing: .translation,
        "Translation-only mode should route combined selection to translation audio"
    )
    requireEqual(
        usesCombinedQueue(
            isSequenceModeActive: false,
            audioModeManager: manager,
            selectedOption: chunk.audioOptions.first { $0.id == "combined" }
        ),
        false,
        "Translation-only mode should not add combined queue offsets"
    )

    sequenceController.isEnabled = false
    let transcriptProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { 6 },
        timeBasedIndex: { 5 }
    )
    manager.toggle(.translation, preservingPosition: transcriptProvider.index)
    requireEqual(modeEvents.count, 2, "Second track toggle should emit a mode event")
    requireEqual(modeEvents[1].0, .singleTrack(.original), "Translation-only toggle should switch to original-only")
    requireEqual(modeEvents[1].1, 6, "Transcript display position should be preserved")
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "original", "Original-only mode should prefer original")
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "original",
        timing: .original,
        "Original-only mode should route combined selection to original audio"
    )
    requireEqual(
        usesCombinedQueue(
            isSequenceModeActive: false,
            audioModeManager: manager,
            selectedOption: chunk.audioOptions.first { $0.id == "combined" }
        ),
        false,
        "Original-only mode should not add combined queue offsets"
    )

    let pendingTarget = SentencePositionProvider.targetSentenceIndex(
        in: chunk,
        explicitIndex: nil,
        pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 102)
    )
    manager.enableSequenceMode(preservingPosition: pendingTarget)
    requireEqual(modeEvents.count, 3, "Sequence restore should emit a mode event")
    requireEqual(modeEvents[2].0, .sequence, "Pending jump restore should return to sequence mode")
    requireEqual(modeEvents[2].1, 2, "Pending jump should preserve the resolved local sentence index")
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "combined", "Sequence mode should prefer combined audio")
    requireSequenceInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "combined",
        "Sequence mode should keep combined audio selected"
    )
    requireEqual(
        usesCombinedQueue(
            isSequenceModeActive: true,
            audioModeManager: manager,
            selectedOption: chunk.audioOptions.first { $0.id == "combined" }
        ),
        true,
        "Sequence mode should keep combined queue timing enabled"
    )

    var pendingResumeTrack: SequenceTrack?
    var resumeVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var resumeSelectedTrackID: String? = "combined"
    prepareResumeSingleTrack(
        .translation,
        manager: manager,
        pendingResumeTrack: &pendingResumeTrack
    )
    requireEqual(
        manager.currentMode,
        .singleTrack(.translation),
        "Translation-only resume should restore single-track mode before seeking"
    )
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: resumeSelectedTrackID),
        optionID: "translation",
        timing: .translation,
        "Translation-only resume should route stale combined selection to translation audio immediately"
    )
    requireEqual(
        applyPendingResumeSingleTrackIfNeeded(
            for: chunk,
            availableTracks: [.original, .translation, .transliteration],
            manager: manager,
            pendingResumeTrack: &pendingResumeTrack,
            visibleTracks: &resumeVisibleTracks,
            selectedAudioTrackID: &resumeSelectedTrackID
        ),
        true,
        "View restore should consume a pending translation-only resume track"
    )
    requireEqual(
        resumeVisibleTracks,
        [.translation],
        "View restore should keep translation-only visible instead of defaulting back to all tracks"
    )
    requireEqual(
        resumeSelectedTrackID,
        "translation",
        "View restore should select the translation audio option before playback prepares"
    )
    requireEqual(
        pendingResumeTrack,
        nil,
        "View restore should consume the pending resume track once applied"
    )
    var batchVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var batchHasCustomTrackSelection = false
    var batchSelectedTrackID: String? = "combined"
    requireEqual(
        preserveSingleTrackModeIfNeeded(
            for: chunk,
            availableTracks: [.original, .translation, .transliteration],
            manager: manager,
            visibleTracks: &batchVisibleTracks,
            hasCustomTrackSelection: &batchHasCustomTrackSelection,
            selectedAudioTrackID: &batchSelectedTrackID
        ),
        true,
        "Cross-batch setup should preserve an existing translation-only audio mode instead of defaulting to all tracks"
    )
    requireEqual(
        batchVisibleTracks,
        [.translation],
        "Cross-batch setup should keep the transcript aligned to the translation-only audio track"
    )
    requireEqual(
        batchHasCustomTrackSelection,
        true,
        "Cross-batch single-track preservation should mark the selection custom so later lifecycle passes do not reset it"
    )
    requireEqual(
        batchSelectedTrackID,
        "translation",
        "Cross-batch single-track preservation should select the matching audio option for the new batch"
    )
    var unloadedBatchVisibleTracks: Set<TextPlayerVariantKind> = [.original]
    var unloadedBatchHasCustomTrackSelection = false
    var unloadedBatchSelectedTrackID: String? = "combined"
    requireEqual(
        preserveSingleTrackModeIfNeeded(
            for: chunk,
            availableTracks: [.original],
            manager: manager,
            visibleTracks: &unloadedBatchVisibleTracks,
            hasCustomTrackSelection: &unloadedBatchHasCustomTrackSelection,
            selectedAudioTrackID: &unloadedBatchSelectedTrackID
        ),
        true,
        "Unloaded next-batch setup should preserve translation-only mode when text tracks temporarily fall back to original"
    )
    requireEqual(
        unloadedBatchVisibleTracks,
        [.translation],
        "Unloaded next-batch setup should keep translation visible until metadata hydrates"
    )
    requireEqual(
        unloadedBatchSelectedTrackID,
        "translation",
        "Unloaded next-batch setup should select translation audio from playable options"
    )
    let nextBatch = InteractiveChunk(
        id: "chapter-2",
        startSentence: 104,
        sentences: [
            .init(id: 4, displayIndex: 104, startGate: 0.0, originalStartGate: 0.0),
            .init(id: 5, displayIndex: 105, startGate: 2.0, originalStartGate: 4.0)
        ],
        audioOptions: [
            audioOption("combined-next", kind: .combined, urls: [originalURL, translationURL]),
            audioOption("original-next", kind: .original, urls: [originalURL]),
            audioOption("translation-next", kind: .translation, urls: [translationURL])
        ]
    )
    var selectedNextBatchTrackID: String? = "combined"
    var preferredNextBatchKind: InteractiveChunk.AudioOption.Kind? = .combined
    var sequenceAudioMode: AudioMode = .sequence
    manager.setTracks(original: false, translation: true, preservingPosition: 18)
    synchronizeSelectedAudioTrackWithCurrentMode(
        for: nextBatch,
        manager: manager,
        selectedAudioTrackID: &selectedNextBatchTrackID,
        preferredAudioKind: &preferredNextBatchKind,
        sequenceAudioMode: &sequenceAudioMode
    )
    requireEqual(
        selectedNextBatchTrackID,
        "translation-next",
        "Chunk handoff should switch the selected audio option before immediate playback can load the next batch"
    )
    requireEqual(
        preferredNextBatchKind,
        .translation,
        "Chunk handoff should keep later fallback selection pinned to translation-only mode"
    )
    requireEqual(
        sequenceAudioMode,
        .singleTrack(.translation),
        "Chunk handoff should update the sequence controller mode before preparing next-batch audio"
    )
    requireInstruction(
        manager.resolveAudioInstruction(for: nextBatch, selectedTrackID: selectedNextBatchTrackID),
        optionID: "translation-next",
        timing: .translation,
        "Chunk handoff should resolve translation-only audio before SwiftUI lifecycle preservation runs"
    )
    var prepareTimeSelectedTrackID: String? = "combined-next"
    var prepareTimePreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    var prepareTimeSequenceAudioMode: AudioMode = .sequence
    if let track = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: prepareTimeSequenceAudioMode,
        preferredAudioKind: prepareTimePreferredKind
    ) {
        applySingleTrackSelection(
            track,
            for: nextBatch,
            manager: manager,
            sequenceAudioMode: &prepareTimeSequenceAudioMode,
            selectedAudioTrackID: &prepareTimeSelectedTrackID,
            preferredAudioKind: &prepareTimePreferredKind
        )
    }
    requireEqual(
        prepareTimeSelectedTrackID,
        "translation-next",
        "Prepare audio should reapply translation-only selection before resolving a stale batch option"
    )
    requireInstruction(
        manager.resolveAudioInstruction(for: nextBatch, selectedTrackID: prepareTimeSelectedTrackID),
        optionID: "translation-next",
        timing: .translation,
        "Prepare audio reapplication should keep next-batch rendering and narration on translation"
    )
    var bridgelessSelectedTrackID: String? = "combined-next"
    var bridgelessPreferredKind: InteractiveChunk.AudioOption.Kind? = .translation
    var bridgelessSequenceAudioMode: AudioMode = .singleTrack(.translation)
    requireEqual(
        requestedSingleTrackMode(
            manager: nil,
            sequenceAudioMode: bridgelessSequenceAudioMode,
            preferredAudioKind: bridgelessPreferredKind
        ),
        .translation,
        "End-of-batch handoff should preserve translation-only selection even if the view manager bridge is unavailable"
    )
    applySingleTrackSelection(
        .translation,
        for: nextBatch,
        manager: nil,
        sequenceAudioMode: &bridgelessSequenceAudioMode,
        selectedAudioTrackID: &bridgelessSelectedTrackID,
        preferredAudioKind: &bridgelessPreferredKind
    )
    requireEqual(
        bridgelessSelectedTrackID,
        "translation-next",
        "Bridgeless end-of-batch handoff should select translation audio instead of falling back to combined"
    )
    requireEqual(
        bridgelessPreferredKind,
        .translation,
        "Bridgeless end-of-batch handoff should keep later repair pinned to translation"
    )
    requireEqual(
        isSequenceModeActive(
            manager: nil,
            sequenceAudioMode: bridgelessSequenceAudioMode,
            selectedAudioTrackID: "combined-next",
            chunk: nextBatch,
            sequenceEnabled: true
        ),
        false,
        "Single-track sequence-controller mode should stop stale combined selections from rendering as sequence after a batch handoff"
    )
    let combinedOnlyNextBatch = InteractiveChunk(
        id: "chapter-2-combined",
        startSentence: 104,
        sentences: [
            .init(id: 4, displayIndex: 104, startGate: 0.0, originalStartGate: 0.0),
            .init(id: 5, displayIndex: 105, startGate: 2.0, originalStartGate: 4.0)
        ],
        audioOptions: [
            audioOption("combined-only-next", kind: .combined, urls: [originalURL, translationURL])
        ]
    )
    var selectedCombinedOnlyTrackID: String? = "combined"
    var preferredCombinedOnlyKind: InteractiveChunk.AudioOption.Kind? = .combined
    var combinedOnlySequenceAudioMode: AudioMode = .sequence
    synchronizeSelectedAudioTrackWithCurrentMode(
        for: combinedOnlyNextBatch,
        manager: manager,
        selectedAudioTrackID: &selectedCombinedOnlyTrackID,
        preferredAudioKind: &preferredCombinedOnlyKind,
        sequenceAudioMode: &combinedOnlySequenceAudioMode
    )
    requireEqual(
        selectedCombinedOnlyTrackID,
        "combined-only-next",
        "Combined-only chunk handoff should still select the available option"
    )
    requireEqual(
        preferredCombinedOnlyKind,
        .translation,
        "Combined-only chunk handoff should remember translation preference for the next batch"
    )
    requireSingleURLInstruction(
        manager.resolveAudioInstruction(for: combinedOnlyNextBatch, selectedTrackID: selectedCombinedOnlyTrackID),
        url: translationURL,
        timing: .translation,
        "Combined-only chunk handoff should extract the translation stream before rendering follows the wrong track"
    )
    requireEqual(
        effectiveSelectedAudioOption(
            for: nextBatch,
            manager: manager,
            selectedAudioTrackID: "original-next"
        )?.id,
        "translation-next",
        "Translation-only rendering helpers should ignore stale original selections after a batch handoff"
    )
    requireEqual(
        effectiveSelectedAudioKind(
            for: nextBatch,
            manager: manager,
            selectedAudioTrackID: "combined-next"
        ),
        .translation,
        "Translation-only header/progress helpers should keep the active lane when selected ID still points at combined"
    )
    let placeholderNextBatch = InteractiveChunk(
        id: "chapter-3-placeholder",
        startSentence: 106,
        sentences: [],
        audioOptions: [
            audioOption("translation-placeholder", kind: .translation, urls: [translationURL])
        ]
    )
    var naturalBatchAnchor: RecentSingleTrackSentenceAnchor?
    rememberSingleTrackBatchStartAnchorIfNeeded(
        for: placeholderNextBatch,
        targetSentenceIndex: nil,
        autoPlay: true,
        isPlaybackRequested: true,
        manager: manager,
        anchor: &naturalBatchAnchor
    )
    requireEqual(
        naturalBatchAnchor,
        .init(chunkID: "chapter-3-placeholder", sentenceNumber: 106),
        "Natural translation-only batch advance should anchor the placeholder batch start before audio autoplay can reset rendering"
    )
    var targetedBatchAnchor: RecentSingleTrackSentenceAnchor?
    rememberSingleTrackBatchStartAnchorIfNeeded(
        for: placeholderNextBatch,
        targetSentenceIndex: 2,
        autoPlay: false,
        isPlaybackRequested: false,
        manager: manager,
        anchor: &targetedBatchAnchor
    )
    requireEqual(
        targetedBatchAnchor,
        .init(chunkID: "chapter-3-placeholder", sentenceNumber: 108),
        "Targeted translation-only batch selection should derive a visible sentence anchor from placeholder range metadata"
    )

    manager.setTracks(original: false, translation: true, preservingPosition: 17)
    let timeProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { nil },
        timeBasedIndex: { 3 }
    )
    manager.toggle(kind: .combined, preservingPosition: timeProvider.index)
    requireEqual(modeEvents.count, 5, "Single-track to combined restore should emit a mode event")
    requireEqual(modeEvents[4].0, .sequence, "Combined kind should restore sequence mode")
    requireEqual(modeEvents[4].1, 3, "Time fallback position should be preserved")

    let explicitTarget = SentencePositionProvider.targetSentenceIndex(
        in: chunk,
        explicitIndex: 1,
        pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 103)
    )
    requireEqual(explicitTarget, 1, "Explicit sentence target should win over pending jump")

    let dutchOnlyChunks = [
        InteractiveChunk(
            id: "chunk_2210",
            startSentence: 2210,
            sentences: (0..<10).map { offset in
                .init(
                    id: offset,
                    displayIndex: 2210 + offset,
                    startGate: Double(offset) * 2.0,
                    originalStartGate: Double(offset) * 4.0
                )
            },
            audioOptions: [
                audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
                audioOption("translation", kind: .translation, urls: [translationURL])
            ]
        ),
        InteractiveChunk(
            id: "chunk_2220",
            startSentence: 2220,
            sentences: (0..<10).map { offset in
                .init(
                    id: offset,
                    displayIndex: 2220 + offset,
                    startGate: Double(offset) * 2.0,
                    originalStartGate: Double(offset) * 4.0
                )
            },
            audioOptions: [
                audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
                audioOption("translation", kind: .translation, urls: [translationURL])
            ]
        ),
        InteractiveChunk(
            id: "chunk_2230",
            startSentence: 2230,
            sentences: (0..<10).map { offset in
                .init(
                    id: offset,
                    displayIndex: 2230 + offset,
                    startGate: Double(offset) * 2.0,
                    originalStartGate: Double(offset) * 4.0
                )
            },
            audioOptions: [
                audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
                audioOption("translation", kind: .translation, urls: [translationURL])
            ]
        )
    ]
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2210",
            currentTime: 18.25,
            track: .translation,
            forward: true
        ),
        .chunkStart(chunkID: "chunk_2220"),
        "Translation-only next sentence at a chunk boundary should advance to the next displayed batch, not skip a batch"
    )
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2220",
            currentTime: 0.10,
            track: .translation,
            forward: false
        ),
        .chunkEnd(chunkID: "chunk_2210"),
        "Translation-only previous sentence at a chunk boundary should return to the previous displayed batch"
    )
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2220",
            currentTime: 4.25,
            track: .translation,
            forward: true,
            anchorSentenceNumber: 2222
        ),
        .sentence(chunkID: "chunk_2220", localIndex: 3, startTime: 6.0),
        "Translation-only anchored next sentence should use visible sentence numbers on the active track"
    )
    requireEqual(
        singleTrackNavigationTarget(
            chunks: dutchOnlyChunks,
            currentChunkID: "chunk_2220",
            currentTime: 18.25,
            track: .translation,
            forward: true,
            anchorSentenceNumber: 2225
        ),
        .sentence(chunkID: "chunk_2220", localIndex: 6, startTime: 12.0),
        "Translation-only slider anchor should beat stale end-of-chunk time so next moves one sentence, not one batch"
    )
    requireEqual(
        singleTrackTimeSeekAnchor(
            time: 18.25,
            sentenceNumber: 2225,
            in: dutchOnlyChunks[1],
            activeTimingTrack: .translation
        ),
        2225,
        "Explicit translation-only time seeks should preserve the requested visible sentence anchor instead of stale player time"
    )
    requireEqual(
        singleTrackTimeSeekAnchor(
            time: 18.25,
            sentenceNumber: nil,
            in: dutchOnlyChunks[1],
            activeTimingTrack: .translation
        ),
        2229,
        "Bare translation-only time seeks should still fall back to active-track gate timing"
    )
    let sliderJumpTargetIndex = SentencePositionProvider.targetSentenceIndex(
        in: dutchOnlyChunks[1],
        explicitIndex: nil,
        pendingJump: .init(chunkID: "chunk_2220", sentenceNumber: 2225)
    )
    requireEqual(
        sliderJumpTargetIndex,
        5,
        "Cross-chunk translation-only slider jumps should resolve the visible sentence to the new chunk's local index before audio loads"
    )
    requireEqual(
        sliderJumpTargetIndex.flatMap {
            startTime(in: dutchOnlyChunks[1], at: $0, track: .translation)
        },
        10.0,
        "Cross-chunk translation-only slider jumps should seek to the target sentence gate, not the start of the 10-sentence batch"
    )
    let derivedDutchChunk = InteractiveChunk(
        id: "chunk_2220_derived",
        startSentence: 2220,
        sentences: (0..<10).map { offset in
            .init(
                id: offset,
                displayIndex: nil,
                startGate: Double(offset) * 2.0,
                originalStartGate: Double(offset) * 4.0
            )
        },
        audioOptions: [
            audioOption("combined", kind: .combined, urls: [originalURL, translationURL]),
            audioOption("translation", kind: .translation, urls: [translationURL])
        ]
    )
    requireEqual(
        SentencePositionProvider.sentenceIndex(in: derivedDutchChunk, matching: 2225),
        5,
        "Derived chunk-range metadata should resolve slider sentence numbers to local row indexes"
    )
    requireEqual(
        SentencePositionProvider.sentenceIndex(in: derivedDutchChunk, matching: 5),
        nil,
        "Derived chunk-range metadata must not let local row ids masquerade as visible sentence numbers"
    )
    var resumeAnchor: RecentSingleTrackSentenceAnchor? = .init(
        chunkID: "chunk_2220",
        sentenceNumber: 2225
    )
    requireEqual(
        recentSingleTrackAnchorDisplaySentence(
            anchor: &resumeAnchor,
            in: dutchOnlyChunks[1],
            highlightingTime: 10.05,
            currentChunkAudioIsActive: true,
            track: .translation
        ),
        nil,
        "Translation-only resume anchor should stop forcing display once live playback reaches the target sentence"
    )
    requireNil(
        resumeAnchor,
        "Translation-only resume anchor should be consumed after live playback reaches the target sentence"
    )
    requireEqual(
        recentSingleTrackAnchorDisplaySentence(
            anchor: &resumeAnchor,
            in: dutchOnlyChunks[1],
            highlightingTime: 12.25,
            currentChunkAudioIsActive: true,
            track: .translation
        ),
        nil,
        "Consumed translation-only resume anchor must not pull the first post-resume sentence back out of sync"
    )
}

@main
private struct PlaybackModeSwitchIntegrationCheck {
    static func main() async {
        await MainActor.run {
            runChecks()
        }
    }
}
