import Foundation
import SwiftUI
import Combine

/// Represents the audio playback mode
enum AudioMode: Equatable {
    /// Only one track plays (either original or translation)
    case singleTrack(SequenceTrack)
    /// Both tracks alternate per sentence (sequence mode)
    case sequence

    var description: String {
        switch self {
        case .singleTrack(let track):
            return "singleTrack(\(track.rawValue))"
        case .sequence:
            return "sequence"
        }
    }
}

/// Central manager for audio mode and track toggle state.
/// This is the single source of truth for whether original/translation audio is enabled.
///
/// Previously, toggle state was duplicated between:
/// - InteractivePlayerView (@AppStorage)
/// - SequencePlaybackController (isOriginalAudioEnabled/isTranslationAudioEnabled)
///
/// This manager consolidates that state and handles mode transitions with position preservation.
@MainActor
final class AudioModeManager: ObservableObject {

    // MARK: - Published State

    /// Whether original audio track is enabled
    @Published private(set) var isOriginalEnabled: Bool {
        didSet {
            // Persist to UserDefaults
            UserDefaults.standard.set(isOriginalEnabled, forKey: Self.originalEnabledKey)
            updateMode()
        }
    }

    /// Whether translation audio track is enabled
    @Published private(set) var isTranslationEnabled: Bool {
        didSet {
            // Persist to UserDefaults
            UserDefaults.standard.set(isTranslationEnabled, forKey: Self.translationEnabledKey)
            updateMode()
        }
    }

    /// The current audio mode (computed from toggle state)
    @Published private(set) var currentMode: AudioMode = .sequence

    // MARK: - Persistence Keys

    private static let originalEnabledKey = "player.showOriginalAudio"
    private static let translationEnabledKey = "player.showTranslationAudio"

    // MARK: - Callbacks

    /// Called when mode changes, providing the new mode and the sentence index to preserve (if any)
    var onModeChange: ((AudioMode, Int?) -> Void)?

    // MARK: - Initialization

    init() {
        // Always initialize with both tracks enabled (sequence mode)
        // This ensures a consistent starting state - users can toggle off as needed
        // We don't persist toggle state across sessions to avoid confusion
        self.isOriginalEnabled = true
        self.isTranslationEnabled = true

        // Set initial mode to sequence (both enabled)
        self.currentMode = .sequence
    }

    // MARK: - Mode Computation

    private static func computeMode(original: Bool, translation: Bool) -> AudioMode {
        if original && translation {
            return .sequence
        } else if original {
            return .singleTrack(.original)
        } else if translation {
            return .singleTrack(.translation)
        } else {
            // Both disabled shouldn't happen, but default to original
            return .singleTrack(.original)
        }
    }

    private func updateMode() {
        let newMode = Self.computeMode(original: isOriginalEnabled, translation: isTranslationEnabled)
        if newMode != currentMode {
            print("[AudioModeManager] Mode changed: \(currentMode.description) -> \(newMode.description)")
            currentMode = newMode
        }
    }

    // MARK: - Toggle Methods

    /// Toggle the specified track, ensuring at least one track remains enabled.
    /// - Parameters:
    ///   - track: The track to toggle
    ///   - currentSentenceIndex: The current sentence index to preserve during mode change
    func toggle(_ track: SequenceTrack, preservingPosition currentSentenceIndex: Int? = nil) {
        let previousMode = currentMode

        switch track {
        case .original:
            if isOriginalEnabled && !isTranslationEnabled {
                // Currently only original is on - switch to only translation
                isOriginalEnabled = false
                isTranslationEnabled = true
            } else {
                isOriginalEnabled.toggle()
            }
        case .translation:
            if isTranslationEnabled && !isOriginalEnabled {
                // Currently only translation is on - switch to only original
                isTranslationEnabled = false
                isOriginalEnabled = true
            } else {
                isTranslationEnabled.toggle()
            }
        }

        // Notify if mode actually changed
        if currentMode != previousMode {
            print("[AudioModeManager] Toggle \(track.rawValue): mode \(previousMode.description) -> \(currentMode.description), preserving sentence \(currentSentenceIndex ?? -1)")
            onModeChange?(currentMode, currentSentenceIndex)
        }
    }

    /// Set both tracks at once (e.g., for enabling combined/sequence mode)
    /// - Parameters:
    ///   - original: Whether original should be enabled
    ///   - translation: Whether translation should be enabled
    ///   - currentSentenceIndex: The current sentence index to preserve during mode change
    func setTracks(original: Bool, translation: Bool, preservingPosition currentSentenceIndex: Int? = nil) {
        let previousMode = currentMode

        // Ensure at least one track is enabled
        let finalOriginal = original || !translation
        let finalTranslation = translation || !original

        isOriginalEnabled = finalOriginal
        isTranslationEnabled = finalTranslation

        // Notify if mode actually changed
        if currentMode != previousMode {
            print("[AudioModeManager] SetTracks: mode \(previousMode.description) -> \(currentMode.description), preserving sentence \(currentSentenceIndex ?? -1)")
            onModeChange?(currentMode, currentSentenceIndex)
        }
    }

    /// Enable sequence mode (both tracks enabled)
    /// - Parameter currentSentenceIndex: The current sentence index to preserve
    func enableSequenceMode(preservingPosition currentSentenceIndex: Int? = nil) {
        setTracks(original: true, translation: true, preservingPosition: currentSentenceIndex)
    }

    // MARK: - Query Methods

    /// Whether sequence mode is currently active (both tracks enabled)
    var isSequenceMode: Bool {
        isOriginalEnabled && isTranslationEnabled
    }

    /// The preferred track to start at when navigating to a new sentence
    /// - In sequence mode: prefer original (sentences start with original)
    /// - In single track mode: use the enabled track
    var preferredTrack: SequenceTrack {
        switch currentMode {
        case .sequence:
            return .original
        case .singleTrack(let track):
            return track
        }
    }

    /// Check if a specific track is enabled
    func isEnabled(_ track: SequenceTrack) -> Bool {
        switch track {
        case .original:
            return isOriginalEnabled
        case .translation:
            return isTranslationEnabled
        }
    }
}

// MARK: - Compatibility with InteractiveChunk.AudioOption.Kind

extension AudioModeManager {
    /// Toggle using the AudioOption.Kind enum (for compatibility with existing UI)
    func toggle(kind: InteractiveChunk.AudioOption.Kind, preservingPosition currentSentenceIndex: Int? = nil) {
        switch kind {
        case .original:
            toggle(.original, preservingPosition: currentSentenceIndex)
        case .translation:
            toggle(.translation, preservingPosition: currentSentenceIndex)
        case .combined:
            enableSequenceMode(preservingPosition: currentSentenceIndex)
        case .other:
            break
        }
    }
}

// MARK: - Audio Resolution

/// The resolved audio instruction for a given chunk + current mode.
/// Centralizes the branching logic previously scattered across prepareAudio(),
/// activeTimingTrack(), and reconfigureAudioForCurrentToggles().
enum ResolvedAudioInstruction: CustomStringConvertible {
    /// Enter sequence mode using the combined track.
    /// The caller should call configureSequencePlayback().
    case sequence(combinedOption: InteractiveChunk.AudioOption)

    /// Play a single audio option directly (its streamURLs as-is).
    case singleOption(option: InteractiveChunk.AudioOption, timingTrack: TextPlayerTimingTrack)

    /// Play a single URL extracted from a combined track's streamURLs array.
    /// Used when only one toggle is enabled but no dedicated track exists.
    case singleURL(url: URL, timingTrack: TextPlayerTimingTrack)

    var description: String {
        switch self {
        case .sequence: return "sequence"
        case .singleOption(let opt, let timing): return "singleOption(\(opt.kind.rawValue), \(timing))"
        case .singleURL(let url, let timing): return "singleURL(\(url.lastPathComponent), \(timing))"
        }
    }
}

extension AudioModeManager {

    // MARK: - Audio Instruction Resolution

    /// Resolve which audio to load for the given chunk based on current mode.
    /// Pure function — no side effects, no dependency on audioCoordinator state.
    ///
    /// - Parameters:
    ///   - chunk: The chunk to resolve audio for
    ///   - selectedTrackID: The currently selected audio track ID
    /// - Returns: An instruction describing what to load, or nil if no audio options exist
    func resolveAudioInstruction(
        for chunk: InteractiveChunk,
        selectedTrackID: String?
    ) -> ResolvedAudioInstruction? {
        let track: InteractiveChunk.AudioOption? = {
            if let id = selectedTrackID {
                return chunk.audioOptions.first(where: { $0.id == id })
            }
            return chunk.audioOptions.first
        }()
        guard let track else { return nil }

        switch currentMode {
        case .sequence:
            if track.kind == .combined {
                return .sequence(combinedOption: track)
            }
            // Selected track isn't combined — play it directly
            return .singleOption(option: track, timingTrack: timingTrackForKind(track.kind))

        case .singleTrack(let enabledTrack):
            if track.kind == .combined {
                return resolveSingleFromCombined(
                    combinedTrack: track,
                    chunk: chunk,
                    enabledTrack: enabledTrack
                )
            }
            return .singleOption(option: track, timingTrack: timingTrackForKind(track.kind))
        }
    }

    // MARK: - Preferred Track Resolution

    /// Resolve which AudioOption ID should be selected when the mode changes.
    /// Used by reconfigureAudioForCurrentToggles().
    ///
    /// - Parameter chunk: The current chunk
    /// - Returns: The ID of the best audio option for the current mode, or nil
    func resolvePreferredTrackID(for chunk: InteractiveChunk) -> String? {
        let options = chunk.audioOptions
        let combinedOption = options.first(where: { $0.kind == .combined })
        let originalOption = options.first(where: { $0.kind == .original })
        let translationOption = options.first(where: { $0.kind == .translation })

        switch currentMode {
        case .sequence:
            return (combinedOption ?? originalOption ?? translationOption)?.id
        case .singleTrack(.original):
            return (originalOption ?? combinedOption ?? translationOption)?.id
        case .singleTrack(.translation):
            return (translationOption ?? combinedOption ?? originalOption)?.id
        }
    }

    // MARK: - Timing Track Resolution

    /// Resolve the timing track for a chunk, given current mode and live playback state.
    ///
    /// - Parameters:
    ///   - chunk: The chunk
    ///   - selectedTrackID: Currently selected audio track ID
    ///   - sequenceTrack: The current sequence controller track (if sequence is enabled)
    ///   - sequenceEnabled: Whether the sequence controller is enabled
    ///   - activeURL: The URL currently being played by the audio coordinator
    func resolveTimingTrack(
        for chunk: InteractiveChunk,
        selectedTrackID: String?,
        sequenceTrack: SequenceTrack,
        sequenceEnabled: Bool,
        activeURL: URL?
    ) -> TextPlayerTimingTrack {
        // Sequence mode active: timing follows sequence controller's current track
        if sequenceEnabled {
            switch sequenceTrack {
            case .original: return .original
            case .translation: return .translation
            }
        }

        // Single-toggle mode: determine from which track is actually playing
        if case .singleTrack(let enabledTrack) = currentMode {
            if let activeURL, let match = matchURLToTimingTrack(activeURL: activeURL, chunk: chunk) {
                return match
            }
            // Fallback to toggle state
            switch enabledTrack {
            case .original: return .original
            case .translation: return .translation
            }
        }

        // Both toggles enabled, non-sequence: check selected track kind
        let track: InteractiveChunk.AudioOption? = {
            if let id = selectedTrackID {
                return chunk.audioOptions.first(where: { $0.id == id })
            }
            return chunk.audioOptions.first
        }()
        guard let track else { return .translation }

        switch track.kind {
        case .combined:
            if track.streamURLs.count > 1 {
                if let activeURL, activeURL == track.streamURLs.first {
                    return .original
                }
                return .translation
            }
            return track.streamURLs.count == 1 ? .mix : .original
        case .original:
            return .original
        case .translation:
            return .translation
        case .other:
            return .translation
        }
    }

    // MARK: - Private Helpers

    /// Resolve a single track to play when the selected track is combined but only one toggle is enabled.
    /// Mirrors the logic previously in prepareAudio() lines 242-309.
    private func resolveSingleFromCombined(
        combinedTrack: InteractiveChunk.AudioOption,
        chunk: InteractiveChunk,
        enabledTrack: SequenceTrack
    ) -> ResolvedAudioInstruction {
        let originalOption = chunk.audioOptions.first { $0.kind == .original }
        let translationOption = chunk.audioOptions.first { $0.kind == .translation }

        switch enabledTrack {
        case .original:
            if let originalOption {
                return .singleOption(option: originalOption, timingTrack: .original)
            }
            if let url = combinedTrack.streamURLs.first {
                return .singleURL(url: url, timingTrack: .original)
            }
            if let translationOption {
                return .singleOption(option: translationOption, timingTrack: .translation)
            }

        case .translation:
            if let translationOption {
                return .singleOption(option: translationOption, timingTrack: .translation)
            }
            if combinedTrack.streamURLs.count >= 2 {
                return .singleURL(url: combinedTrack.streamURLs[1], timingTrack: .translation)
            }
            if let originalOption {
                return .singleOption(option: originalOption, timingTrack: .original)
            }
        }

        // Ultimate fallback: play the combined track directly
        return .singleOption(option: combinedTrack, timingTrack: .mix)
    }

    /// Map an AudioOption.Kind to the corresponding TextPlayerTimingTrack.
    private func timingTrackForKind(_ kind: InteractiveChunk.AudioOption.Kind) -> TextPlayerTimingTrack {
        switch kind {
        case .original: return .original
        case .translation: return .translation
        case .combined: return .mix
        case .other: return .translation
        }
    }

    /// Match an active URL against a chunk's known audio option URLs.
    /// Returns the appropriate timing track, or nil if no match found.
    private func matchURLToTimingTrack(activeURL: URL, chunk: InteractiveChunk) -> TextPlayerTimingTrack? {
        let originalTrack = chunk.audioOptions.first { $0.kind == .original }
        let translationTrack = chunk.audioOptions.first { $0.kind == .translation }
        let combinedTrack = chunk.audioOptions.first { $0.kind == .combined }

        if let originalTrack, originalTrack.streamURLs.contains(activeURL) {
            return .original
        }
        if let translationTrack, translationTrack.streamURLs.contains(activeURL) {
            return .translation
        }
        if let combinedTrack, combinedTrack.streamURLs.count >= 2 {
            if activeURL == combinedTrack.streamURLs.first { return .original }
            if activeURL == combinedTrack.streamURLs[1] { return .translation }
        } else if let combinedTrack, combinedTrack.streamURLs.count == 1,
                  activeURL == combinedTrack.streamURLs.first {
            return isOriginalEnabled ? .original : .translation
        }
        return nil
    }
}
