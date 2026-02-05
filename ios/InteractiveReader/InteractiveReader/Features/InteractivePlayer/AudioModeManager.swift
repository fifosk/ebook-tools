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
