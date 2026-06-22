extension VideoPlayerView {
    func currentSubtitleDisplay() -> VideoSubtitleDisplay? {
        VideoSubtitleDisplayBuilder.build(cues: cues, time: coordinator.currentTime, visibility: subtitleVisibility)
    }

    func syncSubtitleSelectionIfNeeded(force: Bool = false) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else {
            subtitleSelection = nil
            subtitleSelectionRange = nil
            subtitleActiveCueID = nil
            return
        }
        if isManualSubtitleNavigation && !force {
            if subtitleActiveCueID == display.cue.id {
                return
            }
            isManualSubtitleNavigation = false
        }
        if force || subtitleActiveCueID != display.cue.id {
            subtitleActiveCueID = display.cue.id
            subtitleSelection = defaultSubtitleSelection(in: display)
            subtitleSelectionRange = nil
            return
        }
        if let normalized = normalizedSelection(from: subtitleSelection, in: display),
           normalized != subtitleSelection {
            subtitleSelection = normalized
            subtitleSelectionRange = nil
            return
        }
        if subtitleSelection == nil {
            subtitleSelection = defaultSubtitleSelection(in: display)
            subtitleSelectionRange = nil
        }
    }

    func normalizedSelection(
        from selection: VideoSubtitleWordSelection?,
        in display: VideoSubtitleDisplay
    ) -> VideoSubtitleWordSelection? {
        guard let selection else { return nil }
        let line = lineForSelection(selection, in: display)
        guard let line, !line.tokens.isEmpty else { return nil }
        let tokenIndex = min(max(selection.tokenIndex, 0), line.tokens.count - 1)
        return VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: tokenIndex
        )
    }

    func defaultSubtitleSelection(in display: VideoSubtitleDisplay) -> VideoSubtitleWordSelection? {
        let preferredLine = display.lines.first(where: { $0.kind == .translation })
            ?? display.lines.first(where: { $0.kind == .unknown })
            ?? display.lines.first
        guard let line = preferredLine, !line.tokens.isEmpty else { return nil }
        let tokenIndex = currentTokenIndex(
            for: line,
            cueStart: display.highlightStart,
            cueEnd: display.highlightEnd,
            time: coordinator.currentTime
        )
        let resolved = nearestLookupTokenIndex(in: line.tokens, startingAt: tokenIndex) ?? tokenIndex
        return VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: resolved
        )
    }

    func currentTokenIndex(
        for line: VideoSubtitleDisplayLine,
        cueStart: Double,
        cueEnd: Double,
        time: Double
    ) -> Int {
        guard !line.tokens.isEmpty else { return 0 }
        if let styles = line.tokenStyles {
            if let current = styles.firstIndex(where: { $0 == .highlightCurrent }) {
                return current
            }
            if let lastPrior = styles.lastIndex(where: { $0 == .highlightPrior }) {
                return lastPrior
            }
        }
        let clamped = min(max(time, cueStart), cueEnd)
        let epsilon = 1e-3
        if clamped >= cueEnd - epsilon {
            return line.tokens.count - 1
        }
        let revealed = line.revealTimes.filter { $0 <= clamped + epsilon }.count
        if revealed > 0 {
            return min(revealed - 1, line.tokens.count - 1)
        }
        if clamped >= cueStart - epsilon {
            return 0
        }
        return 0
    }

    func lineForSelection(
        _ selection: VideoSubtitleWordSelection,
        in display: VideoSubtitleDisplay
    ) -> VideoSubtitleDisplayLine? {
        if display.lines.indices.contains(selection.lineIndex) {
            let line = display.lines[selection.lineIndex]
            if line.kind == selection.lineKind {
                return line
            }
        }
        if let line = display.lines.first(where: { $0.kind == selection.lineKind }) {
            return line
        }
        if display.lines.indices.contains(selection.lineIndex) {
            return display.lines[selection.lineIndex]
        }
        return nil
    }

    func handleSubtitleWordNavigation(_ delta: Int) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else { return }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        guard let selection, let line = lineForSelection(selection, in: display) else { return }
        guard !line.tokens.isEmpty else { return }
        let direction = delta >= 0 ? 1 : -1
        let startIndex = selection.tokenIndex + direction
        guard let nextIndex = wrappedLookupTokenIndex(
            in: line.tokens,
            startingAt: startIndex,
            direction: direction
        ) else { return }
        isManualSubtitleNavigation = true
        subtitleSelectionRange = nil
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: nextIndex
        )
        scheduleAutoSubtitleLookup()
    }

    func handleSubtitleWordRangeSelection(_ delta: Int) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else { return }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        guard let selection, let line = lineForSelection(selection, in: display) else { return }
        guard !line.tokens.isEmpty else { return }
        let direction = delta >= 0 ? 1 : -1
        let anchorIndex: Int
        let focusIndex: Int
        if let range = subtitleSelectionRange,
           range.lineKind == line.kind,
           range.lineIndex == line.index {
            anchorIndex = range.anchorIndex
            focusIndex = range.focusIndex
        } else {
            anchorIndex = selection.tokenIndex
            focusIndex = selection.tokenIndex
        }
        let nextIndex = max(0, min(focusIndex + direction, line.tokens.count - 1))
        subtitleSelectionRange = VideoSubtitleWordSelectionRange(
            lineKind: line.kind,
            lineIndex: line.index,
            anchorIndex: anchorIndex,
            focusIndex: nextIndex
        )
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: nextIndex
        )
        isManualSubtitleNavigation = true
    }

    func handleSubtitleTrackNavigation(_ delta: Int) -> Bool {
        guard !coordinator.isPlaying else { return false }
        guard let display = currentSubtitleDisplay() else { return false }
        guard !display.lines.isEmpty else { return false }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        let currentLine = selection.flatMap { lineForSelection($0, in: display) } ?? display.lines[0]
        let step = delta >= 0 ? 1 : -1
        let currentIndex = display.lines.indices.contains(currentLine.index)
            ? currentLine.index
            : (display.lines.firstIndex(where: { $0.id == currentLine.id }) ?? 0)
        let nextIndex = currentIndex + step
        guard display.lines.indices.contains(nextIndex) else { return false }
        let line = display.lines[nextIndex]
        let baseTokenIndex = selection?.tokenIndex ?? currentTokenIndex(
            for: currentLine,
            cueStart: display.highlightStart,
            cueEnd: display.highlightEnd,
            time: coordinator.currentTime
        )
        let clampedIndex = max(0, min(baseTokenIndex, max(0, line.tokens.count - 1)))
        let resolvedIndex: Int = {
            guard line.tokens.indices.contains(clampedIndex) else { return clampedIndex }
            if sanitizeLookupQuery(line.tokens[clampedIndex]) != nil {
                return clampedIndex
            }
            return nearestLookupTokenIndex(in: line.tokens, startingAt: clampedIndex) ?? clampedIndex
        }()
        isManualSubtitleNavigation = true
        subtitleSelectionRange = nil
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: resolvedIndex
        )
        scheduleAutoSubtitleLookup()
        return true
    }

    func subtitleLineKinds(in display: VideoSubtitleDisplay) -> [VideoSubtitleLineKind] {
        var seen = Set<VideoSubtitleLineKind>()
        var ordered: [VideoSubtitleLineKind] = []
        for line in display.lines {
            if !seen.contains(line.kind) {
                seen.insert(line.kind)
                ordered.append(line.kind)
            }
        }
        return ordered
    }

    func handleSentenceSkip(_ delta: Int) {
        let groups = subtitleSentenceGroups()
        if groups.isEmpty {
            coordinator.skip(by: delta < 0 ? -15 : 15)
            return
        }
        let time = coordinator.currentTime
        let epsilon = 1e-3
        let currentIndex = groups.firstIndex { time >= $0.start - epsilon && time <= $0.end + epsilon }
            ?? groups.lastIndex { time >= $0.start - epsilon }
            ?? 0
        let nextIndex = max(0, min(currentIndex + (delta < 0 ? -1 : 1), groups.count - 1))
        let targetTime = groups[nextIndex].start

        #if os(tvOS)
        // On tvOS, mute and pause during seek to prevent audio bleed from the old position
        let wasPlaying = coordinator.isPlaying
        let player = coordinator.playerInstance()
        let savedVolume = player?.volume ?? 1.0
        player?.volume = 0
        if wasPlaying {
            coordinator.pause()
        }
        coordinator.seek(to: targetTime) { _ in
            // Restore volume after seek completes
            player?.volume = savedVolume
            if wasPlaying {
                coordinator.play()
            }
        }
        #else
        coordinator.seek(to: targetTime)
        #endif
    }

    func subtitleSentenceGroups() -> [SubtitleSentenceGroup] {
        guard !cues.isEmpty else { return [] }
        let sorted = cues.sorted { lhs, rhs in
            if lhs.start == rhs.start {
                return lhs.end < rhs.end
            }
            return lhs.start < rhs.start
        }
        var groups: [SubtitleSentenceGroup] = []
        let maxGap = 0.06
        for cue in sorted {
            guard !cue.text.isEmpty else { continue }
            if let last = groups.last {
                let gap = cue.start - last.end
                if cue.text == last.text && gap <= maxGap {
                    groups[groups.count - 1] = SubtitleSentenceGroup(
                        start: last.start,
                        end: max(last.end, cue.end),
                        text: last.text
                    )
                    continue
                }
            }
            groups.append(SubtitleSentenceGroup(start: cue.start, end: cue.end, text: cue.text))
        }
        return groups
    }

    func toggleSubtitleVisibility(_ kind: VideoSubtitleLineKind) {
        switch kind {
        case .original:
            subtitleVisibility.showOriginal.toggle()
        case .transliteration:
            subtitleVisibility.showTransliteration.toggle()
        case .translation:
            subtitleVisibility.showTranslation.toggle()
        case .unknown:
            subtitleVisibility.showTranslation.toggle()
        }
    }

    func handleTransliterationToggle() {
        guard hasTransliterationLines else { return }
        toggleSubtitleVisibility(.transliteration)
        handleUserInteraction()
    }

    var hasTransliterationLines: Bool {
        cues.contains { cue in
            cue.lines.contains { $0.kind == .transliteration }
        }
    }
}

struct SubtitleSentenceGroup {
    let start: Double
    let end: Double
    let text: String
}
