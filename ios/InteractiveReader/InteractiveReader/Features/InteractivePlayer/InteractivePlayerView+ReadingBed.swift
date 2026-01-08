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
            updateReadingBedPlayback()
            return
        }
        if !audioCoordinator.isPlaybackRequested {
            updateReadingBedPlayback()
            return
        }
        readingBedPauseTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: readingBedPauseDelayNanos)
            guard !Task.isCancelled else { return }
            updateReadingBedPlayback()
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
