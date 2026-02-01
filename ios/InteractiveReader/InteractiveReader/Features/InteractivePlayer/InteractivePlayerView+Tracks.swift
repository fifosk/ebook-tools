import SwiftUI

extension InteractivePlayerView {
    func trackLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Transliteration"
        case .translation:
            return "Translation"
        }
    }

    func trackSummaryLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Translit"
        case .translation:
            return "Translation"
        }
    }

    func trackToggle(label: String, kind: TextPlayerVariantKind) -> some View {
        Button {
            toggleTrack(kind)
        } label: {
            if visibleTracks.contains(kind) {
                Label(label, systemImage: "checkmark")
            } else {
                Text(label)
            }
        }
    }

    func imageReelToggle() -> some View {
        let isEnabled = showImageReel?.wrappedValue ?? false
        return Button {
            if let showImageReel {
                showImageReel.wrappedValue.toggle()
            }
        } label: {
            if isEnabled {
                Label("Images", systemImage: "checkmark")
            } else {
                Text("Images")
            }
        }
    }

    func toggleTrack(_ kind: TextPlayerVariantKind) {
        withAnimation(.none) {
            if visibleTracks.contains(kind) {
                if visibleTracks.count > 1 {
                    visibleTracks.remove(kind)
                }
            } else {
                visibleTracks.insert(kind)
            }
        }
        hasCustomTrackSelection = true
    }

    func toggleTrackIfAvailable(_ kind: TextPlayerVariantKind) {
        guard let chunk = viewModel.selectedChunk else { return }
        let available = availableTracks(for: chunk)
        guard available.contains(kind) else { return }
        toggleTrack(kind)
    }

    func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk?) {
        guard let chunk else { return }
        handleWordNavigation(delta, in: chunk)
    }

    func toggleAudioTrack(_ kind: InteractiveChunk.AudioOption.Kind) {
        guard let chunk = viewModel.selectedChunk else { return }
        let options = chunk.audioOptions
        guard !options.isEmpty else { return }
        let selectedID = viewModel.selectedAudioTrackID
        let currentOption = selectedID.flatMap { id in
            options.first(where: { $0.id == id })
        } ?? options.first

        let targetOption = options.first(where: { $0.kind == kind })
        let combinedOption = options.first(where: { $0.kind == .combined })
        let originalOption = options.first(where: { $0.kind == .original })
        let translationOption = options.first(where: { $0.kind == .translation })

        let fallbackOption: InteractiveChunk.AudioOption? = {
            switch kind {
            case .original:
                return translationOption ?? combinedOption ?? options.first(where: { $0.kind != .original }) ?? options.first
            case .translation:
                return originalOption ?? combinedOption ?? options.first(where: { $0.kind != .translation }) ?? options.first
            case .combined, .other:
                return options.first
            }
        }()

        if let targetOption {
            if currentOption?.id == targetOption.id {
                if let fallbackOption, fallbackOption.id != targetOption.id {
                    viewModel.selectAudioTrack(id: fallbackOption.id)
                }
            } else {
                viewModel.selectAudioTrack(id: targetOption.id)
            }
            return
        }

        if let combinedOption, currentOption?.id != combinedOption.id {
            viewModel.selectAudioTrack(id: combinedOption.id)
        }
    }

    func availableTracks(for chunk: InteractiveChunk) -> [TextPlayerVariantKind] {
        var available: [TextPlayerVariantKind] = []
        if chunk.sentences.contains(where: { !$0.originalTokens.isEmpty }) {
            available.append(.original)
        }
        if chunk.sentences.contains(where: { !$0.transliterationTokens.isEmpty }) {
            available.append(.transliteration)
        }
        if chunk.sentences.contains(where: { !$0.translationTokens.isEmpty }) {
            available.append(.translation)
        }
        if available.isEmpty {
            return [.original]
        }
        return available
    }

    func hasImageReel(for chunk: InteractiveChunk) -> Bool {
        chunk.sentences.contains { sentence in
            if let rawPath = sentence.imagePath, rawPath.nonEmptyValue != nil {
                return true
            }
            return false
        }
    }

    func applyDefaultTrackSelection(for chunk: InteractiveChunk) {
        let available = Set(availableTracks(for: chunk))
        if !hasCustomTrackSelection || visibleTracks.isEmpty {
            visibleTracks = available
        }
        if let showImageReel {
            showImageReel.wrappedValue = hasImageReel(for: chunk)
        }
    }

    var trackAvailabilitySignature: String {
        guard let chunk = viewModel.selectedChunk else { return "" }
        let available = availableTracks(for: chunk)
        return available.map(\.rawValue).sorted().joined(separator: "|")
    }

    func textTrackSummary(for chunk: InteractiveChunk) -> String {
        let available = availableTracks(for: chunk)
        let visible = available.filter { visibleTracks.contains($0) }
        var parts = visible.map { trackSummaryLabel($0) }
        let canShowImages = hasImageReel(for: chunk) && showImageReel != nil
        if canShowImages, let showImageReel, showImageReel.wrappedValue {
            parts.append("Images")
        }
        let allTextSelected = visible.count == available.count
        let allSelected = allTextSelected && (!canShowImages || showImageReel?.wrappedValue == true)
        if allSelected {
            return "All"
        }
        if parts.isEmpty {
            return "Text"
        }
        if parts.count == 1 {
            return parts[0]
        }
        return parts.joined(separator: " + ")
    }

    func playbackRateLabel(_ rate: Double) -> String {
        let rounded = (rate * 100).rounded() / 100
        let formatted = String(format: rounded.truncatingRemainder(dividingBy: 1) == 0 ? "%.0f" : "%.2f", rounded)
        return "\(formatted)x"
    }

    func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - audioCoordinator.playbackRate) < 0.01
    }

    /// Determines the preferred sequence track based on current visibility settings.
    /// This controls which track to start at when skipping to a different sentence.
    /// - If only original is visible, prefer original
    /// - If only translation/transliteration is visible, prefer translation
    /// - If both are visible, prefer original (start at beginning of sentence)
    /// - If neither is visible, returns original as fallback
    var preferredSequenceTrack: SequenceTrack? {
        let origVisible = visibleTracks.contains(.original)
        let transVisible = visibleTracks.contains(.translation) || visibleTracks.contains(.transliteration)

        if origVisible && transVisible {
            // Both visible: start at beginning of sentence (original comes first)
            return .original
        } else if origVisible {
            return .original
        } else if transVisible {
            return .translation
        }
        return .original // Fallback: start at beginning
    }

    /// Updates the shouldSkipTrack callback on the sequence controller based on current visibility settings.
    /// This ensures that hidden tracks are skipped during automatic playback progression.
    func updateShouldSkipTrackCallback() {
        let origVisible = visibleTracks.contains(.original)
        let transVisible = visibleTracks.contains(.translation) || visibleTracks.contains(.transliteration)

        // If both tracks are visible (or neither for safety), don't skip anything
        if origVisible && transVisible {
            viewModel.sequenceController.shouldSkipTrack = nil
            print("[TrackVisibility] Both tracks visible, not skipping any segments")
        } else {
            // If only one track is visible, skip the other
            viewModel.sequenceController.shouldSkipTrack = { track in
                switch track {
                case .original:
                    return !origVisible
                case .translation:
                    return !transVisible
                }
            }
            print("[TrackVisibility] Updated skip callback: origVisible=\(origVisible), transVisible=\(transVisible)")
        }
    }
}
