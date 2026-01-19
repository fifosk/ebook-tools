import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

extension InteractivePlayerView {
    var baseContent: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            playerContent
        }
    }

    var playerContent: some View {
        playerContentWrapped()
    }

    private func playerContentWrapped() -> some View {
        let viewModel = self.viewModel
        let audioCoordinator = self.audioCoordinator
        var view = AnyView(playerStack)
        #if !os(tvOS)
        view = AnyView(view.simultaneousGesture(menuToggleGesture, including: .subviews))
        #endif
        view = AnyView(view.onAppear {
            loadLlmModelsIfNeeded()
            refreshBookmarks()
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: audioCoordinator.isPlaying)
            configureReadingBed()
            #if os(tvOS)
            if !didSetInitialFocus {
                didSetInitialFocus = true
                Task { @MainActor in
                    focusedArea = .transcript
                }
            }
            #endif
        })
        view = AnyView(view.onChange(of: viewModel.selectedChunk?.id) { _, _ in
            guard let chunk = viewModel.selectedChunk else { return }
            clearLinguistState()
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: audioCoordinator.isPlaying)
            if isMenuVisible && !audioCoordinator.isPlaying {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
            } else {
                frozenTranscriptSentences = nil
            }
        })
        view = AnyView(view.onChange(of: trackAvailabilitySignature) { _, _ in
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
        })
        view = AnyView(view.onChange(of: viewModel.highlightingTime) { _, _ in
            guard !isMenuVisible else { return }
            guard focusedArea != .controls && focusedArea != .bubble else { return }
            guard let chunk = viewModel.selectedChunk else { return }
            if audioCoordinator.isPlaying {
                viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: true)
                return
            }
            syncSelectedSentence(for: chunk)
        })
        view = AnyView(view.onChange(of: viewModel.readingBedURL) { _, _ in
            configureReadingBed()
        })
        view = AnyView(view.onChange(of: readingBedEnabled) { _, _ in
            updateReadingBedPlayback()
        })
        view = AnyView(view.onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
            handleNarrationPlaybackChange(isPlaying: isPlaying)
            if isPlaying {
                clearLinguistState()
            }
            if isPlaying {
                frozenTranscriptSentences = nil
                viewModel.prefetchAdjacentSentencesIfNeeded(isPlaying: true)
            } else if let chunk = viewModel.selectedChunk {
                syncPausedSelection(for: chunk)
                if isMenuVisible {
                    frozenTranscriptSentences = transcriptSentences(for: chunk)
                }
            }
        })
        view = AnyView(view.onChange(of: visibleTracks) { _, _ in
            clearLinguistState()
            if isMenuVisible, !audioCoordinator.isPlaying, let chunk = viewModel.selectedChunk {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
            }
        })
        view = AnyView(view.onChange(of: isMenuVisible) { _, visible in
            guard let chunk = viewModel.selectedChunk else { return }
            if visible && !audioCoordinator.isPlaying {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
            } else {
                frozenTranscriptSentences = nil
            }
            updateReadingBedPlayback()
        })
        view = AnyView(view.onChange(of: bookmarkIdentityKey) { _, _ in
            refreshBookmarks()
        })
        view = AnyView(
            view.onReceive(NotificationCenter.default.publisher(for: PlaybackBookmarkStore.didChangeNotification)) { notification in
                guard let jobId = resolvedBookmarkJobId else { return }
                let userId = resolvedBookmarkUserId
                if let changedUser = notification.userInfo?["userId"] as? String, changedUser != userId {
                    return
                }
                bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: userId)
            }
        )
        view = AnyView(view.onChange(of: readingBedCoordinator.isPlaying) { _, isPlaying in
            guard !isPlaying else { return }
            guard readingBedEnabled else { return }
            guard audioCoordinator.isPlaybackRequested else { return }
            updateReadingBedPlayback()
        })
        view = AnyView(view.onDisappear {
            readingBedPauseTask?.cancel()
            readingBedPauseTask = nil
            readingBedCoordinator.reset()
            clearLinguistState()
        })
        return view
    }

    private var playerStack: some View {
        ZStack(alignment: .top) {
            playerMainLayer
            playerOverlayLayer
        }
    }

    @ViewBuilder
    private var playerMainLayer: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let chunk = viewModel.selectedChunk {
                interactiveContent(for: chunk)
            } else {
                Text("No interactive chunks were returned for this job.")
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    @ViewBuilder
    private var playerOverlayLayer: some View {
        if let chunk = viewModel.selectedChunk, (shouldShowHeaderOverlay || isTV) {
            playerInfoOverlay(for: chunk)
        }
        if let chunk = viewModel.selectedChunk {
            menuOverlay(for: chunk)
        }
        headerToggleButton
        trackpadSwipeLayer
        shortcutHelpOverlay
        keyboardShortcutLayer
    }

    var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    var isShortcutHelpVisible: Bool {
        isShortcutHelpPinned || isShortcutHelpModifierActive
    }

    @ViewBuilder
    func interactiveContent(for chunk: InteractiveChunk) -> some View {
        let transcriptSentences = frozenTranscriptSentences ?? transcriptSentences(for: chunk)
        InteractiveTranscriptView(
            viewModel: viewModel,
            audioCoordinator: audioCoordinator,
            sentences: transcriptSentences,
            selection: linguistSelection,
            selectionRange: linguistSelectionRange,
            bubble: linguistBubble,
            lookupLanguage: resolvedLookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            onLookupLanguageChange: { storedLookupLanguage = $0 },
            llmModel: resolvedLlmModel ?? MyLinguistPreferences.defaultLlmModel,
            llmModelOptions: llmModelOptions,
            onLlmModelChange: { storedLlmModel = $0 },
            playbackPrimaryKind: playbackPrimaryKind(for: chunk),
            visibleTracks: visibleTracks,
            onToggleTrack: { kind in
                toggleTrackIfAvailable(kind)
            },
            isMenuVisible: isMenuVisible,
            trackFontScale: trackFontScale,
            minTrackFontScale: trackFontScaleMin,
            maxTrackFontScale: trackFontScaleMax,
            autoScaleEnabled: autoScaleEnabled,
            linguistFontScale: linguistFontScale,
            canIncreaseLinguistFont: linguistFontScale < linguistFontScaleMax - 0.001,
            canDecreaseLinguistFont: linguistFontScale > linguistFontScaleMin + 0.001,
            focusedArea: $focusedArea,
            onSkipSentence: { delta in
                viewModel.skipSentence(forward: delta > 0)
            },
            onNavigateTrack: { delta in
                handleTrackNavigation(delta, in: chunk)
            },
            onShowMenu: {
                showMenu()
            },
            onHideMenu: {
                hideMenu()
            },
            onLookup: {
                handleLinguistLookup(in: chunk)
            },
            onLookupToken: { sentenceIndex, variantKind, tokenIndex, token in
                handleLinguistLookup(
                    sentenceIndex: sentenceIndex,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    token: token
                )
            },
            onSeekToken: { sentenceIndex, sentenceNumber, variantKind, tokenIndex, seekTime in
                handleTokenSeek(
                    sentenceIndex: sentenceIndex,
                    sentenceNumber: sentenceNumber,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    seekTime: seekTime,
                    in: chunk
                )
            },
            onUpdateSelectionRange: { range, selection in
                linguistSelection = selection
                linguistSelectionRange = range
            },
            onIncreaseLinguistFont: { handleKeyboardFontAdjust(increase: true) },
            onDecreaseLinguistFont: { handleKeyboardFontAdjust(increase: false) },
            onSetTrackFontScale: { setTrackFontScale($0) },
            onSetLinguistFontScale: { setLinguistFontScale($0) },
            onCloseBubble: {
                closeLinguistBubble()
            },
            onTogglePlayback: {
                audioCoordinator.togglePlayback()
            }
        )
        .padding(.top, transcriptTopPadding)
    }

    @ViewBuilder
    func menuOverlay(for chunk: InteractiveChunk) -> some View {
        if isMenuVisible {
            VStack(alignment: .leading, spacing: 12) {
                menuDragHandle
                if let summary = viewModel.highlightingSummary {
                    Text(summary)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                controlBar(chunk)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(menuBackground)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: Color.black.opacity(0.25), radius: 12, x: 0, y: 6)
            .transition(.move(edge: .top).combined(with: .opacity))
            .accessibilityAddTraits(.isModal)
            .zIndex(2)
        }
    }

    @ViewBuilder
    var keyboardShortcutLayer: some View {
        #if os(iOS)
        if isPad {
            KeyboardCommandHandler(
                onPlayPause: { audioCoordinator.togglePlayback() },
                onPrevious: {
                    if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: false)
                    } else {
                        handleWordNavigation(-1, in: viewModel.selectedChunk)
                    }
                },
                onNext: {
                    if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: true)
                    } else {
                        handleWordNavigation(1, in: viewModel.selectedChunk)
                    }
                },
                onPreviousWord: { handleWordNavigation(-1, in: viewModel.selectedChunk) },
                onNextWord: { handleWordNavigation(1, in: viewModel.selectedChunk) },
                onExtendSelectionBackward: {
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleWordRangeSelection(-1, in: chunk)
                },
                onExtendSelectionForward: {
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleWordRangeSelection(1, in: chunk)
                },
                onLookup: {
                    guard !audioCoordinator.isPlaying else { return }
                    guard let chunk = viewModel.selectedChunk else { return }
                    handleLinguistLookup(in: chunk)
                },
                onIncreaseFont: { adjustTrackFontScale(by: trackFontScaleStep) },
                onDecreaseFont: { adjustTrackFontScale(by: -trackFontScaleStep) },
                onToggleOriginal: { toggleTrackIfAvailable(.original) },
                onToggleTransliteration: { toggleTrackIfAvailable(.transliteration) },
                onToggleTranslation: { toggleTrackIfAvailable(.translation) },
                onToggleOriginalAudio: { toggleAudioTrack(.original) },
                onToggleTranslationAudio: { toggleAudioTrack(.translation) },
                onToggleReadingBed: { toggleReadingBed() },
                onIncreaseLinguistFont: { handleKeyboardFontAdjust(increase: true) },
                onDecreaseLinguistFont: { handleKeyboardFontAdjust(increase: false) },
                onToggleShortcutHelp: { toggleShortcutHelp() },
                onToggleHeader: { toggleHeaderCollapsed() },
                onIncreaseHeaderScale: { adjustHeaderScale(by: headerScaleStep) },
                onDecreaseHeaderScale: { adjustHeaderScale(by: -headerScaleStep) },
                onOptionKeyDown: { showShortcutHelpModifier() },
                onOptionKeyUp: { hideShortcutHelpModifier() },
                onShowMenu: {
                    if audioCoordinator.isPlaying {
                        showMenu()
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(1, in: chunk)
                    }
                },
                onHideMenu: {
                    if audioCoordinator.isPlaying {
                        hideMenu()
                    } else if let chunk = viewModel.selectedChunk {
                        handleTrackNavigation(-1, in: chunk)
                    }
                }
            )
            .frame(width: 0, height: 0)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    @ViewBuilder
    var trackpadSwipeLayer: some View {
        #if os(iOS)
        if isPad {
            TrackpadSwipeHandler(
                onSwipeDown: { showMenu() },
                onSwipeUp: { hideMenu() }
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    func handleKeyboardFontAdjust(increase: Bool) {
        if linguistBubble != nil {
            adjustLinguistFontScale(by: increase ? linguistFontScaleStep : -linguistFontScaleStep)
        } else {
            adjustTrackFontScale(by: increase ? trackFontScaleStep : -trackFontScaleStep)
        }
    }

    @ViewBuilder
    var shortcutHelpOverlay: some View {
        #if os(iOS)
        if isPad, isShortcutHelpVisible {
            ShortcutHelpOverlayView(onDismiss: { dismissShortcutHelp() })
                .transition(.opacity)
                .zIndex(4)
        }
        #else
        EmptyView()
        #endif
    }

    #if !os(tvOS)
    var menuToggleGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                guard abs(vertical) > abs(horizontal) else { return }
                if vertical > 24 {
                    showMenu()
                } else if vertical < -24 {
                    hideMenu()
                }
            }
    }
    #endif

    func showMenu() {
        guard !isMenuVisible else { return }
        guard viewModel.selectedChunk != nil else { return }
        resumePlaybackAfterMenu = audioCoordinator.isPlaybackRequested || audioCoordinator.isPlaying
        if resumePlaybackAfterMenu {
            audioCoordinator.pause()
        }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = true
        }
        #if os(tvOS)
        focusedArea = .controls
        #endif
    }

    func hideMenu() {
        guard isMenuVisible else { return }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = false
        }
        if resumePlaybackAfterMenu {
            audioCoordinator.play()
        }
        resumePlaybackAfterMenu = false
        #if os(tvOS)
        focusedArea = .transcript
        #endif
    }

    func playerInfoOverlay(for chunk: InteractiveChunk) -> some View {
        let variant = resolveInfoVariant()
        let label = headerInfo?.itemTypeLabel.isEmpty == false ? headerInfo?.itemTypeLabel : "Job"
        let slideLabel = slideIndicatorLabel(for: chunk)
        let timelineLabel = audioTimelineLabel(for: chunk)
        let showHeaderContent = !isHeaderCollapsed
        let headerView = HStack(alignment: .top, spacing: 12) {
            if showHeaderContent {
                PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                if let headerInfo {
                    infoBadgeView(info: headerInfo, chunk: chunk)
                }
            }
            Spacer(minLength: 12)
            if showHeaderContent || isTV {
                VStack(alignment: .trailing, spacing: 6) {
                    if showHeaderContent {
                        if let slideLabel {
                            slideIndicatorView(label: slideLabel)
                        }
                        if let timelineLabel {
                            audioTimelineView(label: timelineLabel)
                        }
                    } else if let timelineLabel {
                        audioTimelineView(label: timelineLabel)
                    }
                    #if os(tvOS)
                    tvHeaderTogglePill
                    #endif
                }
            }
        }
        .padding(.horizontal, 6)
        .padding(.top, 6)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .allowsHitTesting(true)
        .zIndex(1)
        return headerMagnifyWrapper(headerView)
    }

    func infoBadgeView(info: InteractivePlayerHeaderInfo, chunk: InteractiveChunk) -> some View {
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        return HStack(alignment: .top, spacing: 8) {
            if info.coverURL != nil || info.secondaryCoverURL != nil {
                PlayerCoverStackView(
                    primaryURL: info.coverURL,
                    secondaryURL: info.secondaryCoverURL,
                    width: infoCoverWidth,
                    height: infoCoverHeight,
                    isTV: isTV
                )
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(info.title.isEmpty ? "Untitled" : info.title)
                    .font(infoTitleFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                if !info.author.isEmpty {
                    Text(info.author)
                        .font(infoMetaFont)
                        .foregroundStyle(Color.white.opacity(0.75))
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }
                if !info.languageFlags.isEmpty {
                    PlayerLanguageFlagRow(
                        flags: info.languageFlags,
                        modelLabel: info.translationModel,
                        isTV: isTV,
                        sizeScale: infoHeaderScale,
                        activeRoles: activeRoles,
                        availableRoles: availableRoles,
                        onToggleRole: { role in
                            toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
                        }
                    )
                }
            }
        }
    }

    func slideIndicatorView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.85))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.6))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )
            )
    }

    func audioTimelineView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.75))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.5))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.18), lineWidth: 1)
                    )
            )
    }

    var infoCoverWidth: CGFloat {
        PlayerInfoMetrics.coverWidth(isTV: isTV) * infoHeaderScale
    }

    var infoCoverHeight: CGFloat {
        PlayerInfoMetrics.coverHeight(isTV: isTV) * infoHeaderScale
    }

    var infoTitleFont: Font {
        #if os(tvOS)
        return .headline
        #else
        if isPad {
            return scaledHeaderFont(style: .subheadline, weight: .semibold)
        }
        return .subheadline.weight(.semibold)
        #endif
    }

    var infoMetaFont: Font {
        #if os(tvOS)
        return .callout
        #else
        if isPad {
            return scaledHeaderFont(style: .caption1, weight: .regular)
        }
        return .caption
        #endif
    }

    var infoIndicatorFont: Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        if isPad {
            return scaledHeaderFont(style: .caption1, weight: .semibold)
        }
        return .caption.weight(.semibold)
        #endif
    }

    private var infoHeaderScale: CGFloat {
        #if os(iOS)
        let base: CGFloat = isPad ? 2.0 : 1.0
        return base * headerScale
        #else
        return 1.0
        #endif
    }

    private func scaledHeaderFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: baseSize * infoHeaderScale, weight: weight)
        #else
        return .system(size: 16 * infoHeaderScale, weight: weight)
        #endif
    }

    var headerScale: CGFloat {
        get { CGFloat(headerScaleValue) }
        nonmutating set { headerScaleValue = Double(newValue) }
    }

    func adjustHeaderScale(by delta: CGFloat) {
        setHeaderScale(headerScale + delta)
    }

    func setHeaderScale(_ value: CGFloat) {
        let updated = min(max(value, headerScaleMin), headerScaleMax)
        if updated != headerScale {
            headerScale = updated
        }
    }

    @ViewBuilder
    private func headerMagnifyWrapper<Content: View>(_ content: Content) -> some View {
        #if os(iOS)
        if isPad {
            content.simultaneousGesture(headerMagnifyGesture, including: .all)
        } else {
            content
        }
        #else
        content
        #endif
    }

    #if os(iOS)
    private var headerMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                if headerMagnifyStartScale == nil {
                    headerMagnifyStartScale = headerScale
                }
                let startScale = headerMagnifyStartScale ?? headerScale
                setHeaderScale(startScale * value)
            }
            .onEnded { _ in
                headerMagnifyStartScale = nil
            }
    }
    #endif

    var infoHeaderReservedHeight: CGFloat {
        #if os(tvOS)
        return PlayerInfoMetrics.badgeHeight(isTV: true) + 24
        #else
        let baseHeight = PlayerInfoMetrics.badgeHeight(isTV: false) * infoHeaderScale
        let padding = isPad ? 20 * infoHeaderScale : 16
        return baseHeight + padding
        #endif
    }

    var transcriptTopPadding: CGFloat {
        #if os(iOS) || os(tvOS)
        return isHeaderCollapsed ? 8 : infoHeaderReservedHeight
        #else
        return infoHeaderReservedHeight
        #endif
    }

    var shouldShowHeaderOverlay: Bool {
        return !isHeaderCollapsed
    }

    @ViewBuilder
    var headerToggleButton: some View {
        #if os(iOS)
        if let chunk = viewModel.selectedChunk {
            let timelineLabel = audioTimelineLabel(for: chunk)
            HStack(spacing: 8) {
                if isHeaderCollapsed, let timelineLabel {
                    audioTimelineView(label: timelineLabel)
                }
                Button(action: toggleHeaderCollapsed) {
                    Image(systemName: isHeaderCollapsed ? "chevron.down" : "chevron.up")
                        .font(.caption.weight(.semibold))
                        .padding(6)
                        .background(Color.black.opacity(0.45), in: Circle())
                        .foregroundStyle(.white)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(isHeaderCollapsed ? "Show info header" : "Hide info header")
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing)
            .padding(.top, 6)
            .padding(.trailing, 6)
            .zIndex(2)
        }
        #else
        EmptyView()
        #endif
    }

    #if os(tvOS)
    var tvHeaderTogglePill: some View {
        Button(action: toggleHeaderCollapsed) {
            Image(systemName: isHeaderCollapsed ? "chevron.down" : "chevron.up")
                .font(.caption.weight(.semibold))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.black.opacity(0.6), in: Capsule())
                .foregroundStyle(.white)
        }
        .buttonStyle(.plain)
        .focusable(focusedArea == .controls)
        .allowsHitTesting(focusedArea == .controls)
        .focused($focusedArea, equals: .controls)
        .accessibilityLabel(isHeaderCollapsed ? "Show header" : "Hide header")
    }
    #endif

    func toggleHeaderCollapsed() {
        withAnimation(.easeInOut(duration: 0.2)) {
            isHeaderCollapsed.toggle()
        }
    }

    func playbackPrimaryKind(for chunk: InteractiveChunk) -> TextPlayerVariantKind? {
        guard audioCoordinator.isPlaying else { return nil }
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

        var label = jobEnd != nil
            ? "Playing sentence \(displayCurrent) of \(jobEnd ?? displayCurrent)"
            : "Playing sentence \(displayCurrent)"

        var suffixParts: [String] = []
        if let jobEnd {
            let span = max(jobEnd - jobStart, 0)
            let ratio = span > 0 ? Double(displayCurrent - jobStart) / Double(span) : 1
            if ratio.isFinite {
                let percent = min(max(Int(round(ratio * 100)), 0), 100)
                suffixParts.append("Job \(percent)%")
            }
        }
        if let bookTotal = bookTotalSentences(jobEnd: jobEnd) {
            let ratio = bookTotal > 0 ? Double(displayCurrent) / Double(bookTotal) : 1
            if ratio.isFinite {
                let percent = min(max(Int(round(ratio * 100)), 0), 100)
                suffixParts.append("Book \(percent)%")
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
        return "\(played) / \(remaining) remaining"
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
        var activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        if activeRoles.isEmpty {
            activeRoles = availableRoles
        }
        if activeRoles.contains(role) {
            if activeRoles.count > 1 {
                activeRoles.remove(role)
            } else {
                return
            }
        } else {
            activeRoles.insert(role)
        }
        selectAudioTrack(for: chunk, preferredRoles: activeRoles, availableRoles: availableRoles)
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
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
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
