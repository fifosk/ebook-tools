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

struct InteractiveChunk: Identifiable {
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
    let audioOptions: [AudioOption]
}

@MainActor
private func fail(_ message: String) -> Never {
    fputs("AudioModeManager check failed: \(message)\n", stderr)
    exit(1)
}

@MainActor
private func requireEqual<T: Equatable>(_ actual: T, _ expected: T, _ message: String) {
    if actual != expected {
        fail("\(message). Expected \(expected), got \(actual).")
    }
}

@MainActor
private func requireTrue(_ value: Bool, _ message: String) {
    if !value {
        fail(message)
    }
}

@MainActor
private func requireFalse(_ value: Bool, _ message: String) {
    if value {
        fail(message)
    }
}

@MainActor
private func requireInstruction(
    _ instruction: ResolvedAudioInstruction?,
    sequenceID expectedID: String,
    _ message: String
) {
    guard case .sequence(let option)? = instruction else {
        fail("\(message). Expected sequence instruction.")
    }
    requireEqual(option.id, expectedID, "\(message) sequence id")
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
private func requireInstruction(
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

@MainActor
private func runChecks() {
    let originalURL = URL(string: "https://example.invalid/original.m4a")!
    let translationURL = URL(string: "https://example.invalid/translation.m4a")!
    let combined = audioOption("combined", kind: .combined, urls: [originalURL, translationURL])
    let original = audioOption("original", kind: .original, urls: [originalURL])
    let translation = audioOption("translation", kind: .translation, urls: [translationURL])
    let chunk = InteractiveChunk(id: "chunk-1", audioOptions: [combined, original, translation])

    let manager = AudioModeManager()
    var events: [(AudioMode, Int?)] = []
    manager.onModeChange = { mode, sentenceIndex in
        events.append((mode, sentenceIndex))
    }

    requireTrue(manager.isOriginalEnabled, "Initial state should enable original")
    requireTrue(manager.isTranslationEnabled, "Initial state should enable translation")
    requireTrue(manager.isSequenceMode, "Initial state should be sequence mode")
    requireEqual(manager.currentMode, .sequence, "Initial mode")
    requireEqual(manager.preferredTrack, .original, "Sequence mode should prefer original")

    manager.toggle(.original, preservingPosition: 4)
    requireFalse(manager.isOriginalEnabled, "Toggling original off should disable original")
    requireTrue(manager.isTranslationEnabled, "Translation should remain enabled")
    requireEqual(manager.currentMode, .singleTrack(.translation), "Original toggle should enter translation-only mode")
    requireEqual(events.count, 1, "First mode transition count")
    requireEqual(events[0].0, .singleTrack(.translation), "First transition mode")
    requireEqual(events[0].1, 4, "First transition preserved sentence")

    manager.toggle(.translation, preservingPosition: 5)
    requireFalse(manager.isOriginalEnabled, "Toggling the only enabled translation track should leave original disabled")
    requireTrue(manager.isTranslationEnabled, "Toggling the only enabled translation track should keep translation")
    requireEqual(manager.currentMode, .singleTrack(.translation), "Last active translation toggle should stay translation-only")
    requireEqual(events.count, 1, "Last-active toggle should not emit a mode transition")

    manager.toggle(.original, preservingPosition: 6)
    requireTrue(manager.isOriginalEnabled, "Toggling inactive original should enable original")
    requireTrue(manager.isTranslationEnabled, "Toggling inactive original should keep translation")
    requireEqual(manager.currentMode, .sequence, "Inactive original toggle should restore both tracks")
    requireEqual(manager.preferredTrack, .original, "Restored sequence mode should prefer original")
    requireEqual(events.count, 2, "Second mode transition count")
    requireEqual(events[1].0, .sequence, "Second transition mode")
    requireEqual(events[1].1, 6, "Second transition preserved sentence")

    manager.toggle(.translation, preservingPosition: 7)
    requireTrue(manager.isOriginalEnabled, "Toggling translation from sequence should keep original enabled")
    requireFalse(manager.isTranslationEnabled, "Toggling translation from sequence should disable translation")
    requireEqual(manager.currentMode, .singleTrack(.original), "Sequence translation toggle should enter original-only mode")
    requireEqual(events.count, 3, "Third mode transition count")
    requireEqual(events[2].0, .singleTrack(.original), "Third transition mode")
    requireEqual(events[2].1, 7, "Third transition preserved sentence")

    manager.toggle(.original, preservingPosition: 8)
    requireTrue(manager.isOriginalEnabled, "Toggling the only enabled original track should keep original")
    requireFalse(manager.isTranslationEnabled, "Toggling the only enabled original track should leave translation disabled")
    requireEqual(manager.currentMode, .singleTrack(.original), "Last active original toggle should stay original-only")
    requireEqual(events.count, 3, "Last-active original toggle should not emit a mode transition")

    manager.toggle(.translation, preservingPosition: 9)
    requireTrue(manager.isOriginalEnabled, "Toggling inactive translation should keep original")
    requireTrue(manager.isTranslationEnabled, "Toggling inactive translation should enable translation")
    requireEqual(manager.currentMode, .sequence, "Inactive translation toggle should restore both tracks")
    requireEqual(events.count, 4, "Fourth mode transition count")
    requireEqual(events[3].0, .sequence, "Fourth transition mode")
    requireEqual(events[3].1, 9, "Fourth transition preserved sentence")

    manager.setTracks(original: false, translation: false, preservingPosition: 10)
    requireTrue(manager.isSequenceMode, "Both-off requests should normalize back to sequence mode")
    requireEqual(manager.currentMode, .sequence, "Both-off normalization mode")
    requireEqual(events.count, 4, "No-op both-off normalization from sequence should not emit a duplicate transition")

    manager.enableSequenceMode(preservingPosition: 11)
    requireEqual(events.count, 4, "Enabling already-active sequence mode should not emit a duplicate transition")

    manager.toggle(.translation, preservingPosition: 12)
    requireEqual(manager.currentMode, .singleTrack(.original), "Translation toggle should leave original-only mode")
    manager.toggle(kind: .combined, preservingPosition: 13)
    requireEqual(manager.currentMode, .sequence, "Combined kind should restore sequence mode")
    requireEqual(events.last?.1, 13, "Combined kind should preserve sentence")
    manager.toggle(kind: .other, preservingPosition: 14)
    requireEqual(events.last?.1, 13, "Other kind should not change mode")

    let availableToggleManager = AudioModeManager()
    availableToggleManager.toggle(.original, availableTracks: [.original, .translation], preservingPosition: 20)
    requireEqual(
        availableToggleManager.currentMode,
        .singleTrack(.translation),
        "Available-track toggle should support disabling Original from both-track mode"
    )
    availableToggleManager.toggle(.translation, availableTracks: [.original, .translation], preservingPosition: 21)
    requireEqual(
        availableToggleManager.currentMode,
        .singleTrack(.translation),
        "Available-track toggle should keep the last active Translation lane selected"
    )
    availableToggleManager.toggle(.original, availableTracks: [.original, .translation], preservingPosition: 22)
    requireEqual(
        availableToggleManager.currentMode,
        .sequence,
        "Available-track toggle should restore both lanes by tapping the inactive Original lane"
    )
    availableToggleManager.setTracks(original: true, translation: false, preservingPosition: 23)
    availableToggleManager.toggle(.translation, availableTracks: [.translation], preservingPosition: 24)
    requireEqual(
        availableToggleManager.currentMode,
        .singleTrack(.translation),
        "Available-track toggle should clamp stale Original-only state to the only playable Translation lane"
    )
    availableToggleManager.toggle(.translation, availableTracks: [.translation], preservingPosition: 25)
    requireEqual(
        availableToggleManager.currentMode,
        .singleTrack(.translation),
        "Available-track toggle should not remove the only available Translation lane"
    )

    requireEqual(manager.resolvePreferredTrackID(for: chunk), "combined", "Sequence preferred audio option")
    manager.setTracks(original: true, translation: false, preservingPosition: 15)
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "original", "Original-only preferred audio option")
    manager.setTracks(original: false, translation: true, preservingPosition: 16)
    requireEqual(manager.resolvePreferredTrackID(for: chunk), "translation", "Translation-only preferred audio option")
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "original"),
        optionID: "translation",
        timing: .translation,
        "Translation-only mode should ignore a stale original selected track"
    )

    let nextOriginalURL = URL(string: "https://example.invalid/chunk-2-original.m4a")!
    let nextTranslationURL = URL(string: "https://example.invalid/chunk-2-translation.m4a")!
    let nextCombined = audioOption("next-combined", kind: .combined, urls: [nextOriginalURL, nextTranslationURL])
    let nextOriginal = audioOption("next-original", kind: .original, urls: [nextOriginalURL])
    let nextTranslation = audioOption("next-translation", kind: .translation, urls: [nextTranslationURL])
    let nextChunk = InteractiveChunk(
        id: "chunk-2",
        audioOptions: [nextCombined, nextOriginal, nextTranslation]
    )
    requireEqual(
        manager.resolvePreferredTrackID(for: nextChunk),
        "next-translation",
        "Translation-only mode should resolve the fresh next-batch translation option"
    )
    requireInstruction(
        manager.resolveAudioInstruction(for: nextChunk, selectedTrackID: "translation"),
        optionID: "next-translation",
        timing: .translation,
        "Translation-only mode should ignore the previous batch's selected track id"
    )

    manager.enableSequenceMode()
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        sequenceID: "combined",
        "Sequence mode should use the combined option"
    )

    manager.setTracks(original: true, translation: false)
    requireInstruction(
        manager.resolveAudioInstruction(for: chunk, selectedTrackID: "combined"),
        optionID: "original",
        timing: .original,
        "Original-only mode should prefer the dedicated original option"
    )

    let combinedOnlyChunk = InteractiveChunk(id: "chunk-2", audioOptions: [combined])
    manager.setTracks(original: false, translation: true)
    requireInstruction(
        manager.resolveAudioInstruction(for: combinedOnlyChunk, selectedTrackID: "combined"),
        url: translationURL,
        timing: .translation,
        "Translation-only mode should split the second combined stream when no dedicated track exists"
    )

    manager.enableSequenceMode()
    requireEqual(
        manager.resolveTimingTrack(
            for: chunk,
            selectedTrackID: "combined",
            sequenceTrack: .translation,
            sequenceEnabled: true,
            activeURL: nil
        ),
        .translation,
        "Sequence timing should follow the active sequence track"
    )

    manager.setTracks(original: false, translation: true)
    requireEqual(
        manager.resolveTimingTrack(
            for: chunk,
            selectedTrackID: "combined",
            sequenceTrack: .original,
            sequenceEnabled: true,
            activeURL: originalURL
        ),
        .translation,
        "Translation-only timing should override a stale sequence controller track"
    )

    manager.setTracks(original: true, translation: false)
    requireEqual(
        manager.resolveTimingTrack(
            for: chunk,
            selectedTrackID: "combined",
            sequenceTrack: .original,
            sequenceEnabled: false,
            activeURL: translationURL
        ),
        .original,
        "Original-only timing should ignore a stale translation active URL"
    )

    manager.setTracks(original: false, translation: true)
    requireEqual(
        manager.resolveTimingTrack(
            for: chunk,
            selectedTrackID: "combined",
            sequenceTrack: .original,
            sequenceEnabled: false,
            activeURL: originalURL
        ),
        .translation,
        "Translation-only timing should ignore a stale original active URL"
    )

    manager.enableSequenceMode()
    requireEqual(
        manager.resolveTimingTrack(
            for: combinedOnlyChunk,
            selectedTrackID: "combined",
            sequenceTrack: .original,
            sequenceEnabled: false,
            activeURL: translationURL
        ),
        .translation,
        "Combined timing should map the second stream to translation"
    )
}

@main
private struct AudioModeManagerCheck {
    static func main() async {
        await MainActor.run {
            runChecks()
        }
    }
}
