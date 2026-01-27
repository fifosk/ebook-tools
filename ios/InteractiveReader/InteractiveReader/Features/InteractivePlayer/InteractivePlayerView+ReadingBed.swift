import SwiftUI

extension InteractivePlayerView {
    func toggleReadingBed() {
        withAnimation(.none) {
            readingBedEnabled.toggle()
        }
    }

    var selectedReadingBedLabel: String {
        if let selectedID = viewModel.selectedReadingBedID,
           let beds = viewModel.readingBedCatalog?.beds,
           let match = beds.first(where: { $0.id == selectedID }) {
            return match.label.isEmpty ? match.id : match.label
        }
        return "Default"
    }

    func readingBedSummary(label: String) -> String {
        let state = readingBedEnabled ? "On" : "Off"
        if label.isEmpty {
            return state
        }
        return "\(state) / \(label)"
    }

    func configureReadingBed() {
        readingBedCoordinator.setLooping(true)
        readingBedCoordinator.setVolume(readingBedVolume)
        updateReadingBedPlayback()
    }

    func handleNarrationPlaybackChange(isPlaying: Bool) {
        readingBedPauseTask?.cancel()
        readingBedPauseTask = nil
        if isPlaying {
            // Playback started/resumed - ensure reading bed is playing if enabled
            // Only call update if reading bed isn't already playing correctly
            if readingBedEnabled,
               let url = viewModel.readingBedURL,
               (!readingBedCoordinator.isPlaying || readingBedCoordinator.activeURL != url) {
                updateReadingBedPlayback()
            }
            return
        }
        // Playback stopped - check if this is a definitive pause or a brief transition
        if !audioCoordinator.isPlaybackRequested {
            // Definitive pause (user stopped playback) - pause reading bed immediately
            readingBedCoordinator.pause()
            return
        }
        // Playback requested but not currently playing = likely a transition between chunks
        // Let reading bed continue playing without interruption
        // Schedule a delayed check in case this is actually a stalled playback
        readingBedPauseTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: readingBedPauseDelayNanos)
            guard !Task.isCancelled else { return }
            // After delay, only pause if playback truly stopped (not requested anymore)
            if !audioCoordinator.isPlaybackRequested {
                readingBedCoordinator.pause()
            }
            // If isPlaybackRequested is still true, assume playback will resume
            // and let reading bed continue playing
        }
    }

    func updateReadingBedPlayback() {
        guard readingBedEnabled, let url = viewModel.readingBedURL else {
            readingBedCoordinator.pause()
            return
        }
        guard audioCoordinator.isPlaybackRequested else {
            readingBedCoordinator.pause()
            return
        }
        if readingBedCoordinator.activeURL == url && readingBedCoordinator.isPlaying {
            return
        }
        if readingBedCoordinator.activeURL != url || readingBedCoordinator.activeURL == nil {
            readingBedCoordinator.load(url: url, autoPlay: true)
        } else {
            readingBedCoordinator.play()
        }
    }
}
