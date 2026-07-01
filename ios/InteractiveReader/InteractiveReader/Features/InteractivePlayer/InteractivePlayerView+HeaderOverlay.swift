import SwiftUI

// MARK: - Header Overlay

private struct InteractivePlayerHeaderHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

extension InteractivePlayerView {

    func playerInfoOverlay(for chunk: InteractiveChunk) -> some View {
        let variant = resolveInfoVariant()
        let rawLabel = headerInfo?.itemTypeLabel.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let label = rawLabel.isEmpty ? "Job" : rawLabel
        let progressLabel = headerProgressSummaryLabel(for: chunk)
        let showHeaderContent = !isHeaderCollapsed
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)

        let styledHeaderView = playerInfoHeaderContent(
            for: chunk,
            variant: variant,
            label: label,
            progressLabel: progressLabel,
            showHeaderContent: showHeaderContent,
            availableRoles: availableRoles,
            activeRoles: activeRoles
        )
            .padding(.horizontal, isPhonePortrait ? 16 : (isPhone ? 12 : 6))
            .padding(.top, 6)
            .frame(maxWidth: .infinity, alignment: .topLeading)
            .allowsHitTesting(true)
            .background(
                GeometryReader { proxy in
                    Color.clear.preference(
                        key: InteractivePlayerHeaderHeightKey.self,
                        value: proxy.size.height
                    )
                }
            )
            .onPreferenceChange(InteractivePlayerHeaderHeightKey.self) { height in
                let nextHeight = max(0, height.rounded(.up))
                if abs(headerOverlayMeasuredHeight - nextHeight) > 0.5 {
                    headerOverlayMeasuredHeight = nextHeight
                }
            }
        #if os(tvOS)
        let finalView = styledHeaderView
            .onLongPressGesture(minimumDuration: 0.6, perform: handleHeaderLongPress)
            .zIndex(1)
        #else
        let finalView = styledHeaderView
            .zIndex(1)
        #endif
        return headerMagnifyWrapper(finalView)
    }

    @ViewBuilder
    private func playerInfoHeaderContent(
        for chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String,
        progressLabel: String?,
        showHeaderContent: Bool,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        #if os(iOS)
        if isPhone, showHeaderContent {
            VStack(alignment: .leading, spacing: 8) {
                playerInfoHeaderRow(
                    for: chunk,
                    variant: variant,
                    label: label,
                    progressLabel: progressLabel,
                    showHeaderContent: showHeaderContent
                )
                phoneHeaderControlsRow(
                    info: headerInfo,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles
                )
            }
        } else {
            playerInfoHeaderRow(
                for: chunk,
                variant: variant,
                label: label,
                progressLabel: progressLabel,
                showHeaderContent: showHeaderContent
            )
        }
        #else
        playerInfoHeaderRow(
            for: chunk,
            variant: variant,
            label: label,
            progressLabel: progressLabel,
            showHeaderContent: showHeaderContent
        )
        #endif
    }

    private func playerInfoHeaderRow(
        for chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String,
        progressLabel: String?,
        showHeaderContent: Bool
    ) -> some View {
        headerRowContent(
            for: chunk,
            variant: variant,
            label: label,
            progressLabel: progressLabel,
            showHeaderContent: showHeaderContent
        )
        .padding(.horizontal, showHeaderContent ? headerGlassHorizontalPadding : 0)
        .padding(.vertical, showHeaderContent ? headerGlassVerticalPadding : 0)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background {
            if showHeaderContent && headerInfo == nil {
                PlayerHeaderGlassPanelBackground(cornerRadius: headerGlassCornerRadius)
            }
        }
    }

    @ViewBuilder
    private func headerRowContent(
        for chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String,
        progressLabel: String?,
        showHeaderContent: Bool
    ) -> some View {
        let usesBannerProgress = showHeaderContent && headerInfo != nil
        if isPhonePortrait {
            VStack(alignment: .leading, spacing: 8 * min(infoHeaderScale, 1.4)) {
                if showHeaderContent {
                    headerIdentityCluster(
                        info: headerInfo,
                        chunk: chunk,
                        variant: variant,
                        label: label,
                        progressLabel: progressLabel
                    )
                }
                if (showHeaderContent || isTV) && !usesBannerProgress {
                    headerProgressStack(
                        progressLabel: progressLabel,
                        showHeaderContent: showHeaderContent
                    )
                    .frame(maxWidth: .infinity, alignment: .trailing)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } else {
            HStack(alignment: .top, spacing: headerPrimarySpacing) {
                if showHeaderContent {
                    headerIdentityCluster(
                        info: headerInfo,
                        chunk: chunk,
                        variant: variant,
                        label: label,
                        progressLabel: progressLabel
                    )
                    .frame(maxWidth: usesBannerProgress ? .infinity : nil, alignment: .leading)
                }
                if !usesBannerProgress {
                    Spacer(minLength: headerPrimarySpacing)
                }
                if (showHeaderContent || isTV) && !usesBannerProgress {
                    headerProgressStack(
                        progressLabel: progressLabel,
                        showHeaderContent: showHeaderContent
                    )
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @ViewBuilder
    private func headerIdentityCluster(
        info: InteractivePlayerHeaderInfo?,
        chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String,
        progressLabel: String?
    ) -> some View {
        if let info {
            infoBadgeView(
                info: info,
                chunk: chunk,
                variant: variant,
                label: label,
                progressLabel: progressLabel
            )
        } else {
            PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
        }
    }

    private func headerProgressStack(
        progressLabel: String?,
        showHeaderContent: Bool
    ) -> some View {
        VStack(alignment: .trailing, spacing: 6) {
            if showHeaderContent {
                headerProgressPills(progressLabel: progressLabel)
            } else {
                HStack(spacing: 6) {
                    if let progressLabel {
                        headerProgressPillButton(label: progressLabel)
                    }
                }
            }
            #if os(tvOS)
            tvHeaderTogglePill
            #endif
        }
    }

    @ViewBuilder
    private func headerProgressPills(progressLabel: String?) -> some View {
        #if os(iOS)
        if isPhonePortrait {
            VStack(alignment: .trailing, spacing: 3) {
                if let progressLabel {
                    headerProgressPillButton(label: progressLabel)
                }
            }
        } else {
            headerProgressPillRow(progressLabel: progressLabel)
        }
        #else
        headerProgressPillRow(progressLabel: progressLabel)
        #endif
    }

    private func headerProgressPillRow(progressLabel: String?) -> some View {
        HStack(spacing: 6) {
            if let progressLabel {
                headerProgressPillButton(label: progressLabel)
            }
        }
    }

    private func headerLanguageFlagRow(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>,
        showConnector: Bool
    ) -> some View {
        PlayerLanguageFlagRow(
            flags: info.languageFlags,
            modelLabel: nil,
            isTV: isTV,
            sizeScale: infoPillScale,
            activeRoles: activeRoles,
            availableRoles: availableRoles,
            onToggleRole: { role in
                handleHeaderLanguageRoleToggle(role, for: chunk, availableRoles: availableRoles)
            },
            showConnector: showConnector
        )
    }

    #if os(iOS)
    private func phoneHeaderControlsRow(
        info: InteractivePlayerHeaderInfo?,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        HStack(spacing: 0) {
            if let info, !info.languageFlags.isEmpty {
                headerLanguageFlagRow(
                    info: info,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles,
                    showConnector: false
                )
                Spacer(minLength: 8)
            }
            musicPillView
            Spacer(minLength: 8)
            speedPillView
            Spacer(minLength: 8)
            sleepTimerPillView
            Spacer(minLength: 8)
            jumpPillView
            Spacer(minLength: 8)
            searchPillView
            Spacer(minLength: 8)
            bookmarkRibbonPillView
        }
    }
    #endif

    func infoBadgeView(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String,
        progressLabel: String?
    ) -> some View {
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        return InteractivePlayerHeaderIdentityBanner(
            info: info,
            variant: variant,
            label: label,
            isTV: isTV,
            isPhone: isPhone,
            isPhonePortrait: isPhonePortrait,
            infoHeaderScale: infoHeaderScale,
            infoPillScale: infoPillScale,
            infoCoverWidth: infoCoverWidth,
            infoCoverHeight: infoCoverHeight,
            titleFont: infoTitleFont,
            metaFont: infoMetaFont,
            eyebrowFont: infoEyebrowFont,
            contentSpacing: headerIdentityContentSpacing,
            horizontalPadding: headerIdentityHorizontalPadding,
            verticalPadding: headerIdentityVerticalPadding,
            cornerRadius: headerIdentityCornerRadius,
            maxWidth: headerIdentityMaxWidth,
            coverCornerRadius: headerCoverCornerRadius,
            progressLabel: progressLabel,
            sentenceProgressRange: headerSentenceProgressRange(for: chunk),
            sentenceProgressValue: headerSentenceProgressValue(for: chunk),
            sentenceProgressLabel: headerSentenceProgressLabel(for: chunk),
            onCoverTap: handleHeaderCoverTap,
            onProgressTap: handleHeaderProgressTap,
            onSentenceProgressChange: handleHeaderSentenceProgressChange,
            onSentenceProgressEditingChanged: handleHeaderSentenceProgressEditingChanged
        ) {
            #if os(tvOS)
            headerInlineControlsRow(
                info: info,
                chunk: chunk,
                availableRoles: availableRoles,
                activeRoles: activeRoles
            )
            .focusScope(headerControlsNamespace)
            .focused($focusedArea, equals: .controls)
            #else
            headerInlineControlsRow(
                info: info,
                chunk: chunk,
                availableRoles: availableRoles,
                activeRoles: activeRoles
            )
            #endif
        }
    }

    @ViewBuilder
    private func headerInlineControlsRow(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        #if os(tvOS)
        headerInlineControlsContent(
            info: info,
            chunk: chunk,
            availableRoles: availableRoles,
            activeRoles: activeRoles
        )
        #else
        if isPad {
            ScrollView(.horizontal, showsIndicators: false) {
                headerInlineControlsContent(
                    info: info,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles
                )
            }
        } else {
            headerInlineControlsContent(
                info: info,
                chunk: chunk,
                availableRoles: availableRoles,
                activeRoles: activeRoles
            )
        }
        #endif
    }

    private func headerInlineControlsContent(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        HStack(spacing: 8 * infoPillScale) {
            if !info.languageFlags.isEmpty {
                headerLanguageFlagRow(
                    info: info,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles,
                    showConnector: !isPhone
                )
            }
            musicPillView
            speedPillView
            sleepTimerPillView
            jumpPillView
            searchPillView
            bookmarkRibbonPillView
        }
    }

    private func handleHeaderLanguageRoleToggle(
        _ role: LanguageFlagRole,
        for chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>
    ) {
        toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
    }

    func slideIndicatorView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.85))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(PlayerHeaderPillBackground(isActive: true, isProminent: true))
    }

    func audioTimelineView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.75))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(PlayerHeaderPillBackground(isActive: false))
            .contentShape(Capsule())
            .onTapGesture(perform: handleHeaderProgressTap)
    }

    func timingProvenanceView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.70))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(PlayerHeaderPillBackground(isActive: false))
            .accessibilityLabel(label)
            .accessibilityIdentifier("interactiveReaderTimingProvenancePill")
    }

    func headerProgressPillButton(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.86))
            .multilineTextAlignment(.center)
            .lineLimit(2)
            .minimumScaleFactor(0.78)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(PlayerHeaderPillBackground(isActive: true, isProminent: true))
            .contentShape(Capsule())
            .onTapGesture(perform: handleHeaderProgressTap)
            .accessibilityAddTraits(.isButton)
            .accessibilityLabel(label)
            .accessibilityHint(isHeaderCollapsed ? "Expand reader header" : "Collapse reader header")
            .accessibilityIdentifier("interactiveReaderHeaderProgressPill")
    }

    func headerProgressSummaryLabel(for chunk: InteractiveChunk) -> String? {
        var primaryParts: [String] = []
        if let chapterLabel = headerChapterProgressLabel(for: chunk) {
            primaryParts.append(chapterLabel)
        }
        if let bookPercent = headerBookProgressPercent(for: chunk) {
            primaryParts.append("Book \(bookPercent)%")
        }
        var lines: [String] = []
        if !primaryParts.isEmpty {
            lines.append(primaryParts.joined(separator: " · "))
        }
        if let timeLabel = audioTimelineLabel(for: chunk) {
            lines.append(timeLabel)
        }
        if lines.isEmpty {
            return slideIndicatorLabel(for: chunk)
        }
        return lines.joined(separator: "\n")
    }

    private func headerChapterProgressLabel(for chunk: InteractiveChunk) -> String? {
        let chapters = scopedChapterEntries
        guard !chapters.isEmpty else { return nil }
        let currentSentence = currentHeaderSentenceNumber(for: chunk)
        let activeIndex = currentSentence.flatMap { sentence in
            chapters.firstIndex { chapter in
                let end = effectiveChapterEnd(for: chapter, boundsEnd: jobSentenceBounds.end)
                return sentence >= chapter.startSentence && sentence <= end
            }
        } ?? 0
        let activeChapter = chapters[activeIndex]
        let fullChapters = viewModel.chapterEntries
        let bookIndex = activeChapter.bookIndex
            ?? fullChapters.firstIndex(where: { $0.id == activeChapter.id }).map { $0 + 1 }
            ?? activeIndex + 1
        let bookTotal = fullChapters.count > 0 ? fullChapters.count : chapters.count
        return "Chapter \(bookIndex)/\(bookTotal)"
    }

    private func headerBookProgressPercent(for chunk: InteractiveChunk) -> Int? {
        guard let currentSentence = currentHeaderSentenceNumber(for: chunk) else { return nil }
        let bounds = fullBookSentenceBounds
        let start = bounds.start ?? 1
        guard let end = bounds.end, end >= start else { return nil }
        let clampedCurrent = min(max(currentSentence, start), end)
        let span = max(end - start, 1)
        let ratio = Double(clampedCurrent - start) / Double(span)
        guard ratio.isFinite else { return nil }
        return min(max(Int(round(ratio * 100)), 0), 100)
    }

    private var fullBookSentenceBounds: (start: Int?, end: Int?) {
        let jobBounds = jobSentenceBounds
        let chapters = viewModel.chapterEntries
        guard !chapters.isEmpty else {
            return (jobBounds.start, bookTotalSentences(jobEnd: jobBounds.end))
        }
        let fallbackEnd = bookTotalSentences(jobEnd: jobBounds.end)
        var minValue: Int?
        var maxValue: Int?
        for chapter in chapters {
            minValue = min(minValue ?? chapter.startSentence, chapter.startSentence)
            let chapterEnd = chapter.endSentence ?? fallbackEnd ?? chapter.startSentence
            maxValue = max(maxValue ?? chapterEnd, chapterEnd)
        }
        return (minValue, maxValue ?? fallbackEnd)
    }

    func headerSentenceProgressRange(for chunk: InteractiveChunk) -> ClosedRange<Double>? {
        let bounds = jobSentenceBounds
        let start = bounds.start ?? chunk.startSentence
        let end = bounds.end ?? chunk.endSentence
        guard let start, let end, end > start else { return nil }
        return Double(start)...Double(end)
    }

    func headerSentenceProgressValue(for chunk: InteractiveChunk) -> Double {
        if isHeaderSentenceSliderEditing, let headerSentenceSliderValue {
            return clampedHeaderSentenceProgressValue(headerSentenceSliderValue, for: chunk)
        }
        guard let current = currentHeaderSentenceNumber(for: chunk) else {
            return headerSentenceProgressRange(for: chunk)?.lowerBound ?? 1
        }
        return clampedHeaderSentenceProgressValue(Double(current), for: chunk)
    }

    func headerSentenceProgressLabel(for chunk: InteractiveChunk) -> String {
        let current = Int(headerSentenceProgressValue(for: chunk).rounded())
        let end = headerSentenceProgressRange(for: chunk).map { Int($0.upperBound.rounded()) }
        if let end {
            return "Sentence \(current) / \(end)"
        }
        return "Sentence \(current)"
    }

    private func currentHeaderSentenceNumber(for chunk: InteractiveChunk) -> Int? {
        if let pending = pendingExplicitSentenceJumpID, !pendingExplicitSentenceJumpIsExpired {
            return pending
        }
        if audioCoordinator.isPlaying || viewModel.isSequenceTransitioning || viewModel.sequenceController.isDwelling {
            if let currentIndex = viewModel.sequenceController.currentSentenceIndex,
               viewModel.isSequenceModeActive,
               chunk.sentences.indices.contains(currentIndex) {
                return SentencePositionProvider.sentenceNumber(in: chunk, at: currentIndex)
            }
            if let active = viewModel.activeSentence(at: viewModel.highlightingTime),
               let activeIndex = chunk.sentences.firstIndex(where: { $0.id == active.id && $0.displayIndex == active.displayIndex }) {
                return SentencePositionProvider.sentenceNumber(in: chunk, at: activeIndex)
                    ?? SentencePositionProvider.sentenceNumber(for: active)
            }
        }
        if let selectedSentenceID {
            return selectedSentenceID
        }
        if let active = viewModel.activeSentence(at: viewModel.highlightingTime),
           let activeIndex = chunk.sentences.firstIndex(where: { $0.id == active.id && $0.displayIndex == active.displayIndex }) {
            return SentencePositionProvider.sentenceNumber(in: chunk, at: activeIndex)
                ?? SentencePositionProvider.sentenceNumber(for: active)
        }
        if let activeDisplay = activeSentenceDisplay(for: chunk) {
            return activeDisplay.sentenceNumber
        }
        return chunk.startSentence ?? SentencePositionProvider.sentenceNumber(in: chunk, at: 0)
    }

    private func clampedHeaderSentenceProgressValue(_ value: Double, for chunk: InteractiveChunk) -> Double {
        guard let range = headerSentenceProgressRange(for: chunk) else { return value }
        return min(max(value, range.lowerBound), range.upperBound)
    }

    func handleHeaderSentenceProgressChange(_ value: Double) {
        showPhoneProgressFooter()
        isHeaderSentenceSliderEditing = true
        headerSentenceSliderValue = value.rounded()
    }

    func handleHeaderSentenceProgressEditingChanged(_ isEditing: Bool) {
        showPhoneProgressFooter()
        isHeaderSentenceSliderEditing = isEditing
        guard !isEditing else { return }
        guard let value = headerSentenceSliderValue else { return }
        commitHeaderSentenceProgress(Int(value.rounded()))
        schedulePhoneProgressFooterAutoHide()
    }

    func stepHeaderSentenceProgress(_ delta: Int, in chunk: InteractiveChunk) {
        guard delta != 0 else { return }
        let current = Int(headerSentenceProgressValue(for: chunk).rounded())
        let stepped = current + delta
        let clamped = Int(clampedHeaderSentenceProgressValue(Double(stepped), for: chunk).rounded())
        guard clamped != current else { return }
        headerSentenceSliderValue = Double(clamped)
        isHeaderSentenceSliderEditing = false
        commitHeaderSentenceProgress(clamped)
    }

    private func commitHeaderSentenceProgress(_ targetSentence: Int) {
        guard let chunk = viewModel.selectedChunk else { return }
        let targetChunk = viewModel.jobContext.flatMap {
            viewModel.resolveChunk(containing: targetSentence, in: $0)
        } ?? chunk
        prepareExplicitSentenceJump(to: targetSentence, chunkID: targetChunk.id)
        viewModel.rememberSingleTrackSentenceAnchor(chunkID: targetChunk.id, sentenceNumber: targetSentence)
        viewModel.jumpToSentence(targetSentence, autoPlay: audioCoordinator.isPlaybackRequested)
    }

    func clearHeaderSentenceProgressDraft() {
        isHeaderSentenceSliderEditing = false
        headerSentenceSliderValue = nil
        pendingExplicitSentenceJumpID = nil
        pendingExplicitSentenceJumpChunkID = nil
        pendingExplicitSentenceJumpStartedAt = nil
    }

    func shouldShowFullPhoneProgressFooter(for chunk: InteractiveChunk) -> Bool {
        guard isPhone else { return true }
        guard headerSentenceProgressRange(for: chunk) != nil else { return false }
        return phoneProgressFooterVisible || isHeaderSentenceSliderEditing
    }

    func showPhoneProgressFooter() {
        guard isPhone else { return }
        phoneProgressFooterAutoHideTask?.cancel()
        phoneProgressFooterVisible = true
    }

    func hidePhoneProgressFooter() {
        guard isPhone else { return }
        phoneProgressFooterAutoHideTask?.cancel()
        phoneProgressFooterAutoHideTask = nil
        isHeaderSentenceSliderEditing = false
        headerSentenceSliderValue = nil
        withAnimation(.easeInOut(duration: 0.18)) {
            phoneProgressFooterVisible = false
        }
    }

    func schedulePhoneProgressFooterAutoHide() {
        guard isPhone else { return }
        phoneProgressFooterAutoHideTask?.cancel()
        phoneProgressFooterAutoHideTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 1_800_000_000)
            guard !Task.isCancelled, !isHeaderSentenceSliderEditing else { return }
            withAnimation(.easeInOut(duration: 0.18)) {
                phoneProgressFooterVisible = false
            }
        }
    }

    private var headerGlassHorizontalPadding: CGFloat {
        (isTV ? 14 : 10) * min(infoHeaderScale, 1.6)
    }

    var headerGlassVerticalPadding: CGFloat {
        (isTV ? 10 : 6) * min(infoHeaderScale, 1.6)
    }

    private var headerGlassCornerRadius: CGFloat {
        (isTV ? 26 : 18) * min(infoHeaderScale, 1.35)
    }

    private var headerPrimarySpacing: CGFloat {
        (isTV ? 14 : 10) * min(infoHeaderScale, 1.45)
    }

    private var headerIdentityContentSpacing: CGFloat {
        (isTV ? 16 : 12) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityHorizontalPadding: CGFloat {
        (isTV ? 16 : 12) * min(infoHeaderScale, 1.35)
    }

    var headerIdentityVerticalPadding: CGFloat {
        (isTV ? 10 : 8) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityCornerRadius: CGFloat {
        (isTV ? 22 : 16) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityMaxWidth: CGFloat? {
        if isTV { return .infinity }
        if isPad { return .infinity }
        if isPhonePortrait { return nil }
        return 620
    }

    private var headerCoverCornerRadius: CGFloat {
        (isTV ? 10 : 8) * min(infoHeaderScale, 1.35)
    }

}

private struct InteractivePlayerHeaderIdentityBanner: View {
    let info: InteractivePlayerHeaderInfo
    let variant: PlayerChannelVariant
    let label: String
    let isTV: Bool
    let isPhone: Bool
    let isPhonePortrait: Bool
    let infoHeaderScale: CGFloat
    let infoPillScale: CGFloat
    let infoCoverWidth: CGFloat
    let infoCoverHeight: CGFloat
    let titleFont: Font
    let metaFont: Font
    let eyebrowFont: Font
    let contentSpacing: CGFloat
    let horizontalPadding: CGFloat
    let verticalPadding: CGFloat
    let cornerRadius: CGFloat
    let maxWidth: CGFloat?
    let coverCornerRadius: CGFloat
    let progressLabel: String?
    let sentenceProgressRange: ClosedRange<Double>?
    let sentenceProgressValue: Double
    let sentenceProgressLabel: String
    let onCoverTap: () -> Void
    let onProgressTap: () -> Void
    let onSentenceProgressChange: (Double) -> Void
    let onSentenceProgressEditingChanged: (Bool) -> Void
    let controls: AnyView

    init<Controls: View>(
        info: InteractivePlayerHeaderInfo,
        variant: PlayerChannelVariant,
        label: String,
        isTV: Bool,
        isPhone: Bool,
        isPhonePortrait: Bool,
        infoHeaderScale: CGFloat,
        infoPillScale: CGFloat,
        infoCoverWidth: CGFloat,
        infoCoverHeight: CGFloat,
        titleFont: Font,
        metaFont: Font,
        eyebrowFont: Font,
        contentSpacing: CGFloat,
        horizontalPadding: CGFloat,
        verticalPadding: CGFloat,
        cornerRadius: CGFloat,
        maxWidth: CGFloat?,
        coverCornerRadius: CGFloat,
        progressLabel: String?,
        sentenceProgressRange: ClosedRange<Double>?,
        sentenceProgressValue: Double,
        sentenceProgressLabel: String,
        onCoverTap: @escaping () -> Void,
        onProgressTap: @escaping () -> Void,
        onSentenceProgressChange: @escaping (Double) -> Void,
        onSentenceProgressEditingChanged: @escaping (Bool) -> Void,
        @ViewBuilder controls: () -> Controls
    ) {
        self.info = info
        self.variant = variant
        self.label = label
        self.isTV = isTV
        self.isPhone = isPhone
        self.isPhonePortrait = isPhonePortrait
        self.infoHeaderScale = infoHeaderScale
        self.infoPillScale = infoPillScale
        self.infoCoverWidth = infoCoverWidth
        self.infoCoverHeight = infoCoverHeight
        self.titleFont = titleFont
        self.metaFont = metaFont
        self.eyebrowFont = eyebrowFont
        self.contentSpacing = contentSpacing
        self.horizontalPadding = horizontalPadding
        self.verticalPadding = verticalPadding
        self.cornerRadius = cornerRadius
        self.maxWidth = maxWidth
        self.coverCornerRadius = coverCornerRadius
        self.progressLabel = progressLabel
        self.sentenceProgressRange = sentenceProgressRange
        self.sentenceProgressValue = sentenceProgressValue
        self.sentenceProgressLabel = sentenceProgressLabel
        self.onCoverTap = onCoverTap
        self.onProgressTap = onProgressTap
        self.onSentenceProgressChange = onSentenceProgressChange
        self.onSentenceProgressEditingChanged = onSentenceProgressEditingChanged
        self.controls = AnyView(controls())
    }

    var body: some View {
        bannerContent
            .padding(.horizontal, horizontalPadding)
            .padding(.vertical, verticalPadding)
            .frame(maxWidth: maxWidth, alignment: .leading)
            .background(PlayerHeaderIdentityBannerBackground(cornerRadius: cornerRadius))
            .overlay(alignment: .topTrailing) {
                headerIdentitySheen
            }
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            .accessibilityIdentifier("interactiveReaderHeaderIdentityBanner")
    }

    @ViewBuilder
    private var bannerContent: some View {
        if isPhonePortrait {
            compactBannerContent
        } else {
            horizontalBannerContent
        }
    }

    private var horizontalBannerContent: some View {
        VStack(alignment: .leading, spacing: 5 * min(infoHeaderScale, 1.2)) {
            HStack(alignment: .center, spacing: contentSpacing) {
                PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                    .layoutPriority(3)
                headerCoverArtworkView(info: info)
                    .onTapGesture(perform: onCoverTap)
                    .layoutPriority(2)
                headerTextAndControlsStack
                    .layoutPriority(1)
                Spacer(minLength: contentSpacing)
                headerProgressPills
                    .layoutPriority(2)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var compactBannerContent: some View {
        VStack(alignment: .leading, spacing: 5 * min(infoHeaderScale, 1.25)) {
            HStack(alignment: .center, spacing: contentSpacing) {
                PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                    .layoutPriority(3)
                headerCoverArtworkView(info: info)
                    .onTapGesture(perform: onCoverTap)
                    .layoutPriority(2)
                titleSubtitleStack
                    .layoutPriority(1)
            }
            headerMetadataPillRow(info: info)
            headerProgressPills
            if !isPhone {
                controls
            }
        }
    }

    private var headerTextAndControlsStack: some View {
        VStack(alignment: .leading, spacing: 4 * min(infoHeaderScale, 1.2)) {
            titleMetadataLine
            if !isPhone {
                controls
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private var headerProgressPills: some View {
        if progressLabel != nil {
            if isPhonePortrait {
                VStack(alignment: .leading, spacing: 4 * min(infoPillScale, 1.2)) {
                    headerProgressPillContent
                }
            } else {
                HStack(spacing: 6 * min(infoPillScale, 1.35)) {
                    headerProgressPillContent
                }
            }
        }
    }

    @ViewBuilder
    private var headerProgressPillContent: some View {
        if let progressLabel {
            headerProgressPill(label: progressLabel)
                .contentShape(Capsule())
                .onTapGesture(perform: onProgressTap)
                .accessibilityAddTraits(.isButton)
                .accessibilityHint("Collapse reader header")
                .accessibilityIdentifier("interactiveReaderHeaderProgressPill")
        }
    }

    private func headerProgressPill(label: String) -> some View {
        Text(label)
            .font(eyebrowFont)
            .foregroundStyle(Color.white.opacity(0.86))
            .multilineTextAlignment(.center)
            .lineLimit(2)
            .minimumScaleFactor(0.78)
            .padding(.horizontal, 8 * min(infoPillScale, 1.4))
            .padding(.vertical, 4 * min(infoPillScale, 1.4))
            .background(PlayerHeaderPillBackground(isActive: true, isProminent: true))
    }

    @ViewBuilder
    private var headerSentenceProgressSlider: some View {
        #if os(iOS)
        if let range = sentenceProgressRange, range.lowerBound < range.upperBound {
            VStack(alignment: .leading, spacing: 3 * min(infoPillScale, 1.2)) {
                HStack(spacing: 6 * min(infoPillScale, 1.3)) {
                    Image(systemName: "text.line.first.and.arrowtriangle.forward")
                        .font(eyebrowFont)
                    Text(sentenceProgressLabel)
                        .font(eyebrowFont)
                        .lineLimit(1)
                    Spacer(minLength: 8)
                    Text("\(Int(sentenceProgressValue.rounded()))")
                        .font(eyebrowFont.monospacedDigit())
                        .foregroundStyle(Color.white.opacity(0.68))
                }
                .foregroundStyle(Color.white.opacity(0.78))
                Slider(
                    value: Binding(
                        get: { sentenceProgressValue },
                        set: { onSentenceProgressChange($0) }
                    ),
                    in: range,
                    step: 1,
                    onEditingChanged: onSentenceProgressEditingChanged
                )
                .tint(Color.orange.opacity(0.92))
                .accessibilityLabel("Sentence progress")
                .accessibilityValue(sentenceProgressLabel)
            }
        }
        #endif
    }

    private var titleSubtitleStack: some View {
        HStack(alignment: .firstTextBaseline, spacing: 6 * min(infoHeaderScale, 1.2)) {
            Text(headerTitle(for: info))
                .font(titleFont)
                .foregroundStyle(Color.white)
                .lineLimit(1)
                .minimumScaleFactor(0.82)
                .layoutPriority(3)
            if let subtitle = headerIdentitySubtitle(for: info) {
                Text(subtitle)
                    .font(metaFont)
                    .foregroundStyle(Color.white.opacity(0.74))
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)
                    .layoutPriority(1)
            }
            let category = info.itemTypeLabel.trimmingCharacters(in: .whitespacesAndNewlines)
            if !category.isEmpty {
                Text(category.uppercased())
                    .font(eyebrowFont)
                    .foregroundStyle(Color.white.opacity(0.68))
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)
            }
        }
    }

    private var titleMetadataLine: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8 * min(infoHeaderScale, 1.2)) {
            titleSubtitleStack
                .layoutPriority(3)
            headerMetadataPillRow(info: info)
                .layoutPriority(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private func headerCoverArtworkView(info: InteractivePlayerHeaderInfo) -> some View {
        Group {
            if info.coverURL != nil || info.secondaryCoverURL != nil {
                PlayerCoverStackView(
                    primaryURL: info.coverURL,
                    secondaryURL: info.secondaryCoverURL,
                    width: infoCoverWidth,
                    height: infoCoverHeight,
                    isTV: isTV
                )
            } else {
                headerCoverPlaceholder(info: info)
            }
        }
        .padding(2 * min(infoHeaderScale, 1.4))
        .background(
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .fill(Color.black.opacity(0.24))
        )
        .overlay(
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .strokeBorder(Color.white.opacity(0.16), lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.30), radius: 12, x: 0, y: 7)
        .contentShape(RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous))
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Show book metadata")
        .accessibilityIdentifier("interactiveReaderHeaderCover")
    }

    private func headerCoverPlaceholder(info: InteractivePlayerHeaderInfo) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.18),
                            Color.white.opacity(0.06)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            VStack(spacing: 2 * min(infoHeaderScale, 1.2)) {
                Image(systemName: itemTypeSystemImage(for: info.itemTypeLabel))
                    .font(.system(size: max(13, infoCoverHeight * 0.26), weight: .semibold))
                Text(headerCoverInitial(for: info))
                    .font(.system(size: max(12, infoCoverHeight * 0.22), weight: .bold))
                    .lineLimit(1)
            }
            .foregroundStyle(Color.white.opacity(0.74))
        }
        .frame(width: infoCoverWidth, height: infoCoverHeight)
        .overlay(
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .stroke(Color.white.opacity(0.22), lineWidth: 1)
        )
    }

    @ViewBuilder
    private func headerMetadataPillRow(info: InteractivePlayerHeaderInfo) -> some View {
        let itemType = info.itemTypeLabel.trimmingCharacters(in: .whitespacesAndNewlines)
        let translationModel = info.translationModel?.trimmingCharacters(in: .whitespacesAndNewlines)
        if isPhonePortrait {
            VStack(alignment: .leading, spacing: 4 * min(infoPillScale, 1.2)) {
                headerMetadataPills(itemType: itemType, translationModel: translationModel)
            }
        } else {
            HStack(spacing: 6 * min(infoPillScale, 1.35)) {
                headerMetadataPills(itemType: itemType, translationModel: translationModel)
            }
        }
    }

    @ViewBuilder
    private func headerMetadataPills(itemType: String, translationModel: String?) -> some View {
        if let translationModel, !translationModel.isEmpty {
            headerMetadataPill(label: translationModel, systemImage: "sparkles")
        }
    }

    private func headerMetadataPill(label: String, systemImage: String) -> some View {
        HStack(spacing: 4 * min(infoPillScale, 1.4)) {
            Image(systemName: systemImage)
                .font(eyebrowFont)
            Text(label)
                .font(eyebrowFont)
                .lineLimit(1)
                .minimumScaleFactor(0.78)
        }
        .foregroundStyle(Color.white.opacity(0.82))
        .padding(.horizontal, 8 * min(infoPillScale, 1.4))
        .padding(.vertical, 3 * min(infoPillScale, 1.4))
        .background(PlayerHeaderPillBackground(isActive: true, isProminent: true))
    }

    private var headerIdentitySheen: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(
                LinearGradient(
                    colors: [
                        Color.white.opacity(0.12),
                        Color.white.opacity(0.02),
                        Color.clear
                    ],
                    startPoint: .topTrailing,
                    endPoint: .bottomLeading
                )
            )
            .frame(
                width: (isTV ? 260 : 160) * min(infoHeaderScale, 1.2),
                height: (isTV ? 80 : 52) * min(infoHeaderScale, 1.2)
            )
            .offset(x: (isTV ? 44 : 28) * min(infoHeaderScale, 1.2), y: -(isTV ? 24 : 16) * min(infoHeaderScale, 1.2))
            .allowsHitTesting(false)
    }

    private func itemTypeSystemImage(for itemType: String) -> String {
        let normalized = itemType.lowercased()
        if normalized.contains("subtitle") || normalized.contains("caption") {
            return "captions.bubble"
        }
        if normalized.contains("video") || normalized.contains("youtube") || normalized.contains("tv") {
            return "play.rectangle"
        }
        if normalized.contains("job") {
            return "briefcase"
        }
        return "book.closed"
    }

    private func headerTitle(for info: InteractivePlayerHeaderInfo) -> String {
        let title = info.title.trimmingCharacters(in: .whitespacesAndNewlines)
        return title.isEmpty ? "Untitled" : title
    }

    private func headerIdentitySubtitle(for info: InteractivePlayerHeaderInfo) -> String? {
        let author = info.author.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !author.isEmpty else {
            return nil
        }
        return "by \(author)"
    }

    private func headerCoverInitial(for info: InteractivePlayerHeaderInfo) -> String {
        String(headerTitle(for: info).prefix(1)).uppercased()
    }
}
