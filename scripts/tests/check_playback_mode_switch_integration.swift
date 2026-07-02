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

enum LanguageFlagRole: String, Hashable {
    case original
    case translation
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

private func playbackRequestAfterQueueEnd(
    hadURLAwareHandler: Bool,
    wasPlaybackRequested: Bool
) -> Bool {
    var isPlaybackRequested = wasPlaybackRequested
    if hadURLAwareHandler {
        return isPlaybackRequested
    }
    isPlaybackRequested = false
    return isPlaybackRequested
}

private func sameURLReloadState(
    urls: [URL],
    activeURLs: [URL],
    activeURL: URL?,
    wasPlaybackRequested: Bool,
    autoPlay: Bool,
    forceNoAutoPlay: Bool,
    preservePlaybackRequested: Bool
) -> (isPlaybackRequested: Bool, activeURL: URL?) {
    let shouldAutoPlay = forceNoAutoPlay ? false : (autoPlay || wasPlaybackRequested)
    guard activeURLs == urls else {
        return (preservePlaybackRequested ? wasPlaybackRequested : shouldAutoPlay, urls.first)
    }
    var nextActiveURL = activeURL
    if nextActiveURL == nil {
        nextActiveURL = urls.first
    }
    return (preservePlaybackRequested ? wasPlaybackRequested : shouldAutoPlay, nextActiveURL)
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
private func useCombinedPhasesForIntegration(
    chunk: InteractiveChunk,
    manager: AudioModeManager,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?,
    selectedAudioTrackID: String?,
    activeURL: URL?
) -> Bool {
    if requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) != nil {
        return false
    }
    guard let track = effectiveSelectedAudioOption(
        for: chunk,
        manager: manager,
        selectedAudioTrackID: selectedAudioTrackID,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) else {
        return false
    }
    guard track.kind == .combined, track.streamURLs.count == 1 else {
        return false
    }
    guard let activeURL else { return true }
    return activeURL == track.primaryURL
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
private func restoreSingleTrackModeFromViewModelPreferenceIfNeeded(
    for chunk: InteractiveChunk,
    availableTracks: Set<TextPlayerVariantKind>,
    manager: AudioModeManager,
    visibleTracks: inout Set<TextPlayerVariantKind>,
    hasCustomTrackSelection: inout Bool,
    selectedAudioTrackID: inout String?,
    preferredSingleTrackMode: SequenceTrack?,
    durableSingleTrackPlaybackMode: SequenceTrack? = nil,
    loadedSingleTrackPlaybackMode: SequenceTrack? = nil,
    sequenceAudioMode: inout AudioMode,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?
) -> Bool {
    let requestedTrack = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind,
        durableSingleTrackPlaybackMode: durableSingleTrackPlaybackMode,
        loadedSingleTrackPlaybackMode: loadedSingleTrackPlaybackMode,
        chunk: chunk
    )
    guard let requestedTrack else { return false }

    let desiredTextTrack: TextPlayerVariantKind = requestedTrack == .original ? .original : .translation
    guard availableTracks.contains(desiredTextTrack) || chunkSupportsAudioTrack(requestedTrack, in: chunk) else {
        return false
    }

    visibleTracks = [desiredTextTrack]
    hasCustomTrackSelection = true
    manager.setTracks(
        original: requestedTrack == .original,
        translation: requestedTrack == .translation
    )
    sequenceAudioMode = manager.currentMode
    var restoredPreferredSingleTrackMode = preferredSingleTrackMode
    applySingleTrackSelection(
        requestedTrack,
        for: chunk,
        manager: manager,
        sequenceAudioMode: &sequenceAudioMode,
        selectedAudioTrackID: &selectedAudioTrackID,
        preferredAudioKind: &preferredAudioKind,
        preferredSingleTrackMode: &restoredPreferredSingleTrackMode
    )
    return true
}

@MainActor
private func restoreSingleTrackModeFromVisibleSelectionIfNeeded(
    for chunk: InteractiveChunk,
    availableTracks: Set<TextPlayerVariantKind>,
    manager: AudioModeManager,
    visibleTracks: inout Set<TextPlayerVariantKind>,
    hasCustomTrackSelection: inout Bool,
    selectedAudioTrackID: inout String?,
    sequenceAudioMode: inout AudioMode,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?,
    preferredSingleTrackMode: inout SequenceTrack?
) -> Bool {
    guard hasCustomTrackSelection, visibleTracks.count == 1 else { return false }
    guard let onlyTrack = visibleTracks.first else { return false }
    let requestedTrack: SequenceTrack?
    switch onlyTrack {
    case .original:
        requestedTrack = .original
    case .translation:
        requestedTrack = .translation
    case .transliteration:
        requestedTrack = nil
    }
    guard let requestedTrack else { return false }
    guard availableTracks.contains(onlyTrack) || chunkSupportsAudioTrack(requestedTrack, in: chunk) else {
        return false
    }

    manager.setTracks(
        original: requestedTrack == .original,
        translation: requestedTrack == .translation
    )
    sequenceAudioMode = manager.currentMode
    applySingleTrackSelection(
        requestedTrack,
        for: chunk,
        manager: manager,
        sequenceAudioMode: &sequenceAudioMode,
        selectedAudioTrackID: &selectedAudioTrackID,
        preferredAudioKind: &preferredAudioKind,
        preferredSingleTrackMode: &preferredSingleTrackMode
    )
    return true
}

private func shouldPreferCustomMultiTrackSelection(
    availableTracks: Set<TextPlayerVariantKind>,
    visibleTracks: Set<TextPlayerVariantKind>,
    hasCustomTrackSelection: Bool
) -> Bool {
    guard hasCustomTrackSelection else { return false }
    guard availableTracks.contains(.original), availableTracks.contains(.translation) else { return false }
    return visibleTracks.contains(.original) && visibleTracks.contains(.translation)
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

@MainActor
private func synchronizeAudioModeWithVisibleTextTracks(
    for chunk: InteractiveChunk,
    availableTracks: Set<TextPlayerVariantKind>,
    manager: AudioModeManager,
    visibleTracks: inout Set<TextPlayerVariantKind>,
    hasCustomTrackSelection: inout Bool,
    selectedAudioTrackID: inout String?,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?,
    preferredSingleTrackMode: inout SequenceTrack?,
    sequenceAudioMode: inout AudioMode,
    allowExpandingSingleTrackAudio: Bool = false
) -> Bool {
    let canUseOriginal = availableTracks.contains(.original)
    let canUseTranslation = availableTracks.contains(.translation)
    guard canUseOriginal || canUseTranslation else { return false }

    let wantsOriginal = canUseOriginal && visibleTracks.contains(.original)
    let wantsTranslation = canUseTranslation && visibleTracks.contains(.translation)
    guard wantsOriginal || wantsTranslation else { return false }

    if !allowExpandingSingleTrackAudio,
       wantsOriginal && wantsTranslation,
       let durableSingleTrack = requestedSingleTrackMode(
            manager: manager,
            sequenceAudioMode: sequenceAudioMode,
            preferredSingleTrackMode: preferredSingleTrackMode,
            preferredAudioKind: preferredAudioKind
       ) {
        visibleTracks = [durableSingleTrack == .original ? .original : .translation]
        hasCustomTrackSelection = true
        applySingleTrackSelection(
            durableSingleTrack,
            for: chunk,
            manager: manager,
            sequenceAudioMode: &sequenceAudioMode,
            selectedAudioTrackID: &selectedAudioTrackID,
            preferredAudioKind: &preferredAudioKind,
            preferredSingleTrackMode: &preferredSingleTrackMode
        )
        return true
    }

    guard wantsOriginal != manager.isOriginalEnabled
        || wantsTranslation != manager.isTranslationEnabled else {
        return false
    }

    manager.setTracks(original: wantsOriginal, translation: wantsTranslation)
    sequenceAudioMode = manager.currentMode
    selectedAudioTrackID = manager.resolvePreferredTrackID(for: chunk)
    if case .singleTrack(let track) = manager.currentMode {
        preferredSingleTrackMode = track
    } else {
        preferredSingleTrackMode = nil
    }
    preferredAudioKind = selectedAudioTrackID.flatMap { id in
        chunk.audioOptions.first(where: { $0.id == id })?.kind
    }
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
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?,
    durableSingleTrackPlaybackMode: SequenceTrack? = nil,
    loadedSingleTrackPlaybackMode: SequenceTrack? = nil,
    chunk: InteractiveChunk? = nil,
    selectedTimingURL: URL? = nil,
    selectedTimingSingleTrackMode: SequenceTrack? = nil
) -> SequenceTrack? {
    if let loadedSingleTrackPlaybackMode {
        return loadedSingleTrackPlaybackMode
    }
    if let preferredSingleTrackMode {
        return preferredSingleTrackMode
    }
    if let durableSingleTrackPlaybackMode {
        return durableSingleTrackPlaybackMode
    }
    if let chunk,
       let selectedTimingSingleTrackMode {
        if let selectedTimingURL,
           singleTrackModeForAudioURL(selectedTimingURL, in: chunk) == selectedTimingSingleTrackMode {
            return selectedTimingSingleTrackMode
        }
        if chunkSupportsAudioTrack(selectedTimingSingleTrackMode, in: chunk) {
            return selectedTimingSingleTrackMode
        }
    }
    if let manager {
        if case .singleTrack(let track) = manager.currentMode {
            return track
        }
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

private func singleTrackModeForAudioURL(
    _ url: URL,
    in chunk: InteractiveChunk
) -> SequenceTrack? {
    if chunk.audioOptions.contains(where: { $0.kind == .original && $0.streamURLs.contains(url) }) {
        return .original
    }
    if chunk.audioOptions.contains(where: { $0.kind == .translation && $0.streamURLs.contains(url) }) {
        return .translation
    }
    if let combined = chunk.audioOptions.first(where: { $0.kind == .combined }) {
        if combined.streamURLs.first == url {
            return .original
        }
        if combined.streamURLs.dropFirst().contains(url) {
            return .translation
        }
    }
    return nil
}

@MainActor
private func requestedSingleTrackMode(
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?,
    chunk: InteractiveChunk,
    sequenceEnabled: Bool,
    activeURLs: [URL],
    durableSingleTrackPlaybackMode: SequenceTrack? = nil,
    loadedSingleTrackPlaybackMode: SequenceTrack? = nil,
    sequencePlanIsEmpty: Bool = true
) -> SequenceTrack? {
    if let requested = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind,
        durableSingleTrackPlaybackMode: durableSingleTrackPlaybackMode,
        loadedSingleTrackPlaybackMode: loadedSingleTrackPlaybackMode,
        chunk: chunk
    ) {
        return requested
    }
    guard !sequenceEnabled,
          sequencePlanIsEmpty,
          activeURLs.count == 1,
          let activeURL = activeURLs.first else {
        return nil
    }
    return singleTrackModeForAudioURL(activeURL, in: chunk)
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
private func concreteAudioModeTrack(
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?
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
    return preferredSingleTrackMode
}

@MainActor
private func audioModeMatchesSelectedTrack(
    _ track: InteractiveChunk.AudioOption,
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?
) -> Bool {
    switch track.kind {
    case .original:
        return concreteAudioModeTrack(
            manager: manager,
            sequenceAudioMode: sequenceAudioMode,
            preferredSingleTrackMode: preferredSingleTrackMode
        ) == .original
    case .translation:
        return concreteAudioModeTrack(
            manager: manager,
            sequenceAudioMode: sequenceAudioMode,
            preferredSingleTrackMode: preferredSingleTrackMode
        ) == .translation
    case .combined:
        return concreteAudioModeTrack(
            manager: manager,
            sequenceAudioMode: sequenceAudioMode,
            preferredSingleTrackMode: preferredSingleTrackMode
        ) == nil
    case .other:
        return true
    }
}

@MainActor
private func applyAudioModePreference(
    for track: InteractiveChunk.AudioOption,
    manager: AudioModeManager?,
    sequenceAudioMode: inout AudioMode,
    preferredSingleTrackMode: inout SequenceTrack?
) {
    switch track.kind {
    case .original:
        preferredSingleTrackMode = .original
        if let manager {
            manager.setTracks(original: true, translation: false)
            sequenceAudioMode = manager.currentMode
        } else {
            sequenceAudioMode = .singleTrack(.original)
        }
    case .translation:
        preferredSingleTrackMode = .translation
        if let manager {
            manager.setTracks(original: false, translation: true)
            sequenceAudioMode = manager.currentMode
        } else {
            sequenceAudioMode = .singleTrack(.translation)
        }
    case .combined:
        preferredSingleTrackMode = nil
        if let manager {
            manager.enableSequenceMode()
            sequenceAudioMode = manager.currentMode
        } else {
            sequenceAudioMode = .sequence
        }
    case .other:
        break
    }
}

@MainActor
private func selectAudioTrack(
    id: String,
    in chunk: InteractiveChunk,
    manager: AudioModeManager?,
    sequenceAudioMode: inout AudioMode,
    selectedAudioTrackID: inout String?,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?,
    preferredSingleTrackMode: inout SequenceTrack?
) -> Bool {
    let previousTrackID = selectedAudioTrackID
    selectedAudioTrackID = id
    guard let track = chunk.audioOptions.first(where: { $0.id == id }) else { return false }
    let modeWasAlreadyAligned = audioModeMatchesSelectedTrack(
        track,
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode
    )
    preferredAudioKind = track.kind
    applyAudioModePreference(
        for: track,
        manager: manager,
        sequenceAudioMode: &sequenceAudioMode,
        preferredSingleTrackMode: &preferredSingleTrackMode
    )
    return !(previousTrackID == id && modeWasAlreadyAligned)
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
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?,
    selectedTimingURL: URL? = nil,
    selectedTimingSingleTrackMode: SequenceTrack? = nil,
    sequencePlanIsEmpty: Bool = true
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
    if let selectedTimingURL,
       let selectedTimingSingleTrack = selectedTimingSingleTrackMode,
       singleTrackModeForAudioURL(selectedTimingURL, in: chunk) == selectedTimingSingleTrack {
        if let endedURL {
            let combinedURLs = chunk.audioOptions.first(where: { $0.kind == .combined })?.streamURLs
                ?? [selectedTimingURL]
            if PlaybackEndedURLPolicy.endedURL(
                endedURL,
                belongsToSingleTrack: selectedTimingSingleTrack,
                in: combinedURLs
            ) {
                return selectedTimingSingleTrack
            }
        } else {
            return selectedTimingSingleTrack
        }
    }
    guard sequencePlanIsEmpty else {
        return nil
    }
    let completedURL: URL? = {
        if let endedURL {
            if !activeURLs.isEmpty,
               activeURLs.count != 1 || activeURLs.first != endedURL {
                return nil
            }
            return endedURL
        }
        guard activeURLs.count == 1 else { return nil }
        return activeURLs.first
    }()
    guard let completedURL else {
        return nil
    }
    if chunk.audioOptions.contains(where: { $0.kind == .original && $0.streamURLs.contains(completedURL) }) {
        return .original
    }
    if chunk.audioOptions.contains(where: { $0.kind == .translation && $0.streamURLs.contains(completedURL) }) {
        return .translation
    }
    if let combined = chunk.audioOptions.first(where: { $0.kind == .combined }) {
        if combined.streamURLs.first == completedURL {
            return .original
        }
        if combined.streamURLs.dropFirst().contains(completedURL) {
            return .translation
        }
    }
    return nil
}

@MainActor
private func playbackEndedURLBelongsToCurrentChunk(
    _ endedURL: URL,
    selectedOption: InteractiveChunk.AudioOption,
    chunk: InteractiveChunk,
    activeURLs: [URL],
    sequenceEnabled: Bool,
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?,
    selectedTimingURL: URL? = nil,
    selectedTimingSingleTrackMode: SequenceTrack? = nil
) -> Bool {
    if let selectedTimingURL,
       let selectedTimingSingleTrack = selectedTimingSingleTrackMode,
       singleTrackModeForAudioURL(selectedTimingURL, in: chunk) == selectedTimingSingleTrack {
        return PlaybackEndedURLPolicy.endedURL(
            endedURL,
            belongsTo: selectedOption,
            singleTrack: selectedTimingSingleTrack
        )
    }
    let activeSingleTrack = singleTrackModeForCompletedPlayback(
        endedURL: nil,
        chunk: chunk,
        activeURLs: activeURLs,
        sequenceEnabled: sequenceEnabled,
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind,
        selectedTimingURL: selectedTimingURL,
        selectedTimingSingleTrackMode: selectedTimingSingleTrackMode
    )
    return PlaybackEndedURLPolicy.endedURL(
        endedURL,
        belongsTo: selectedOption,
        singleTrack: activeSingleTrack ?? requestedSingleTrackMode(
            manager: manager,
            sequenceAudioMode: sequenceAudioMode,
            preferredSingleTrackMode: preferredSingleTrackMode,
            preferredAudioKind: preferredAudioKind
        )
    )
}

@MainActor
private func selectedLaneAudioIsActive(
    activeURL: URL?,
    chunk: InteractiveChunk,
    selectedOption: InteractiveChunk.AudioOption?,
    requestedSingleTrackMode: SequenceTrack?
) -> Bool {
    guard let activeURL else { return false }
    if let requestedSingleTrackMode {
        switch requestedSingleTrackMode {
        case .original:
            if chunk.audioOptions.contains(where: { $0.kind == .original && $0.streamURLs.contains(activeURL) }) {
                return true
            }
        case .translation:
            if chunk.audioOptions.contains(where: { $0.kind == .translation && $0.streamURLs.contains(activeURL) }) {
                return true
            }
        }
        return chunk.audioOptions.contains { option in
            guard option.kind == .combined else { return false }
            return PlaybackEndedURLPolicy.endedURL(
                activeURL,
                belongsTo: option,
                singleTrack: requestedSingleTrackMode
            )
        }
    }
    guard let selectedOption else { return false }
    return selectedOption.streamURLs.contains(activeURL)
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
private func playbackTimeForIntegration(
    baseTime: Double,
    chunk: InteractiveChunk,
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?,
    selectedAudioTrackID: String?,
    activeURL: URL?,
    durations: [URL: Double]
) -> Double {
    if requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) != nil {
        return baseTime
    }
    let track: InteractiveChunk.AudioOption? = {
        guard let selectedAudioTrackID else { return chunk.audioOptions.first }
        return chunk.audioOptions.first(where: { $0.id == selectedAudioTrackID }) ?? chunk.audioOptions.first
    }()
    guard let track else { return baseTime }
    let urls = track.streamURLs
    guard urls.count > 1,
          let activeURL,
          let activeIndex = urls.firstIndex(of: activeURL) else {
        return baseTime
    }
    let offset = urls.prefix(activeIndex).reduce(0.0) { partial, url in
        partial + (durations[url] ?? 0)
    }
    return offset + baseTime
}

@MainActor
private func shouldPrefetchSequenceAudio(
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?
) -> Bool {
    requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) == nil && manager?.currentMode == .sequence
}

@MainActor
private func preferredPrefetchAudioOption(
    for chunk: InteractiveChunk,
    manager: AudioModeManager,
    selectedAudioTrackID: String?,
    sequenceAudioMode: AudioMode = .sequence,
    preferredSingleTrackMode: SequenceTrack? = nil,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind? = nil
) -> InteractiveChunk.AudioOption? {
    effectiveSelectedAudioOption(
        for: chunk,
        manager: manager,
        selectedAudioTrackID: selectedAudioTrackID,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    )
}

@MainActor
private func prefetchAudioURL(
    for option: InteractiveChunk.AudioOption,
    manager: AudioModeManager?,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?
) -> URL? {
    guard option.kind == .combined,
          let requestedTrack = requestedSingleTrackMode(
            manager: manager,
            sequenceAudioMode: sequenceAudioMode,
            preferredSingleTrackMode: preferredSingleTrackMode,
            preferredAudioKind: preferredAudioKind
          ) else {
        return option.streamURLs.first
    }
    switch requestedTrack {
    case .original:
        return option.streamURLs.first
    case .translation:
        if option.streamURLs.count > 1 {
            return option.streamURLs[1]
        }
        return option.streamURLs.first
    }
}

@MainActor
private func activeAudioRolesForIntegration(
    availableRoles: Set<LanguageFlagRole>,
    manager: AudioModeManager,
    sequenceAudioMode: AudioMode,
    preferredSingleTrackMode: SequenceTrack?,
    preferredAudioKind: InteractiveChunk.AudioOption.Kind?,
    selectedKind: InteractiveChunk.AudioOption.Kind?
) -> Set<LanguageFlagRole> {
    switch manager.currentMode {
    case .sequence:
        return availableRoles.intersection([.original, .translation])
    case .singleTrack(.original):
        if availableRoles.contains(.original) {
            return [.original]
        }
    case .singleTrack(.translation):
        if availableRoles.contains(.translation) {
            return [.translation]
        }
    }
    if let track = requestedSingleTrackMode(
        manager: manager,
        sequenceAudioMode: sequenceAudioMode,
        preferredSingleTrackMode: preferredSingleTrackMode,
        preferredAudioKind: preferredAudioKind
    ) {
        switch track {
        case .original:
            return availableRoles.contains(.original) ? [.original] : []
        case .translation:
            return availableRoles.contains(.translation) ? [.translation] : []
        }
    }
    switch selectedKind {
    case .original:
        return availableRoles.contains(.original) ? [.original] : []
    case .translation:
        return availableRoles.contains(.translation) ? [.translation] : []
    case .combined, .other:
        return availableRoles.intersection([.original, .translation])
    case .none:
        return []
    }
}

@MainActor
private func toggleHeaderAudioRoleForIntegration(
    _ role: LanguageFlagRole,
    for chunk: InteractiveChunk,
    availableRoles: Set<LanguageFlagRole>,
    manager: AudioModeManager,
    selectedAudioTrackID: inout String?,
    preferredAudioKind: inout InteractiveChunk.AudioOption.Kind?,
    preferredSingleTrackMode: inout SequenceTrack?,
    sequenceAudioMode: inout AudioMode
) {
    let track: SequenceTrack = role == .original ? .original : .translation
    manager.toggle(track, availableTracks: availableRoles.sequenceTracks)
    sequenceAudioMode = manager.currentMode

    switch manager.currentMode {
    case .singleTrack(let selectedTrack):
        applySingleTrackSelection(
            selectedTrack,
            for: chunk,
            manager: manager,
            sequenceAudioMode: &sequenceAudioMode,
            selectedAudioTrackID: &selectedAudioTrackID,
            preferredAudioKind: &preferredAudioKind,
            preferredSingleTrackMode: &preferredSingleTrackMode
        )
    case .sequence:
        selectedAudioTrackID = manager.resolvePreferredTrackID(for: chunk)
        preferredSingleTrackMode = nil
        preferredAudioKind = selectedAudioTrackID.flatMap { id in
            chunk.audioOptions.first(where: { $0.id == id })?.kind
        }
    }
}

private extension Set where Element == LanguageFlagRole {
    var sequenceTracks: [SequenceTrack] {
        var tracks: [SequenceTrack] = []
        if contains(.original) {
            tracks.append(.original)
        }
        if contains(.translation) {
            tracks.append(.translation)
        }
        return tracks
    }
}

private func availableAudioRolesForIntegration(_ chunk: InteractiveChunk) -> Set<LanguageFlagRole> {
    let kinds = Set(chunk.audioOptions.map(\.kind))
    var roles = Set<LanguageFlagRole>()
    if kinds.contains(.original) {
        roles.insert(.original)
    }
    if kinds.contains(.translation) {
        roles.insert(.translation)
    }
    if chunk.audioOptions.contains(where: { $0.kind == .combined && !$0.streamURLs.isEmpty }) {
        roles.formUnion([.original, .translation])
    }
    return roles
}

private func availableTextTracksForIntegration(_ chunk: InteractiveChunk) -> [TextPlayerVariantKind] {
    var available: [TextPlayerVariantKind] = []
    if !available.contains(.original), chunkSupportsAudioTrack(.original, in: chunk) {
        available.append(.original)
    }
    if !available.contains(.translation), chunkSupportsAudioTrack(.translation, in: chunk) {
        available.append(.translation)
    }
    if available.isEmpty {
        return [.original]
    }
    return available
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
    let combinedBackedRoleChunk = InteractiveChunk(
        id: "chapter-roles",
        startSentence: nil,
        sentences: [.init(id: 0, displayIndex: 1)],
        audioOptions: [
            audioOption("combined-roles", kind: .combined, urls: [originalURL, translationURL]),
            audioOption("original-roles", kind: .original, urls: [originalURL])
        ]
    )
    requireEqual(
        availableAudioRolesForIntegration(combinedBackedRoleChunk),
        [.original, .translation],
        "Header audio role availability should expose Translation when a combined option carries the translation stream"
    )
    let lazyMetadataAudioBackedChunk = InteractiveChunk(
        id: "lazy-media-audio-backed",
        startSentence: 2656,
        sentences: [],
        audioOptions: [
            audioOption("original-lazy", kind: .original, urls: [originalURL]),
            audioOption("translation-lazy", kind: .translation, urls: [translationURL])
        ]
    )
    requireEqual(
        availableTextTracksForIntegration(lazyMetadataAudioBackedChunk),
        [.original, .translation],
        "Lazy chunks with dedicated audio lanes should keep Translation text track selectable while metadata loads"
    )
    let lazyMetadataCombinedBackedChunk = InteractiveChunk(
        id: "lazy-media-combined-backed",
        startSentence: 2666,
        sentences: [],
        audioOptions: [
            audioOption("combined-lazy", kind: .combined, urls: [originalURL, translationURL])
        ]
    )
    requireEqual(
        availableTextTracksForIntegration(lazyMetadataCombinedBackedChunk),
        [.original, .translation],
        "Lazy chunks with combined audio should keep Translation text track selectable while metadata loads"
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
    requireEqual(modeEvents.count, 1, "Last active track toggle should not emit a mode event")
    requireEqual(manager.currentMode, .singleTrack(.translation), "Last active translation toggle should stay translation-only")
    manager.toggle(.original, preservingPosition: transcriptProvider.index)
    requireEqual(modeEvents.count, 2, "Inactive companion track toggle should emit a mode event")
    requireEqual(modeEvents[1].0, .sequence, "Translation-only toggle should restore sequence mode")
    requireEqual(modeEvents[1].1, 6, "Transcript display position should be preserved")
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "combined", "Restored sequence mode should prefer combined audio")
    requireSequenceInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "combined",
        "Restored sequence mode should route combined selection to sequence audio"
    )
    requireEqual(
        usesCombinedQueue(
            isSequenceModeActive: true,
            audioModeManager: manager,
            selectedOption: chunk.audioOptions.first { $0.id == "combined" }
        ),
        true,
        "Restored sequence mode should add combined queue offsets"
    )

    manager.setTracks(original: true, translation: false, preservingPosition: nil)
    requireEqual(modeEvents.count, 3, "Preparing sequence restore should emit an original-only mode event")
    requireEqual(modeEvents[2].0, .singleTrack(.original), "Sequence restore setup should enter original-only mode")

    let pendingTarget = SentencePositionProvider.targetSentenceIndex(
        in: chunk,
        explicitIndex: nil,
        pendingJump: .init(chunkID: "chapter-1", sentenceNumber: 102)
    )
    manager.enableSequenceMode(preservingPosition: pendingTarget)
    requireEqual(modeEvents.count, 4, "Sequence restore should emit a mode event")
    requireEqual(modeEvents[3].0, .sequence, "Pending jump restore should return to sequence mode")
    requireEqual(modeEvents[3].1, 2, "Pending jump should preserve the resolved local sentence index")
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
    requireEqual(
        requestedSingleTrackMode(
            manager: nil,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .original,
            preferredAudioKind: .combined,
            loadedSingleTrackPlaybackMode: .translation
        ),
        .translation,
        "Loaded translation-only lane should beat stale preferred state at batch EOF"
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
    let playbackTimeSequenceManager = AudioModeManager()
    let durableSingleTrackPlaybackTime = playbackTimeForIntegration(
        baseTime: 1.25,
        chunk: nextBatch,
        manager: playbackTimeSequenceManager,
        sequenceAudioMode: .sequence,
        preferredSingleTrackMode: .translation,
        preferredAudioKind: .combined,
        selectedAudioTrackID: "combined-next",
        activeURL: translationURL,
        durations: [originalURL: 8.0, translationURL: 4.0]
    )
    requireEqual(
        durableSingleTrackPlaybackTime,
        1.25,
        "Single-track playback time should ignore hidden-track queue offsets even if the manager briefly reports sequence at a batch boundary"
    )
    let singleFileCombinedBatch = InteractiveChunk(
        id: "chapter-2-single-file-combined",
        startSentence: 104,
        sentences: [
            .init(id: 104, displayIndex: 104, startGate: 4.0, originalStartGate: 0.0)
        ],
        audioOptions: [
            audioOption("combined-single-file-next", kind: .combined, urls: [translationURL])
        ]
    )
    requireEqual(
        useCombinedPhasesForIntegration(
            chunk: singleFileCombinedBatch,
            manager: playbackTimeSequenceManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined,
            selectedAudioTrackID: "combined-single-file-next",
            activeURL: translationURL
        ),
        false,
        "Single-track rendering should not re-enter combined-phase timing when a hydrated next batch still points at a combined audio option"
    )
    requireEqual(
        useCombinedPhasesForIntegration(
            chunk: singleFileCombinedBatch,
            manager: playbackTimeSequenceManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            selectedAudioTrackID: "combined-single-file-next",
            activeURL: translationURL
        ),
        true,
        "Sequence rendering should keep combined-phase timing for one-file combined batches"
    )
    let sequencePlaybackTime = playbackTimeForIntegration(
        baseTime: 1.25,
        chunk: nextBatch,
        manager: playbackTimeSequenceManager,
        sequenceAudioMode: .sequence,
        preferredSingleTrackMode: nil,
        preferredAudioKind: .combined,
        selectedAudioTrackID: "combined-next",
        activeURL: translationURL,
        durations: [originalURL: 8.0, translationURL: 4.0]
    )
    requireEqual(
        sequencePlaybackTime,
        9.25,
        "Sequence playback time should still include prior queue-file offsets when no single-track lane is requested"
    )
    requireEqual(
        activeAudioRolesForIntegration(
            availableRoles: [.original, .translation],
            manager: playbackTimeSequenceManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined,
            selectedKind: .combined
        ),
        [.original, .translation],
        "Header active audio roles should trust the live manager and show both roles during true sequence playback"
    )
    requireEqual(
        activeAudioRolesForIntegration(
            availableRoles: [.original, .translation],
            manager: playbackTimeSequenceManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            selectedKind: .combined
        ),
        [.original, .translation],
        "Header active audio roles should still show both roles for true sequence playback"
    )
    let headerToggleAvailableRoles: Set<LanguageFlagRole> = [.original, .translation]
    let headerToggleManager = AudioModeManager()
    var headerToggleSelectedTrackID: String? = "combined-next"
    var headerTogglePreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    var headerTogglePreferredSingleTrackMode: SequenceTrack?
    var headerToggleSequenceMode: AudioMode = .sequence
    toggleHeaderAudioRoleForIntegration(
        .original,
        for: nextBatch,
        availableRoles: headerToggleAvailableRoles,
        manager: headerToggleManager,
        selectedAudioTrackID: &headerToggleSelectedTrackID,
        preferredAudioKind: &headerTogglePreferredKind,
        preferredSingleTrackMode: &headerTogglePreferredSingleTrackMode,
        sequenceAudioMode: &headerToggleSequenceMode
    )
    requireEqual(
        headerToggleManager.currentMode,
        .singleTrack(.translation),
        "Header role pills should disable Original and keep Translation active when both roles are active and Original is tapped"
    )
    requireEqual(
        headerToggleSelectedTrackID,
        "translation-next",
        "Header role pill toggle should switch selected audio id to Translation after disabling Original"
    )
    toggleHeaderAudioRoleForIntegration(
        .translation,
        for: nextBatch,
        availableRoles: headerToggleAvailableRoles,
        manager: headerToggleManager,
        selectedAudioTrackID: &headerToggleSelectedTrackID,
        preferredAudioKind: &headerTogglePreferredKind,
        preferredSingleTrackMode: &headerTogglePreferredSingleTrackMode,
        sequenceAudioMode: &headerToggleSequenceMode
    )
    requireEqual(
        headerToggleManager.currentMode,
        .singleTrack(.translation),
        "Header role pills should keep the only active Translation role enabled when it is tapped"
    )
    requireEqual(
        headerToggleSelectedTrackID,
        "translation-next",
        "Header role pill toggle should keep selected audio id on Translation when the last active role is tapped"
    )
    toggleHeaderAudioRoleForIntegration(
        .original,
        for: nextBatch,
        availableRoles: headerToggleAvailableRoles,
        manager: headerToggleManager,
        selectedAudioTrackID: &headerToggleSelectedTrackID,
        preferredAudioKind: &headerTogglePreferredKind,
        preferredSingleTrackMode: &headerTogglePreferredSingleTrackMode,
        sequenceAudioMode: &headerToggleSequenceMode
    )
    requireEqual(
        headerToggleManager.currentMode,
        .sequence,
        "Header role pills should restore both roles when tapping the inactive Original role"
    )
    requireEqual(
        headerToggleSelectedTrackID,
        "combined-next",
        "Header role pill toggle should switch selected audio id to Combined after both roles are active"
    )
    toggleHeaderAudioRoleForIntegration(
        .translation,
        for: nextBatch,
        availableRoles: headerToggleAvailableRoles,
        manager: headerToggleManager,
        selectedAudioTrackID: &headerToggleSelectedTrackID,
        preferredAudioKind: &headerTogglePreferredKind,
        preferredSingleTrackMode: &headerTogglePreferredSingleTrackMode,
        sequenceAudioMode: &headerToggleSequenceMode
    )
    requireEqual(
        headerToggleManager.currentMode,
        .singleTrack(.original),
        "Header role pills should disable Translation and keep Original active when both roles are active and Translation is tapped"
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
    let wrongSingleTrackManager = AudioModeManager()
    wrongSingleTrackManager.setTracks(original: true, translation: false)
    requireEqual(
        requestedSingleTrackMode(
            manager: wrongSingleTrackManager,
            sequenceAudioMode: .singleTrack(.original),
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .original
        ),
        .translation,
        "Remembered translation-only lane should beat a stale original-only manager state at a batch boundary"
    )
    var wrongManagerSelectedTrackID: String? = "original-next"
    var wrongManagerPreferredKind: InteractiveChunk.AudioOption.Kind? = .original
    var wrongManagerPreferredSingleTrack: SequenceTrack? = .translation
    var wrongManagerSequenceAudioMode: AudioMode = .singleTrack(.original)
    if let track = requestedSingleTrackMode(
        manager: wrongSingleTrackManager,
        sequenceAudioMode: wrongManagerSequenceAudioMode,
        preferredSingleTrackMode: wrongManagerPreferredSingleTrack,
        preferredAudioKind: wrongManagerPreferredKind
    ) {
        applySingleTrackSelection(
            track,
            for: nextBatch,
            manager: wrongSingleTrackManager,
            sequenceAudioMode: &wrongManagerSequenceAudioMode,
            selectedAudioTrackID: &wrongManagerSelectedTrackID,
            preferredAudioKind: &wrongManagerPreferredKind,
            preferredSingleTrackMode: &wrongManagerPreferredSingleTrack
        )
    }
    requireEqual(
        wrongManagerSelectedTrackID,
        "translation-next",
        "Batch repair should restore the translation audio option when transient manager state reports original"
    )
    requireEqual(
        wrongManagerSequenceAudioMode,
        .singleTrack(.translation),
        "Batch repair should put the sequence controller back on the durable translation lane"
    )
    var pickerSelectedTrackID: String? = "translation-next"
    var pickerPreferredKind: InteractiveChunk.AudioOption.Kind? = .translation
    var pickerPreferredSingleTrack: SequenceTrack?
    var pickerSequenceAudioMode: AudioMode = .sequence
    let pickerManager = AudioModeManager()
    requireEqual(
        selectAudioTrack(
            id: "translation-next",
            in: nextBatch,
            manager: pickerManager,
            sequenceAudioMode: &pickerSequenceAudioMode,
            selectedAudioTrackID: &pickerSelectedTrackID,
            preferredAudioKind: &pickerPreferredKind,
            preferredSingleTrackMode: &pickerPreferredSingleTrack
        ),
        true,
        "Selecting an already checked translation option should still reprepare when the shared audio mode drifted back to sequence"
    )
    requireEqual(
        pickerManager.currentMode,
        .singleTrack(.translation),
        "iPad audio picker selection should stamp translation-only into the shared audio mode before batch handoff"
    )
    requireEqual(
        pickerSequenceAudioMode,
        .singleTrack(.translation),
        "iPad audio picker selection should repair sequence-controller mode before playback prepares"
    )
    requireEqual(
        pickerPreferredSingleTrack,
        .translation,
        "iPad audio picker selection should persist translation-only as the durable batch lane"
    )
    let staleViewManager = AudioModeManager()
    requireEqual(
        requestedSingleTrackMode(
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            chunk: nextBatch,
            selectedTimingURL: translationURL,
            selectedTimingSingleTrackMode: .translation
        ),
        .translation,
        "Selected translation timing lane should survive a stale combined reset before batch rendering refreshes"
    )
    requireEqual(
        requestedSingleTrackMode(
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            chunk: nextBatch,
            selectedTimingURL: nil,
            selectedTimingSingleTrackMode: .translation
        ),
        .translation,
        "Selected translation timing lane should survive no-URL EOF recovery at a batch boundary"
    )
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
    requireEqual(
        shouldPrefetchSequenceAudio(
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined
        ),
        false,
        "Remembered translation-only lane should stop next-batch prefetch from warming sequence audio after manager reset"
    )
    requireEqual(
        preferredPrefetchAudioOption(
            for: nextBatch,
            manager: staleViewManager,
            selectedAudioTrackID: "combined-next",
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined
        )?.id,
        "translation-next",
        "Remembered translation-only lane should make next-batch prefetch choose translation audio"
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
    requireEqual(
        playbackEndedURLBelongsToCurrentChunk(
            originalURL,
            selectedOption: combinedOnlyOption,
            chunk: combinedOnlyNextBatch,
            activeURLs: [translationURL],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined
        ),
        false,
        "Active translation-only URL should reject stale hidden original EOF before the next batch can reset to combined"
    )
    requireEqual(
        playbackEndedURLBelongsToCurrentChunk(
            originalURL,
            selectedOption: combinedOnlyOption,
            chunk: combinedOnlyNextBatch,
            activeURLs: [],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            selectedTimingURL: translationURL,
            selectedTimingSingleTrackMode: .translation
        ),
        false,
        "Selected translation timing URL should reject stale hidden original EOF after AVPlayer clears active state"
    )
    requireEqual(
        playbackEndedURLBelongsToCurrentChunk(
            translationURL,
            selectedOption: combinedOnlyOption,
            chunk: combinedOnlyNextBatch,
            activeURLs: [originalURL, translationURL],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            selectedTimingURL: originalURL,
            selectedTimingSingleTrackMode: nil
        ),
        true,
        "Combined fallback queues should not treat the first selected timing URL as single-track evidence"
    )
    requireEqual(
        playbackEndedURLBelongsToCurrentChunk(
            translationURL,
            selectedOption: combinedOnlyOption,
            chunk: combinedOnlyNextBatch,
            activeURLs: [translationURL],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined
        ),
        true,
        "Active translation-only URL should accept its own EOF for batch handoff"
    )
    requireEqual(
        singleTrackModeForCompletedPlayback(
            endedURL: translationURL,
            chunk: combinedOnlyNextBatch,
            activeURLs: [],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            selectedTimingURL: translationURL,
            selectedTimingSingleTrackMode: .translation
        ),
        .translation,
        "Selected translation timing URL should preserve the lane when EOF active URLs are empty"
    )
    requireEqual(
        requestedSingleTrackMode(
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            chunk: combinedOnlyNextBatch,
            sequenceEnabled: false,
            activeURLs: [translationURL]
        ),
        .translation,
        "Loaded single translation URL should preserve the selected lane even when manager and picker state reset to combined at a batch boundary"
    )
    requireNil(
        requestedSingleTrackMode(
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            chunk: combinedOnlyNextBatch,
            sequenceEnabled: false,
            activeURLs: [translationURL],
            sequencePlanIsEmpty: false
        ),
        "Finished sequence batches must not infer translation-only selection from the final translation URL"
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
    requireNil(
        singleTrackModeForCompletedPlayback(
            endedURL: translationURL,
            chunk: combinedOnlyNextBatch,
            activeURLs: [translationURL],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined,
            sequencePlanIsEmpty: false
        ),
        "Sequence EOF handoff should keep all-track selection instead of pinning the next batch to translation-only"
    )
    requireEqual(
        singleTrackModeForCompletedPlayback(
            endedURL: nil,
            chunk: combinedOnlyNextBatch,
            activeURLs: [translationURL],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined
        ),
        .translation,
        "Single-track EOF handoff should preserve translation from the active URL when the ended callback lost its URL"
    )
    requireNil(
        singleTrackModeForCompletedPlayback(
            endedURL: nil,
            chunk: combinedOnlyNextBatch,
            activeURLs: [originalURL, translationURL],
            sequenceEnabled: false,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: nil,
            preferredAudioKind: .combined
        ),
        "Missing EOF URL should not guess a lane from a multi-file active queue"
    )
    var eofResolvedPreferredSingleTrack: SequenceTrack?
    if let staleCompletedLane {
        eofResolvedPreferredSingleTrack = staleCompletedLane
    }
    requireEqual(
        eofResolvedPreferredSingleTrack,
        .translation,
        "Single-track EOF resolution should stamp the durable lane before stale URL guards or next-batch selection run"
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
    requireEqual(
        prefetchAudioURL(
            for: combinedOnlyOption,
            manager: staleViewManager,
            sequenceAudioMode: .sequence,
            preferredSingleTrackMode: .translation,
            preferredAudioKind: .combined
        ),
        translationURL,
        "Combined-only translation prefetch should warm the translation stream instead of the hidden original stream"
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
    let batchBridgePlaceholder = InteractiveChunk(
        id: "chapter-2-placeholder",
        startSentence: 104,
        sentences: [],
        audioOptions: [
            audioOption("translation-placeholder", kind: .translation, urls: [translationURL]),
            audioOption("combined-placeholder", kind: .combined, urls: [originalURL, translationURL])
        ]
    )
    let placeholderBridgeManager = AudioModeManager()
    var placeholderBridgeVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var placeholderBridgeHasCustomTrackSelection = false
    var placeholderBridgeSelectedTrackID: String? = "combined-placeholder"
    var placeholderBridgeSequenceMode: AudioMode = .sequence
    var placeholderBridgePreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    requireEqual(
        restoreSingleTrackModeFromViewModelPreferenceIfNeeded(
            for: batchBridgePlaceholder,
            availableTracks: [],
            manager: placeholderBridgeManager,
            visibleTracks: &placeholderBridgeVisibleTracks,
            hasCustomTrackSelection: &placeholderBridgeHasCustomTrackSelection,
            selectedAudioTrackID: &placeholderBridgeSelectedTrackID,
            preferredSingleTrackMode: .translation,
            sequenceAudioMode: &placeholderBridgeSequenceMode,
            preferredAudioKind: &placeholderBridgePreferredKind
        ),
        true,
        "Batch handoff should restore translation-only mode from view-model state even before text tracks hydrate"
    )
    requireEqual(
        placeholderBridgeManager.currentMode,
        .singleTrack(.translation),
        "Placeholder batch bridge should put the SwiftUI audio manager back into translation-only mode before defaults run"
    )
    requireEqual(
        placeholderBridgeVisibleTracks,
        [.translation],
        "Placeholder batch bridge should keep the transcript pinned to the selected single track"
    )
    requireEqual(
        placeholderBridgeSelectedTrackID,
        "translation-placeholder",
        "Placeholder batch bridge should resolve the selected audio id to the translation option"
    )
    let hydratedBatchBridgeManager = AudioModeManager()
    var hydratedBatchBridgeVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var hydratedBatchBridgeHasCustomTrackSelection = false
    var hydratedBatchBridgeSelectedTrackID: String? = "combined-next"
    var hydratedBatchBridgeSequenceMode: AudioMode = .sequence
    var hydratedBatchBridgePreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    requireEqual(
        restoreSingleTrackModeFromViewModelPreferenceIfNeeded(
            for: nextBatch,
            availableTracks: [.original, .translation, .transliteration],
            manager: hydratedBatchBridgeManager,
            visibleTracks: &hydratedBatchBridgeVisibleTracks,
            hasCustomTrackSelection: &hydratedBatchBridgeHasCustomTrackSelection,
            selectedAudioTrackID: &hydratedBatchBridgeSelectedTrackID,
            preferredSingleTrackMode: .translation,
            sequenceAudioMode: &hydratedBatchBridgeSequenceMode,
            preferredAudioKind: &hydratedBatchBridgePreferredKind
        ),
        true,
        "Hydrated batch availability should not expand back to All when the view model remembers translation-only"
    )
    requireEqual(
        hydratedBatchBridgeSequenceMode,
        .singleTrack(.translation),
        "Hydrated batch bridge should restore sequence controller mode before playback prepares"
    )
    requireEqual(
        hydratedBatchBridgeVisibleTracks,
        [.translation],
        "Hydrated batch bridge should preserve the selected transcript lane instead of showing all tracks"
    )
    requireEqual(
        hydratedBatchBridgeSelectedTrackID,
        "translation-next",
        "Hydrated batch bridge should repair the selected audio id before playback prepares"
    )
    let durableOnlyBatchBridgeManager = AudioModeManager()
    var durableOnlyBatchBridgeVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var durableOnlyBatchBridgeHasCustomTrackSelection = false
    var durableOnlyBatchBridgeSelectedTrackID: String? = "combined-next"
    var durableOnlyBatchBridgeSequenceMode: AudioMode = .sequence
    var durableOnlyBatchBridgePreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    requireEqual(
        restoreSingleTrackModeFromViewModelPreferenceIfNeeded(
            for: nextBatch,
            availableTracks: [.original, .translation, .transliteration],
            manager: durableOnlyBatchBridgeManager,
            visibleTracks: &durableOnlyBatchBridgeVisibleTracks,
            hasCustomTrackSelection: &durableOnlyBatchBridgeHasCustomTrackSelection,
            selectedAudioTrackID: &durableOnlyBatchBridgeSelectedTrackID,
            preferredSingleTrackMode: nil,
            durableSingleTrackPlaybackMode: .translation,
            sequenceAudioMode: &durableOnlyBatchBridgeSequenceMode,
            preferredAudioKind: &durableOnlyBatchBridgePreferredKind
        ),
        true,
        "Hydrated batch bridge should restore translation-only from durable state even when preferred state was cleared"
    )
    requireEqual(
        durableOnlyBatchBridgeManager.currentMode,
        .singleTrack(.translation),
        "Durable-only batch bridge should put the SwiftUI manager back on translation before defaults run"
    )
    requireEqual(
        durableOnlyBatchBridgeSequenceMode,
        .singleTrack(.translation),
        "Durable-only batch bridge should restore sequence-controller mode before playback prepares"
    )
    requireEqual(
        durableOnlyBatchBridgeVisibleTracks,
        [.translation],
        "Durable-only batch bridge should keep rendered text on the selected translation lane"
    )
    requireEqual(
        durableOnlyBatchBridgeSelectedTrackID,
        "translation-next",
        "Durable-only batch bridge should repair the chunk-local audio id before playback prepares"
    )
    let passiveHydratedManager = AudioModeManager()
    var passiveHydratedVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var passiveHydratedHasCustomTrackSelection = false
    var passiveHydratedSelectedTrackID: String? = "combined-next"
    var passiveHydratedPreferredKind: InteractiveChunk.AudioOption.Kind? = .combined
    var passiveHydratedPreferredSingleTrack: SequenceTrack? = .translation
    var passiveHydratedSequenceMode: AudioMode = .sequence
    requireEqual(
        synchronizeAudioModeWithVisibleTextTracks(
            for: nextBatch,
            availableTracks: [.original, .translation, .transliteration],
            manager: passiveHydratedManager,
            visibleTracks: &passiveHydratedVisibleTracks,
            hasCustomTrackSelection: &passiveHydratedHasCustomTrackSelection,
            selectedAudioTrackID: &passiveHydratedSelectedTrackID,
            preferredAudioKind: &passiveHydratedPreferredKind,
            preferredSingleTrackMode: &passiveHydratedPreferredSingleTrack,
            sequenceAudioMode: &passiveHydratedSequenceMode
        ),
        true,
        "Passive hydrated-batch sync should not expand a remembered translation-only lane back to combined"
    )
    requireEqual(
        passiveHydratedVisibleTracks,
        [.translation],
        "Passive hydrated-batch sync should keep rendered tracks pinned to the selected translation lane"
    )
    requireEqual(
        passiveHydratedSelectedTrackID,
        "translation-next",
        "Passive hydrated-batch sync should repair the selected audio option before rendering refreshes"
    )
    requireEqual(
        passiveHydratedSequenceMode,
        .singleTrack(.translation),
        "Passive hydrated-batch sync should restore single-track sequence state"
    )
    var explicitHydratedVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    var explicitHydratedHasCustomTrackSelection = true
    var explicitHydratedSelectedTrackID: String? = "translation-next"
    var explicitHydratedPreferredKind: InteractiveChunk.AudioOption.Kind? = .translation
    var explicitHydratedPreferredSingleTrack: SequenceTrack? = .translation
    var explicitHydratedSequenceMode: AudioMode = .singleTrack(.translation)
    requireEqual(
        synchronizeAudioModeWithVisibleTextTracks(
            for: nextBatch,
            availableTracks: [.original, .translation, .transliteration],
            manager: passiveHydratedManager,
            visibleTracks: &explicitHydratedVisibleTracks,
            hasCustomTrackSelection: &explicitHydratedHasCustomTrackSelection,
            selectedAudioTrackID: &explicitHydratedSelectedTrackID,
            preferredAudioKind: &explicitHydratedPreferredKind,
            preferredSingleTrackMode: &explicitHydratedPreferredSingleTrack,
            sequenceAudioMode: &explicitHydratedSequenceMode,
            allowExpandingSingleTrackAudio: true
        ),
        true,
        "Explicit text-track toggle should still be able to expand translation-only playback to combined"
    )
    requireEqual(
        explicitHydratedSequenceMode,
        .sequence,
        "Explicit text-track expansion should restore sequence audio mode"
    )
    let customLifecycleManager = AudioModeManager()
    customLifecycleManager.setTracks(original: false, translation: true)
    var customLifecycleVisibleTracks: Set<TextPlayerVariantKind> = [.original, .translation]
    var customLifecycleHasCustomTrackSelection = true
    var customLifecycleSelectedTrackID: String? = "translation-next"
    var customLifecyclePreferredKind: InteractiveChunk.AudioOption.Kind? = .translation
    var customLifecyclePreferredSingleTrack: SequenceTrack? = .translation
    var customLifecycleSequenceMode: AudioMode = .singleTrack(.translation)
    let customLifecycleShouldExpand = shouldPreferCustomMultiTrackSelection(
        availableTracks: [.original, .translation, .transliteration],
        visibleTracks: customLifecycleVisibleTracks,
        hasCustomTrackSelection: customLifecycleHasCustomTrackSelection
    )
    requireEqual(
        customLifecycleShouldExpand,
        true,
        "Lifecycle setup should recognize an explicit Original + Translation text-track selection as a combined playback request"
    )
    requireEqual(
        customLifecycleShouldExpand
            ? false
            : restoreSingleTrackModeFromViewModelPreferenceIfNeeded(
                for: nextBatch,
                availableTracks: [.original, .translation, .transliteration],
                manager: customLifecycleManager,
                visibleTracks: &customLifecycleVisibleTracks,
                hasCustomTrackSelection: &customLifecycleHasCustomTrackSelection,
                selectedAudioTrackID: &customLifecycleSelectedTrackID,
                preferredSingleTrackMode: customLifecyclePreferredSingleTrack,
                durableSingleTrackPlaybackMode: .translation,
                sequenceAudioMode: &customLifecycleSequenceMode,
                preferredAudioKind: &customLifecyclePreferredKind
            ),
        false,
        "Lifecycle setup must not let a stale durable single-track lane override an explicit text-track expansion"
    )
    requireEqual(
        synchronizeAudioModeWithVisibleTextTracks(
            for: nextBatch,
            availableTracks: [.original, .translation, .transliteration],
            manager: customLifecycleManager,
            visibleTracks: &customLifecycleVisibleTracks,
            hasCustomTrackSelection: &customLifecycleHasCustomTrackSelection,
            selectedAudioTrackID: &customLifecycleSelectedTrackID,
            preferredAudioKind: &customLifecyclePreferredKind,
            preferredSingleTrackMode: &customLifecyclePreferredSingleTrack,
            sequenceAudioMode: &customLifecycleSequenceMode,
            allowExpandingSingleTrackAudio: customLifecycleShouldExpand
        ),
        true,
        "Lifecycle setup should preserve explicit multi-track selection by expanding audio back to sequence"
    )
    requireEqual(
        customLifecycleSequenceMode,
        .sequence,
        "Custom multi-track lifecycle setup should leave the sequence controller in combined playback mode"
    )
    requireEqual(
        customLifecycleVisibleTracks,
        [.original, .translation],
        "Custom multi-track lifecycle setup should not collapse visible tracks back to Translation-only"
    )
    let staleVisibleLifecycleManager = AudioModeManager()
    staleVisibleLifecycleManager.setTracks(original: true, translation: false)
    var staleVisibleTracks: Set<TextPlayerVariantKind> = [.translation]
    var staleVisibleHasCustomTrackSelection = true
    var staleVisibleSelectedTrackID: String? = "original-next"
    var staleVisiblePreferredKind: InteractiveChunk.AudioOption.Kind? = .original
    var staleVisiblePreferredSingleTrack: SequenceTrack? = .original
    var staleVisibleSequenceMode: AudioMode = .singleTrack(.original)
    let restoredVisibleTranslation = restoreSingleTrackModeFromVisibleSelectionIfNeeded(
        for: nextBatch,
        availableTracks: [.original, .translation, .transliteration],
        manager: staleVisibleLifecycleManager,
        visibleTracks: &staleVisibleTracks,
        hasCustomTrackSelection: &staleVisibleHasCustomTrackSelection,
        selectedAudioTrackID: &staleVisibleSelectedTrackID,
        sequenceAudioMode: &staleVisibleSequenceMode,
        preferredAudioKind: &staleVisiblePreferredKind,
        preferredSingleTrackMode: &staleVisiblePreferredSingleTrack
    )
    requireEqual(
        restoredVisibleTranslation,
        true,
        "Lifecycle track availability refresh should honor the visible Translation-only user selection before stale Original memory"
    )
    requireEqual(
        restoredVisibleTranslation
            ? false
            : restoreSingleTrackModeFromViewModelPreferenceIfNeeded(
                for: nextBatch,
                availableTracks: [.original, .translation, .transliteration],
                manager: staleVisibleLifecycleManager,
                visibleTracks: &staleVisibleTracks,
                hasCustomTrackSelection: &staleVisibleHasCustomTrackSelection,
                selectedAudioTrackID: &staleVisibleSelectedTrackID,
                preferredSingleTrackMode: .original,
                durableSingleTrackPlaybackMode: .original,
                loadedSingleTrackPlaybackMode: .original,
                sequenceAudioMode: &staleVisibleSequenceMode,
                preferredAudioKind: &staleVisiblePreferredKind
            ),
        false,
        "Stale Original lifecycle memory must not run after visible Translation-only selection is restored"
    )
    requireEqual(
        staleVisibleLifecycleManager.currentMode,
        .singleTrack(.translation),
        "Visible Translation-only lifecycle refresh should re-pin audio mode to Translation"
    )
    requireEqual(
        staleVisibleSelectedTrackID,
        "translation-next",
        "Visible Translation-only lifecycle refresh should repair stale Original selected audio id"
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
    requireEqual(
        selectedLaneAudioIsActive(
            activeURL: originalURL,
            chunk: nextBatch,
            selectedOption: nextBatch.audioOptions.first(where: { $0.kind == .combined }),
            requestedSingleTrackMode: .translation
        ),
        false,
        "Translation-only render anchors must not release on a hidden original stream from the selected combined option"
    )
    requireEqual(
        selectedLaneAudioIsActive(
            activeURL: translationURL,
            chunk: nextBatch,
            selectedOption: nextBatch.audioOptions.first(where: { $0.kind == .combined }),
            requestedSingleTrackMode: .translation
        ),
        true,
        "Translation-only render anchors should release only when the selected lane stream reaches the batch target"
    )
    requireEqual(
        selectedLaneAudioIsActive(
            activeURL: originalURL,
            chunk: nextBatch,
            selectedOption: nextBatch.audioOptions.first(where: { $0.kind == .original }),
            requestedSingleTrackMode: .translation
        ),
        false,
        "Translation-only render anchors must reject a stale dedicated original option after the batch selection refreshes"
    )
    requireEqual(
        selectedLaneAudioIsActive(
            activeURL: translationURL,
            chunk: nextBatch,
            selectedOption: nextBatch.audioOptions.first(where: { $0.kind == .original }),
            requestedSingleTrackMode: .translation
        ),
        true,
        "Translation-only render anchors should still accept the translation stream after the selected option refreshes to original"
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
    requireEqual(
        playbackRequestAfterQueueEnd(
            hadURLAwareHandler: true,
            wasPlaybackRequested: true
        ),
        true,
        "URL-aware EOF handoff should keep playback intent alive for the view model to load the next batch"
    )
    requireEqual(
        playbackRequestAfterQueueEnd(
            hadURLAwareHandler: false,
            wasPlaybackRequested: true
        ),
        false,
        "End-of-book EOF without a URL-aware handoff should clear playback intent"
    )
    let sameURLHandoff = sameURLReloadState(
        urls: [translationURL],
        activeURLs: [translationURL],
        activeURL: nil,
        wasPlaybackRequested: true,
        autoPlay: false,
        forceNoAutoPlay: true,
        preservePlaybackRequested: true
    )
    requireEqual(
        sameURLHandoff.isPlaybackRequested,
        true,
        "Same-URL batch handoff should preserve reader playback intent while the selected lane is reasserted"
    )
    requireEqual(
        sameURLHandoff.activeURL,
        translationURL,
        "Same-URL batch handoff should republish the active URL when the player item is reused"
    )

    manager.setTracks(original: false, translation: true, preservingPosition: 17)
    let timeProvider = SentencePositionProvider.from(
        sequenceController: sequenceController,
        transcriptDisplayIndex: { nil },
        timeBasedIndex: { 3 }
    )
    manager.toggle(kind: .combined, preservingPosition: timeProvider.index)
    requireEqual(modeEvents.count, 6, "Single-track to combined restore should emit a mode event")
    requireEqual(modeEvents[5].0, .sequence, "Combined kind should restore sequence mode")
    requireEqual(modeEvents[5].1, 3, "Time fallback position should be preserved")

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
