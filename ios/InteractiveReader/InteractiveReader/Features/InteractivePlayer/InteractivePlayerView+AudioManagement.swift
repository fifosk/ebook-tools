import SwiftUI

// MARK: - Audio Management

extension InteractivePlayerView {

    func playbackPrimaryKind(for chunk: InteractiveChunk) -> TextPlayerVariantKind? {
        // Return a valid kind if playback is active or requested.
        // Using isPlaybackRequested in addition to isPlaying handles the brief moments
        // during track switches where isPlaying might be false momentarily.
        guard audioCoordinator.isPlaying || audioCoordinator.isPlaybackRequested else { return nil }
        let activeTrack = viewModel.activeTimingTrack(for: chunk)
        switch activeTrack {
        case .original:
            if visibleTracks.contains(.original) {
                return .original
            }
            if visibleTracks.contains(.translation) {
                return .translation
            }
            if visibleTracks.contains(.transliteration) {
                return .transliteration
            }
        case .translation, .mix:
            if visibleTracks.contains(.translation) {
                return .translation
            }
            if visibleTracks.contains(.transliteration) {
                return .transliteration
            }
            if visibleTracks.contains(.original) {
                return .original
            }
        }
        return nil
    }

    func resolveInfoVariant() -> PlayerChannelVariant {
        let rawLabel = (headerInfo?.itemTypeLabel ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let lower = rawLabel.lowercased()
        if lower.contains("subtitle") {
            return .subtitles
        }
        if lower.contains("video") {
            return .video
        }
        if lower.contains("book") || headerInfo?.author.isEmpty == false || headerInfo?.title.isEmpty == false {
            return .book
        }
        return .job
    }

    func slideIndicatorLabel(for chunk: InteractiveChunk) -> String? {
        guard let currentSentence = currentSentenceNumber(for: chunk) else { return nil }
        let jobBounds = jobSentenceBounds
        let jobStart = jobBounds.start ?? 1
        let jobEnd = jobBounds.end
        let displayCurrent = jobEnd.map { min(currentSentence, $0) } ?? currentSentence

        // Unified compact format across all platforms
        var label = jobEnd != nil
            ? "S:\(displayCurrent)/\(jobEnd ?? displayCurrent)"
            : "S:\(displayCurrent)"

        var suffixParts: [String] = []
        if let jobEnd {
            let span = max(jobEnd - jobStart, 0)
            let ratio = span > 0 ? Double(displayCurrent - jobStart) / Double(span) : 1
            if ratio.isFinite {
                let percent = min(max(Int(round(ratio * 100)), 0), 100)
                suffixParts.append("J:\(percent)%")
            }
        }
        if let bookTotal = bookTotalSentences(jobEnd: jobEnd) {
            let ratio = bookTotal > 0 ? Double(displayCurrent) / Double(bookTotal) : 1
            if ratio.isFinite {
                let percent = min(max(Int(round(ratio * 100)), 0), 100)
                suffixParts.append("B:\(percent)%")
            }
        }
        if !suffixParts.isEmpty {
            label += " · " + suffixParts.joined(separator: " · ")
        }
        return label
    }

    func audioTimelineLabel(for chunk: InteractiveChunk) -> String? {
        guard let metrics = audioTimelineMetrics(for: chunk) else { return nil }
        let played = formatDurationLabel(metrics.played)
        let remaining = formatDurationLabel(metrics.remaining)
        return "\(played) / \(remaining)"
    }

    func audioTimelineMetrics(
        for chunk: InteractiveChunk
    ) -> (played: Double, remaining: Double, total: Double)? {
        guard let context = viewModel.jobContext else { return nil }
        let chunks = context.chunks
        guard let currentIndex = chunks.firstIndex(where: { $0.id == chunk.id }) else { return nil }
        let preferredKind = selectedAudioKind(for: chunk)
        let total = chunks.reduce(0.0) { partial, entry in
            partial + resolvedAudioDuration(for: entry, preferredKind: preferredKind, isCurrent: entry.id == chunk.id)
        }
        guard total > 0 else { return nil }
        let before = chunks.prefix(currentIndex).reduce(0.0) { partial, entry in
            partial + resolvedAudioDuration(for: entry, preferredKind: preferredKind, isCurrent: false)
        }
        let currentDuration = resolvedAudioDuration(for: chunk, preferredKind: preferredKind, isCurrent: true)
        let usesCombinedQueue = preferredKind == .combined && viewModel.usesCombinedQueue(for: chunk)
        let currentTime = max(
            usesCombinedQueue ? viewModel.combinedQueuePlaybackTime(for: chunk) : viewModel.playbackTime(for: chunk),
            0
        )
        let within = currentDuration > 0 ? min(currentTime, currentDuration) : currentTime
        let played = min(before + within, total)
        let remaining = max(total - played, 0)
        return (played, remaining, total)
    }

    func selectedAudioKind(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption.Kind? {
        if let selectedID = viewModel.selectedAudioTrackID,
           let option = chunk.audioOptions.first(where: { $0.id == selectedID }) {
            return option.kind
        }
        return chunk.audioOptions.first?.kind
    }

    func availableAudioRoles(for chunk: InteractiveChunk) -> Set<LanguageFlagRole> {
        let kinds = Set(chunk.audioOptions.map(\.kind))
        var roles: Set<LanguageFlagRole> = []
        if kinds.contains(.original) {
            roles.insert(.original)
        }
        if kinds.contains(.translation) {
            roles.insert(.translation)
        }
        if roles.isEmpty, kinds.contains(.combined) {
            roles = [.original, .translation]
        }
        return roles
    }

    func activeAudioRoles(
        for chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>
    ) -> Set<LanguageFlagRole> {
        guard let kind = selectedAudioKind(for: chunk) else { return [] }
        switch kind {
        case .original:
            return availableRoles.contains(.original) ? [.original] : []
        case .translation:
            return availableRoles.contains(.translation) ? [.translation] : []
        case .combined, .other:
            return availableRoles.intersection([.original, .translation])
        }
    }

    func toggleHeaderAudioRole(
        _ role: LanguageFlagRole,
        for chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>
    ) {
        guard !availableRoles.isEmpty else { return }

        // Capture current sentence position BEFORE changing mode
        let currentSentenceIndex = captureCurrentSentenceIndex(for: chunk)

        // Convert role to audio track kind and use AudioModeManager
        switch role {
        case .original:
            audioModeManager.toggle(.original, preservingPosition: currentSentenceIndex)
        case .translation:
            audioModeManager.toggle(.translation, preservingPosition: currentSentenceIndex)
        }

        // Reconfigure playback with position preservation
        reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)
    }

    func selectAudioTrack(
        for chunk: InteractiveChunk,
        preferredRoles: Set<LanguageFlagRole>,
        availableRoles: Set<LanguageFlagRole>
    ) {
        let options = chunk.audioOptions
        guard !options.isEmpty else { return }
        let combinedOption = options.first(where: { $0.kind == .combined })
        let originalOption = options.first(where: { $0.kind == .original })
        let translationOption = options.first(where: { $0.kind == .translation })
        var desiredRoles = preferredRoles.intersection(availableRoles)
        if desiredRoles.isEmpty {
            desiredRoles = availableRoles
        }
        let targetOption: InteractiveChunk.AudioOption?
        if desiredRoles.contains(.original), desiredRoles.contains(.translation), let combinedOption {
            targetOption = combinedOption
        } else if desiredRoles.contains(.original), let originalOption {
            targetOption = originalOption
        } else if desiredRoles.contains(.translation), let translationOption {
            targetOption = translationOption
        } else if let combinedOption {
            targetOption = combinedOption
        } else {
            targetOption = translationOption ?? originalOption ?? options.first
        }
        if let targetOption, targetOption.id != viewModel.selectedAudioTrackID {
            viewModel.selectAudioTrack(id: targetOption.id)
        }
    }

    func resolvedAudioDuration(
        for chunk: InteractiveChunk,
        preferredKind: InteractiveChunk.AudioOption.Kind?,
        isCurrent: Bool
    ) -> Double {
        let usesCombinedQueue = preferredKind == .combined && viewModel.usesCombinedQueue(for: chunk)
        if isCurrent {
            if usesCombinedQueue,
               let duration = viewModel.combinedPlaybackDuration(for: chunk) {
                return max(duration, 0)
            }
            if let duration = viewModel.timelineDuration(for: chunk) ?? viewModel.playbackDuration(for: chunk) {
                return max(duration, 0)
            }
        }
        if usesCombinedQueue,
           let duration = viewModel.combinedPlaybackDuration(for: chunk) {
            return max(duration, 0)
        }
        let option = chunk.audioOptions.first(where: { $0.kind == preferredKind }) ?? chunk.audioOptions.first
        if let duration = option?.duration, duration > 0 {
            return duration
        }
        if preferredKind == .combined,
           let fallback = viewModel.fallbackDuration(for: chunk, kind: .combined),
           fallback > 0 {
            return fallback
        }
        if let option,
           let fallback = viewModel.fallbackDuration(for: chunk, kind: option.kind),
           fallback > 0 {
            return fallback
        }
        let sentenceSum = chunk.sentences.compactMap { $0.totalDuration }.reduce(0, +)
        if sentenceSum > 0 {
            return sentenceSum
        }
        return 0
    }

    func formatDurationLabel(_ value: Double) -> String {
        let total = max(0, Int(value.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        if hours > 0 {
            return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
        }
        return String(format: "%02d:%02d", minutes, seconds)
    }

    func currentSentenceNumber(for chunk: InteractiveChunk) -> Int? {
        if let active = activeSentenceDisplay(for: chunk) {
            if let number = active.sentenceNumber {
                return number
            }
            if let start = chunk.startSentence {
                return start + max(active.index, 0)
            }
            return active.index + 1
        }
        return nil
    }

    func bookTotalSentences(jobEnd: Int?) -> Int? {
        if !viewModel.chapterEntries.isEmpty {
            var maxEnd: Int?
            for chapter in viewModel.chapterEntries {
                let candidate = chapter.endSentence ?? chapter.startSentence
                maxEnd = maxEnd.map { max($0, candidate) } ?? candidate
            }
            return maxEnd
        }
        return jobEnd
    }
}
