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
    let sentenceNumber: Int?
    let targetIndex: Int?
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
    let sentenceNumber: Int? = {
        if let sentenceNumber = currentAnchor.sentenceNumber {
            return sentenceNumber
        }
        guard let targetIndex = currentAnchor.targetIndex else { return nil }
        return SentencePositionProvider.sentenceNumber(in: chunk, at: targetIndex)
    }()
    guard let sentenceNumber else { return nil }
    guard currentChunkAudioIsActive else { return sentenceNumber }
    guard let targetIndex = SentencePositionProvider.sentenceIndex(
        in: chunk,
        matching: sentenceNumber
    ),
    let start = startTime(in: chunk, at: targetIndex, track: track) else {
        return sentenceNumber
    }
    let tolerance = 0.18
    if chunk.sentences.indices.contains(targetIndex + 1),
       let nextStart = startTime(in: chunk, at: targetIndex + 1, track: track),
       nextStart > start {
        if highlightingTime >= start - tolerance && highlightingTime < nextStart + tolerance {
            anchor = nil
            return nil
        }
        return sentenceNumber
    }
    if highlightingTime >= start - tolerance && highlightingTime <= start + 2.5 {
        anchor = nil
        return nil
    }
    return sentenceNumber
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
    guard let targetIndex = inferredTargetIndex else {
        return
    }
    anchor = .init(
        chunkID: chunk.id,
        sentenceNumber: singleTrackSentenceNumber(in: chunk, targetIndex: targetIndex),
        targetIndex: targetIndex >= 0 ? targetIndex : nil
    )
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

@MainActor
private func alignVisibleTracksWithCurrentAudioMode(
    for chunk: InteractiveChunk,
    availableTracks: Set<TextPlayerVariantKind>,
    manager: AudioModeManager,
    visibleTracks: inout Set<TextPlayerVariantKind>,
    hasCustomTrackSelection: inout Bool,
    selectedAudioTrackID: inout String?,
    expandSequenceMode: Bool = false
) -> Bool {
    switch manager.currentMode {
    case .singleTrack(let track):
        let desiredTextTrack: TextPlayerVariantKind = track == .original ? .original : .translation
        guard availableTracks.contains(desiredTextTrack) || chunkSupportsAudioTrack(track, in: chunk) else { return false }
        guard visibleTracks != [desiredTextTrack] || !hasCustomTrackSelection else { return false }
        visibleTracks = [desiredTextTrack]
        hasCustomTrackSelection = true
        selectedAudioTrackID = manager.resolvePreferredTrackID(for: chunk)
        return true

    case .sequence:
        guard expandSequenceMode else { return false }
        guard !availableTracks.isEmpty, visibleTracks != availableTracks || hasCustomTrackSelection else { return false }
        visibleTracks = availableTracks
        hasCustomTrackSelection = false
        selectedAudioTrackID = manager.resolvePreferredTrackID(for: chunk)
        return true
    }
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
    preferredSingleTrackMode: inout SequenceTrack?,
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
    if case .singleTrack(let track) = manager.currentMode {
        preferredSingleTrackMode = track
    }
    sequenceAudioMode = manager.currentMode
}

@MainActor
private func requestedSingleTrackMode(
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?
) -> SequenceTrack? {
    if let manager {
        if case .singleTrack(let track) = manager.currentMode {
            return track
        }
    }
    if case .singleTrack(let track) = sequenceAudioMode {
        return track
    }
    if let preferredSingleTrackMode {
        return preferredSingleTrackMode
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
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?,
    preferredSingleTrackMode: inout SequenceTrack?
) {
    preferredSingleTrackMode = track
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
            preferredSingleTrackMode: &preferredSingleTrackMode,
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

@MainActor
private func prepareAdjacentChunkSelection(
    currentChunk: InteractiveChunk,
    chunks: [InteractiveChunk],
    forward: Bool,
    manager: AudioModeManager?,
    sequenceAudioMode: inout AudioMode,
    selectedAudioTrackID: inout String?,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?,
    preferredSingleTrackMode: inout SequenceTrack?,
    anchor: inout RecentSingleTrackSentenceAnchor?
) -> (chunk: InteractiveChunk, targetIndex: Int?)? {
    guard let currentIndex = chunks.firstIndex(where: { $0.id == currentChunk.id }) else { return nil }
    let targetIndex = forward ? currentIndex + 1 : currentIndex - 1
    guard chunks.indices.contains(targetIndex) else { return nil }
    let targetChunk = chunks[targetIndex]
    let targetSentenceIndex = forward ? 0 : -1
    if let track = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) {
        applySingleTrackSelection(
            track,
            for: targetChunk,
            manager: manager,
            sequenceAudioMode: &sequenceAudioMode,
            selectedAudioTrackID: &selectedAudioTrackID,
            preferredAudioKind: &preferredAudioKind,
            preferredSingleTrackMode: &preferredSingleTrackMode
        )
        anchor = .init(
            chunkID: targetChunk.id,
            sentenceNumber: singleTrackSentenceNumber(
                in: targetChunk,
                targetIndex: targetSentenceIndex
            ),
            targetIndex: targetSentenceIndex >= 0 ? targetSentenceIndex : nil
        )
    }
    return (targetChunk, targetSentenceIndex)
}

@MainActor
private func singleTrackModeForCompletedPlayback(
    endedURL: URL?,
    chunk: InteractiveChunk,
    activeURLs: [URL],
    sequenceEnabled: Bool,
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?
) -> SequenceTrack? {
    if let track = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) {
        return track
    }
    guard !sequenceEnabled else { return nil }
    guard let endedURL else { return nil }
    if !activeURLs.isEmpty,
       activeURLs.count != 1 || activeURLs.first != endedURL {
        return nil
    }
    if chunk.audioOptions.contains(where: { $0.kind == .original && $0.streamURLs.contains(endedURL) }) {
        return .original
    }
    if chunk.audioOptions.contains(where: { $0.kind == .translation && $0.streamURLs.contains(endedURL) }) {
        return .translation
    }
    if let combined = chunk.audioOptions.first(where: { $0.kind == .combined }) {
        if combined.streamURLs.first == endedURL {
            return .original
        }
        if combined.streamURLs.dropFirst().contains(endedURL) {
            return .translation
        }
    }
    return nil
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
    sequenceEnabled: Bool,
    preferredSingleTrackMode: SequenceTrack? = nil,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind? = nil
) -> Bool {
    guard requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) == nil else {
        return false
    }
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
    selectedAudioTrackID: String?,
    sequenceAudioMode: AudioMode = .sequence,
    preferredSingleTrackMode: SequenceTrack? = nil,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind? = nil
) -> InteractiveChunk.AudioOption? {
    if let track = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) {
        return preferredSingleTrackAudioOption(for: track, in: chunk)
    }
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
    selectedAudioTrackID: String?,
    sequenceAudioMode: AudioMode = .sequence,
    preferredSingleTrackMode: SequenceTrack? = nil,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind? = nil
) -> InteractiveChunk.AudioOption.Kind? {
    if let track = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ), chunkSupportsAudioTrack(track, in: chunk) {
        return track == .original ? .original : .translation
    }
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
        selectedAudioTrackID: selectedAudioTrackID,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
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
    var preferredNextBatchSingleTrack: SequenceTrack?
    var sequenceAudioMode: AudioMode = .sequence
    manager.setTracks(original: false, translation: true, preservingPosition: 18)
    synchronizeSelectedAudioTrackWithCurrentMode(
        for: nextBatch,
        manager: manager,
        selectedAudioTrackID: &selectedNextBatchTrackID,
        preferredAudioKind: &preferredNextBatchKind,
        preferredSingleTrackMode: &preferredNextBatchSingleTrack,
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
        preferredNextBatchSingleTrack,
        .translation,
        "Chunk handoff should record translation-only as the durable lane before batch autoplay starts"
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
    var prepareTimePreferredSingleTrack: SequenceTrack?
    var prepareTimeSequenceAudioMode: AudioMode = .sequence
    if let track = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: prepareTimeSequenceAudioMode,
        preferredSingleTrackMode: nil,
        preferredAudioKind: prepareTimePreferredKind
    ) {
        applySingleTrackSelection(
            track,
            for: nextBatch,
            manager: manager,
            sequenceAudioMode: &prepareTimeSequenceAudioMode,
            selectedAudioTrackID: &prepareTimeSelectedTrackID,
            preferredAudioKind: &prepareTimePreferredKind,
            preferredSingleTrackMode: &prepareTimePreferredSingleTrack
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
    var adjacentSelectedTrackID: String? = "combined-next"
    var adjacentPreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    var adjacentPreferredSingleTrack: SequenceTrack?
    var adjacentSequenceAudioMode: AudioMode = .sequence
    var adjacentAnchor: RecentSingleTrackSentenceAnchor?
    let adjacentTarget = prepareAdjacentChunkSelection(
        currentChunk: chunk,
        chunks: [chunk, nextBatch],
        forward: true,
        manager: manager,
        sequenceAudioMode: &adjacentSequenceAudioMode,
        selectedAudioTrackID: &adjacentSelectedTrackID,
        preferredAudioKind: &adjacentPreferredKind,
        preferredSingleTrackMode: &adjacentPreferredSingleTrack,
        anchor: &adjacentAnchor
    )
    requireEqual(
        adjacentTarget?.chunk.id,
        "chapter-2",
        "Adjacent batch helper should select the next chunk at end of batch"
    )
    requireEqual(
        adjacentTarget?.targetIndex,
        0,
        "Adjacent batch helper should target the first visible sentence in the next batch"
    )
    requireEqual(
        adjacentSelectedTrackID,
        "translation-next",
        "Adjacent batch helper should repair stale combined selection before autoplay observes the next batch"
    )
    requireEqual(
        adjacentSequenceAudioMode,
        .singleTrack(.translation),
        "Adjacent batch helper should keep the sequence controller in translation-only mode"
    )
    requireEqual(
        adjacentAnchor,
        .init(chunkID: "chapter-2", sentenceNumber: 104, targetIndex: 0),
        "Adjacent batch helper should anchor the first next-batch sentence before rendering refreshes"
    )
    requireInstruction(
        manager.resolveAudioInstruction(for: nextBatch, selectedTrackID: adjacentSelectedTrackID),
        optionID: "translation-next",
        timing: .translation,
        "Adjacent batch helper should resolve translation audio after repairing the selection"
    )
    var bridgelessSelectedTrackID: String? = "combined-next"
    var bridgelessPreferredKind: InteractiveChunk.AudioOption.Kind? = .translation
    var bridgelessPreferredSingleTrack: SequenceTrack?
    var bridgelessSequenceAudioMode: AudioMode = .singleTrack(.translation)
    requireEqual(
        requestedSingleTrackMode(
            manager: nil,
            sequenceAudioMode: bridgelessSequenceAudioMode,
            preferredSingleTrackMode: nil,
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
        preferredAudioKind: &bridgelessPreferredKind,
        preferredSingleTrackMode: &bridgelessPreferredSingleTrack
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
    var staleManagerSelectedTrackID: String? = "combined-next"
    var staleManagerPreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    var staleManagerSequenceAudioMode: AudioMode = .sequence
    var staleManagerPreferredSingleTrackMode: SequenceTrack? = .translation
    let staleSequenceManager = AudioModeManager()
    if let track = requestedSingleTrackMode(
        manager: staleSequenceManager,
        sequenceAudioMode: staleManagerSequenceAudioMode,
        preferredSingleTrackMode: staleManagerPreferredSingleTrackMode,
        preferredAudioKind: staleManagerPreferredKind
    ) {
        applySingleTrackSelection(
            track,
            for: nextBatch,
            manager: staleSequenceManager,
            sequenceAudioMode: &staleManagerSequenceAudioMode,
            selectedAudioTrackID: &staleManagerSelectedTrackID,
            preferredAudioKind: &staleManagerPreferredKind,
            preferredSingleTrackMode: &staleManagerPreferredSingleTrackMode
        )
    }
    requireEqual(
        staleManagerSelectedTrackID,
        "translation-next",
        "Remembered translation-only lane should survive a stale sequence manager at the next batch boundary"
    )
    requireEqual(
        staleManagerSequenceAudioMode,
        .singleTrack(.translation),
        "Remembered translation-only lane should restore sequence-controller mode before next-batch audio resolves"
    )
    let staleViewManager = AudioModeManager()
    requireEqual(
        isSequenceModeActive(
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            selectedAudioTrackID: "combined-next",
            chunk: nextBatch,
            sequenceEnabled: true,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined
        ),
        false,
        "Remembered translation-only lane should stop stale view-manager sequence state from reactivating batch rendering"
    )
    requireEqual(
        effectiveSelectedAudioOption(
            for: nextBatch,
            manager: staleViewManager,
            selectedAudioTrackID: "combined-next",
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined
        )?.id,
        "translation-next",
        "Remembered translation-only lane should keep header/progress helpers on the translation option when batch selection is stale"
    )
    requireEqual(
        effectiveSelectedAudioKind(
            for: nextBatch,
            manager: staleViewManager,
            selectedAudioTrackID: "combined-next",
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined
        ),
        .translation,
        "Remembered translation-only lane should keep batch duration and role summaries on translation"
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
    var preferredCombinedOnlySingleTrack: SequenceTrack?
    var combinedOnlySequenceAudioMode: AudioMode = .sequence
    synchronizeSelectedAudioTrackWithCurrentMode(
        for: combinedOnlyNextBatch,
        manager: manager,
        selectedAudioTrackID: &selectedCombinedOnlyTrackID,
        preferredAudioKind: &preferredCombinedOnlyKind,
        preferredSingleTrackMode: &preferredCombinedOnlySingleTrack,
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
    requireEqual(
        preferredCombinedOnlySingleTrack,
        .translation,
        "Combined-only chunk handoff should keep a durable translation-only lane even when the selected option remains combined"
    )
    requireSingleURLInstruction(
        manager.resolveAudioInstruction(for: combinedOnlyNextBatch, selectedTrackID: selectedCombinedOnlyTrackID),
        url: translationURL,
        timing: .translation,
        "Combined-only chunk handoff should extract the translation stream before rendering follows the wrong track"
    )
    let combinedOnlyOption = combinedOnlyNextBatch.audioOptions[0]
    requireEqual(
        PlaybackEndedURLPolicy.endedURL(
            originalURL,
            belongsTo: combinedOnlyOption,
            singleTrack: .translation
        ),
        false,
        "Combined-only translation playback should reject hidden original EOF callbacks"
    )
    requireEqual(
        PlaybackEndedURLPolicy.endedURL(
            translationURL,
            belongsTo: combinedOnlyOption,
            singleTrack: .translation
        ),
        true,
        "Combined-only translation playback should accept translation EOF callbacks"
    )
    requireEqual(
        PlaybackEndedURLPolicy.endedURL(
            originalURL,
            belongsTo: combinedOnlyOption,
            singleTrack: .original
        ),
        true,
        "Combined-only original playback should accept original EOF callbacks"
    )
    let staleCompletedLane = singleTrackModeForCompletedPlayback(
        endedURL: translationURL,
        chunk: combinedOnlyNextBatch,
        activeURLs: [translationURL],
        sequenceEnabled: false,
        manager: staleViewManager,
        sequenceAudioMode: .sequence,
        preferredSingleTrackMode: nil,
        preferredAudioKind: .combined
    )
    requireEqual(
        staleCompletedLane,
        .translation,
        "Single-track EOF handoff should infer translation from the completed URL when manager and selected id reset to combined"
    )
    var eofSelectedTrackID: String? = "combined-only-next"
    var eofPreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    var eofPreferredSingleTrack: SequenceTrack?
    var eofSequenceAudioMode: AudioMode = .sequence
    if let staleCompletedLane {
        applySingleTrackSelection(
            staleCompletedLane,
            for: combinedOnlyNextBatch,
            manager: staleViewManager,
            sequenceAudioMode: &eofSequenceAudioMode,
            selectedAudioTrackID: &eofSelectedTrackID,
            preferredAudioKind: &eofPreferredKind,
            preferredSingleTrackMode: &eofPreferredSingleTrack
        )
    }
    requireEqual(
        eofPreferredSingleTrack,
        .translation,
        "Single-track EOF handoff should restore a durable translation lane before selecting the next batch"
    )
    requireEqual(
        eofSequenceAudioMode,
        .singleTrack(.translation),
        "Single-track EOF handoff should restore single-track mode before new-batch audio prepares"
    )
    requireSingleURLInstruction(
        staleViewManager.resolveAudioInstruction(for: combinedOnlyNextBatch, selectedTrackID: eofSelectedTrackID),
        url: translationURL,
        timing: .translation,
        "Single-track EOF handoff should keep rendering and narration on the completed translation lane"
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
    var headerVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var headerHasCustomTrackSelection = false
    var headerSelectedTrackID: String? = "combined-next"
    let headerManager = AudioModeManager()
    headerManager.setTracks(original: false, translation: true, preservingPosition: 18)
    requireEqual(
        alignVisibleTracksWithCurrentAudioMode(
            for: nextBatch,
            availableTracks: [.original, .translation, .transliteration],
            manager: headerManager,
            visibleTracks: &headerVisibleTracks,
            hasCustomTrackSelection: &headerHasCustomTrackSelection,
            selectedAudioTrackID: &headerSelectedTrackID
        ),
        true,
        "Header/menu translation-only audio changes should immediately pin the visible text track before batch handoff"
    )
    requireEqual(
        headerVisibleTracks,
        [.translation],
        "Header/menu translation-only selection should not leave all transcript tracks visible until a later lifecycle pass"
    )
    requireEqual(
        headerSelectedTrackID,
        "translation-next",
        "Header/menu translation-only selection should repair the selected audio id for the active batch"
    )
    headerManager.enableSequenceMode(preservingPosition: 18)
    requireEqual(
        alignVisibleTracksWithCurrentAudioMode(
            for: nextBatch,
            availableTracks: [.original, .translation, .transliteration],
            manager: headerManager,
            visibleTracks: &headerVisibleTracks,
            hasCustomTrackSelection: &headerHasCustomTrackSelection,
            selectedAudioTrackID: &headerSelectedTrackID,
            expandSequenceMode: true
        ),
        true,
        "Combined audio selection should expand transcript tracks instead of leaving stale translation-only rendering"
    )
    requireEqual(
        headerVisibleTracks,
        [.original, .translation, .transliteration],
        "Combined audio selection should restore all available transcript tracks"
    )
    requireEqual(
        headerHasCustomTrackSelection,
        false,
        "Combined audio selection should clear the single-track custom transcript pin"
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
    let reorderedSequenceBatch = InteractiveChunk(
        id: "chapter-2-reordered",
        startSentence: 104,
        sentences: [
            .init(id: 4, displayIndex: 104, startGate: 0.0, originalStartGate: 0.0)
        ],
        audioOptions: [
            audioOption("original-next", kind: .original, urls: [originalURL]),
            audioOption("translation-next", kind: .translation, urls: [translationURL]),
            audioOption("combined-next", kind: .combined, urls: [originalURL, translationURL])
        ]
    )
    let sequenceBoundaryManager = AudioModeManager()
    requireSequenceInstruction(
        sequenceBoundaryManager.resolveAudioInstruction(
            for: reorderedSequenceBatch,
            selectedTrackID: "translation-next"
        ),
        optionID: "combined-next",
        "Sequence-mode batch handoff should prefer the current chunk's combined option over a valid stale single-track selection"
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
        .init(chunkID: "chapter-3-placeholder", sentenceNumber: 106, targetIndex: 0),
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
        .init(chunkID: "chapter-3-placeholder", sentenceNumber: 108, targetIndex: 2),
        "Targeted translation-only batch selection should derive a visible sentence anchor from placeholder range metadata"
    )
    let unresolvedPlaceholderBatch = InteractiveChunk(
        id: "chapter-4-placeholder",
        startSentence: nil,
        sentences: [],
        audioOptions: [
            audioOption("translation-unresolved", kind: .translation, urls: [translationURL])
        ]
    )
    var unresolvedBatchAnchor: RecentSingleTrackSentenceAnchor?
    rememberSingleTrackBatchStartAnchorIfNeeded(
        for: unresolvedPlaceholderBatch,
        targetSentenceIndex: 0,
        autoPlay: true,
        isPlaybackRequested: true,
        manager: manager,
        anchor: &unresolvedBatchAnchor
    )
    requireEqual(
        unresolvedBatchAnchor,
        .init(chunkID: "chapter-4-placeholder", sentenceNumber: nil, targetIndex: 0),
        "Unresolved placeholder batches should still preserve the target row until metadata exposes the sentence number"
    )
    let hydratedUnresolvedBatch = InteractiveChunk(
        id: "chapter-4-placeholder",
        startSentence: 109,
        sentences: [
            .init(id: 0, displayIndex: 109, startGate: 0.0, originalStartGate: 0.0)
        ],
        audioOptions: unresolvedPlaceholderBatch.audioOptions
    )
    requireEqual(
        recentSingleTrackAnchorDisplaySentence(
            anchor: &unresolvedBatchAnchor,
            in: hydratedUnresolvedBatch,
            highlightingTime: 0.0,
            currentChunkAudioIsActive: false,
            track: .translation
        ),
        109,
        "Hydrated placeholder batches should upgrade the target row anchor to the real displayed sentence number"
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
        sentenceNumber: 2225,
        targetIndex: nil
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
