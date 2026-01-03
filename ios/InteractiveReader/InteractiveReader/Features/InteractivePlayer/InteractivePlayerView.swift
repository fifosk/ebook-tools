import AVFoundation
import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

private enum InteractivePlayerFocusArea: Hashable {
    case controls
    case transcript
}

struct InteractivePlayerHeaderInfo: Equatable {
    let title: String
    let author: String
    let itemTypeLabel: String
    let coverURL: URL?
    let secondaryCoverURL: URL?
    let languageFlags: [LanguageFlagEntry]
}

struct InteractivePlayerView: View {
    @ObservedObject var viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let showImageReel: Binding<Bool>?
    let showsScrubber: Bool
    let linguistInputLanguage: String
    let linguistLookupLanguage: String
    let linguistExplanationLanguage: String
    let headerInfo: InteractivePlayerHeaderInfo?
    @State private var readingBedCoordinator = AudioPlayerCoordinator()
    @State private var readingBedEnabled = true
    @State private var scrubbedTime: Double?
    @State private var visibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    @State private var selectedSentenceID: Int?
    @State private var linguistSelection: TextPlayerWordSelection?
    @State private var linguistBubble: MyLinguistBubbleState?
    @State private var linguistLookupTask: Task<Void, Never>?
    @State private var linguistSpeechTask: Task<Void, Never>?
    @State private var isMenuVisible = false
    @State private var isHeaderCollapsed = false
    @State private var frozenTranscriptSentences: [TextPlayerSentenceDisplay]?
    @State private var isShortcutHelpPinned = false
    @State private var isShortcutHelpModifierActive = false
    @State private var readingBedPauseTask: Task<Void, Never>?
    @AppStorage("interactive.trackFontScale") private var trackFontScaleValue: Double =
        Double(InteractivePlayerView.defaultTrackFontScale)
    @AppStorage("interactive.linguistFontScale") private var linguistFontScaleValue: Double =
        Double(InteractivePlayerView.defaultLinguistFontScale)
    @StateObject private var pronunciationSpeaker = PronunciationSpeaker()
    #if os(tvOS)
    @State private var didSetInitialFocus = false
    #endif
    @FocusState private var focusedArea: InteractivePlayerFocusArea?

    private let playbackRates: [Double] = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
    private let readingBedVolume: Double = 0.08
    private let readingBedPauseDelayNanos: UInt64 = 250_000_000
    private let trackFontScaleStep: CGFloat = 0.1
    private let trackFontScaleMin: CGFloat = 1.0
    private let trackFontScaleMax: CGFloat = 3.0
    private let linguistFontScaleMin: CGFloat = 0.8
    private let linguistFontScaleMax: CGFloat = 1.6
    private let linguistFontScaleStep: CGFloat = 0.05
    private static var defaultTrackFontScale: CGFloat {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad ? 2.0 : 1.0
        #else
        return 1.0
        #endif
    }
    private static let defaultLinguistFontScale: CGFloat = 1.2

    init(
        viewModel: InteractivePlayerViewModel,
        audioCoordinator: AudioPlayerCoordinator,
        showImageReel: Binding<Bool>? = nil,
        showsScrubber: Bool = true,
        linguistInputLanguage: String = "",
        linguistLookupLanguage: String = "English",
        linguistExplanationLanguage: String = "English",
        headerInfo: InteractivePlayerHeaderInfo? = nil
    ) {
        self._viewModel = ObservedObject(wrappedValue: viewModel)
        self._audioCoordinator = ObservedObject(wrappedValue: audioCoordinator)
        self.showImageReel = showImageReel
        self.showsScrubber = showsScrubber
        self.linguistInputLanguage = linguistInputLanguage
        self.linguistLookupLanguage = linguistLookupLanguage
        self.linguistExplanationLanguage = linguistExplanationLanguage
        self.headerInfo = headerInfo
    }

    var body: some View {
        #if os(tvOS)
        baseContent
            .onPlayPauseCommand {
                audioCoordinator.togglePlayback()
            }
            .applyIf(!isMenuVisible) { view in
                view.onMoveCommand { direction in
                    guard focusedArea == .transcript else { return }
                    guard let chunk = viewModel.selectedChunk else { return }
                    switch direction {
                    case .left:
                        if audioCoordinator.isPlaying {
                            viewModel.skipSentence(forward: false)
                        } else {
                            handleWordNavigation(-1, in: chunk)
                        }
                    case .right:
                        if audioCoordinator.isPlaying {
                            viewModel.skipSentence(forward: true)
                        } else {
                            handleWordNavigation(1, in: chunk)
                        }
                    case .up:
                        if !audioCoordinator.isPlaying {
                            handleTrackNavigation(-1, in: chunk)
                        }
                    case .down:
                        showMenu()
                    default:
                        break
                    }
                }
            }
            .applyIf(isMenuVisible) { view in
                view.onMoveCommand { direction in
                    if direction == .up {
                        hideMenu()
                    }
                }
            }
        #else
        baseContent
        #endif
    }

    private var baseContent: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            playerContent
        }
    }

    private var playerContent: some View {
        ZStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 12) {
                if let chunk = viewModel.selectedChunk {
                    interactiveContent(for: chunk)
                } else {
                    Text("No interactive chunks were returned for this job.")
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)

            if let chunk = viewModel.selectedChunk, shouldShowHeaderOverlay {
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
        #if !os(tvOS)
        .simultaneousGesture(menuToggleGesture, including: .subviews)
        #endif
        .onAppear {
            guard let chunk = viewModel.selectedChunk else { return }
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            configureReadingBed()
            #if os(tvOS)
            if !didSetInitialFocus {
                didSetInitialFocus = true
                Task { @MainActor in
                    focusedArea = .transcript
                }
            }
            #endif
        }
        .onChange(of: viewModel.selectedChunk?.id) { _, _ in
            guard let chunk = viewModel.selectedChunk else { return }
            clearLinguistState()
            applyDefaultTrackSelection(for: chunk)
            syncSelectedSentence(for: chunk)
            if isMenuVisible && !audioCoordinator.isPlaying {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
            } else {
                frozenTranscriptSentences = nil
            }
        }
        .onChange(of: viewModel.highlightingTime) { _, _ in
            guard !isMenuVisible else { return }
            guard focusedArea != .controls else { return }
            guard let chunk = viewModel.selectedChunk else { return }
            if audioCoordinator.isPlaying {
                return
            }
            syncSelectedSentence(for: chunk)
        }
        .onChange(of: viewModel.readingBedURL) { _, _ in
            configureReadingBed()
        }
        .onChange(of: readingBedEnabled) { _, _ in
            updateReadingBedPlayback()
        }
        .onChange(of: audioCoordinator.isPlaying) { _, isPlaying in
            handleNarrationPlaybackChange(isPlaying: isPlaying)
            if isPlaying {
                clearLinguistState()
            }
            if isPlaying {
                frozenTranscriptSentences = nil
            } else if isMenuVisible, let chunk = viewModel.selectedChunk {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
            }
        }
        .onChange(of: visibleTracks) { _, _ in
            clearLinguistState()
            if isMenuVisible, !audioCoordinator.isPlaying, let chunk = viewModel.selectedChunk {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
            }
        }
        .onChange(of: isMenuVisible) { _, visible in
            guard let chunk = viewModel.selectedChunk else { return }
            if visible && !audioCoordinator.isPlaying {
                frozenTranscriptSentences = transcriptSentences(for: chunk)
            } else {
                frozenTranscriptSentences = nil
            }
            updateReadingBedPlayback()
        }
        .onChange(of: readingBedCoordinator.isPlaying) { _, isPlaying in
            guard !isPlaying else { return }
            guard readingBedEnabled else { return }
            guard audioCoordinator.isPlaybackRequested else { return }
            updateReadingBedPlayback()
        }
        .onDisappear {
            readingBedPauseTask?.cancel()
            readingBedPauseTask = nil
            readingBedCoordinator.reset()
            clearLinguistState()
        }
    }

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    private var isShortcutHelpVisible: Bool {
        isShortcutHelpPinned || isShortcutHelpModifierActive
    }

    @ViewBuilder
    private func interactiveContent(for chunk: InteractiveChunk) -> some View {
        let transcriptSentences = frozenTranscriptSentences ?? transcriptSentences(for: chunk)
        InteractiveTranscriptView(
            viewModel: viewModel,
            audioCoordinator: audioCoordinator,
            sentences: transcriptSentences,
            selection: linguistSelection,
            bubble: linguistBubble,
            isMenuVisible: isMenuVisible,
            trackFontScale: trackFontScale,
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
            onIncreaseLinguistFont: { adjustLinguistFontScale(by: linguistFontScaleStep) },
            onDecreaseLinguistFont: { adjustLinguistFontScale(by: -linguistFontScaleStep) },
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
    private func menuOverlay(for chunk: InteractiveChunk) -> some View {
        if isMenuVisible {
            let reelURLs = imageReelURLs(for: chunk)
            VStack(alignment: .leading, spacing: 12) {
                menuDragHandle
                if let headerInfo {
                    menuHeader(info: headerInfo, reelURLs: reelURLs)
                }
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
    private var keyboardShortcutLayer: some View {
        #if os(iOS)
        if isPad {
            KeyboardCommandHandler(
                onPlayPause: { audioCoordinator.togglePlayback() },
                onPrevious: { viewModel.skipSentence(forward: false) },
                onNext: { viewModel.skipSentence(forward: true) },
                onPreviousWord: { handleWordNavigation(-1, in: viewModel.selectedChunk) },
                onNextWord: { handleWordNavigation(1, in: viewModel.selectedChunk) },
                onIncreaseFont: { adjustTrackFontScale(by: trackFontScaleStep) },
                onDecreaseFont: { adjustTrackFontScale(by: -trackFontScaleStep) },
                onToggleOriginal: { toggleTrackIfAvailable(.original) },
                onToggleTransliteration: { toggleTrackIfAvailable(.transliteration) },
                onToggleTranslation: { toggleTrackIfAvailable(.translation) },
                onToggleOriginalAudio: { toggleAudioTrack(.original) },
                onToggleTranslationAudio: { toggleAudioTrack(.translation) },
                onIncreaseLinguistFont: { adjustLinguistFontScale(by: linguistFontScaleStep) },
                onDecreaseLinguistFont: { adjustLinguistFontScale(by: -linguistFontScaleStep) },
                onToggleShortcutHelp: { toggleShortcutHelp() },
                onOptionKeyDown: { showShortcutHelpModifier() },
                onOptionKeyUp: { hideShortcutHelpModifier() },
                onShowMenu: { showMenu() },
                onHideMenu: { hideMenu() }
            )
            .frame(width: 0, height: 0)
            .accessibilityHidden(true)
        }
        #else
        EmptyView()
        #endif
    }

    @ViewBuilder
    private var trackpadSwipeLayer: some View {
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

    @ViewBuilder
    private var shortcutHelpOverlay: some View {
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

    private var menuDragHandle: some View {
        #if os(tvOS)
        EmptyView()
        #else
        Capsule()
            .fill(Color.white.opacity(0.25))
            .frame(width: 36, height: 4)
            .frame(maxWidth: .infinity)
            .padding(.top, 2)
            .contentShape(Rectangle())
        #endif
    }

    #if !os(tvOS)
    private var menuToggleGesture: some Gesture {
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

    private func showMenu() {
        guard !isMenuVisible else { return }
        guard viewModel.selectedChunk != nil else { return }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = true
        }
        #if os(tvOS)
        focusedArea = .controls
        #endif
    }

    private func hideMenu() {
        guard isMenuVisible else { return }
        withAnimation(.easeOut(duration: 0.2)) {
            isMenuVisible = false
        }
        #if os(tvOS)
        focusedArea = .transcript
        #endif
    }

    @ViewBuilder
    private func menuHeader(info: InteractivePlayerHeaderInfo, reelURLs: [URL]) -> some View {
        HStack(alignment: .top, spacing: 12) {
            if let coverURL = info.coverURL {
                AsyncImage(url: coverURL) { phase in
                    if let image = phase.image {
                        image.resizable().scaledToFill()
                    } else {
                        Color.gray.opacity(0.2)
                    }
                }
                .frame(width: menuCoverWidth, height: menuCoverHeight)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                )
            }
            VStack(alignment: .leading, spacing: 6) {
                Text(info.title.isEmpty ? "Untitled" : info.title)
                    .font(menuTitleFont)
                    .lineLimit(2)
                    .minimumScaleFactor(0.85)
                Text(info.author.isEmpty ? "Unknown author" : info.author)
                    .font(menuAuthorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)
                Text(info.itemTypeLabel)
                    .font(menuMetaFont)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.2), in: Capsule())
            }
            if !reelURLs.isEmpty {
                Spacer(minLength: 12)
                InteractivePlayerImageReel(urls: reelURLs, height: menuCoverHeight)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }

    private func playerInfoOverlay(for chunk: InteractiveChunk) -> some View {
        let variant = resolveInfoVariant()
        let label = headerInfo?.itemTypeLabel.isEmpty == false ? headerInfo?.itemTypeLabel : "Job"
        let slideLabel = slideIndicatorLabel(for: chunk)
        let timelineLabel = audioTimelineLabel(for: chunk)
        return HStack(alignment: .top, spacing: 12) {
            PlayerChannelBugView(variant: variant, label: label)
            if let headerInfo {
                infoBadgeView(info: headerInfo)
            }
            Spacer(minLength: 12)
            if slideLabel != nil || timelineLabel != nil {
                VStack(alignment: .trailing, spacing: 6) {
                    if let slideLabel {
                        slideIndicatorView(label: slideLabel)
                    }
                    if let timelineLabel {
                        audioTimelineView(label: timelineLabel)
                    }
                }
            }
        }
        .padding(.horizontal, 6)
        .padding(.top, 6)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .allowsHitTesting(false)
        .zIndex(1)
    }

    private func infoBadgeView(info: InteractivePlayerHeaderInfo) -> some View {
        HStack(alignment: .top, spacing: 8) {
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
                    PlayerLanguageFlagRow(flags: info.languageFlags, isTV: isTV)
                }
            }
        }
    }

    private func slideIndicatorView(label: String) -> some View {
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

    private func audioTimelineView(label: String) -> some View {
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

    private var infoCoverWidth: CGFloat {
        PlayerInfoMetrics.coverWidth(isTV: isTV)
    }

    private var infoCoverHeight: CGFloat {
        PlayerInfoMetrics.coverHeight(isTV: isTV)
    }

    private var infoTitleFont: Font {
        #if os(tvOS)
        return .headline
        #else
        return .subheadline.weight(.semibold)
        #endif
    }

    private var infoMetaFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .caption
        #endif
    }

    private var infoIndicatorFont: Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        return .caption.weight(.semibold)
        #endif
    }

    private var infoHeaderReservedHeight: CGFloat {
        #if os(tvOS)
        return PlayerInfoMetrics.badgeHeight(isTV: true) + 24
        #else
        return PlayerInfoMetrics.badgeHeight(isTV: false) + (isPad ? 20 : 16)
        #endif
    }

    private var transcriptTopPadding: CGFloat {
        #if os(iOS)
        return isHeaderCollapsed ? 8 : infoHeaderReservedHeight
        #else
        return infoHeaderReservedHeight
        #endif
    }

    private var shouldShowHeaderOverlay: Bool {
        #if os(iOS)
        return !isHeaderCollapsed
        #else
        return true
        #endif
    }

    @ViewBuilder
    private var headerToggleButton: some View {
        #if os(iOS)
        if viewModel.selectedChunk != nil {
            Button(action: toggleHeaderCollapsed) {
                Image(systemName: isHeaderCollapsed ? "chevron.down" : "chevron.up")
                    .font(.caption.weight(.semibold))
                    .padding(6)
                    .background(Color.black.opacity(0.45), in: Circle())
                    .foregroundStyle(.white)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(isHeaderCollapsed ? "Show info header" : "Hide info header")
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing)
            .padding(.top, 6)
            .padding(.trailing, 6)
            .zIndex(2)
        }
        #else
        EmptyView()
        #endif
    }

    private func toggleHeaderCollapsed() {
        withAnimation(.easeInOut(duration: 0.2)) {
            isHeaderCollapsed.toggle()
        }
    }

    private func resolveInfoVariant() -> PlayerChannelVariant {
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

    private func slideIndicatorLabel(for chunk: InteractiveChunk) -> String? {
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

    private func audioTimelineLabel(for chunk: InteractiveChunk) -> String? {
        guard let metrics = audioTimelineMetrics(for: chunk) else { return nil }
        let played = formatDurationLabel(metrics.played)
        let remaining = formatDurationLabel(metrics.remaining)
        return "\(played) / \(remaining) remaining"
    }

    private func audioTimelineMetrics(
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

    private func selectedAudioKind(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption.Kind? {
        if let selectedID = viewModel.selectedAudioTrackID,
           let option = chunk.audioOptions.first(where: { $0.id == selectedID }) {
            return option.kind
        }
        return chunk.audioOptions.first?.kind
    }

    private func resolvedAudioDuration(
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

    private func formatDurationLabel(_ value: Double) -> String {
        let total = max(0, Int(value.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    private func currentSentenceNumber(for chunk: InteractiveChunk) -> Int? {
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

    private func bookTotalSentences(jobEnd: Int?) -> Int? {
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

    private var menuCoverWidth: CGFloat {
        #if os(tvOS)
        return 96
        #else
        return 64
        #endif
    }

    private var menuCoverHeight: CGFloat {
        #if os(tvOS)
        return 144
        #else
        return 96
        #endif
    }

    private var menuTitleFont: Font {
        #if os(tvOS)
        return .title2
        #else
        return .title3
        #endif
    }

    private var menuAuthorFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .callout
        #endif
    }

    private var menuMetaFont: Font {
        #if os(tvOS)
        return .caption2
        #else
        return .caption
        #endif
    }

    @ViewBuilder
    private var menuBackground: some View {
        #if os(tvOS)
        Color.black.opacity(0.78)
        #else
        Rectangle()
            .fill(.ultraThinMaterial)
        #endif
    }

    private func imageReelURLs(for chunk: InteractiveChunk) -> [URL] {
        guard let showImageReel, showImageReel.wrappedValue else { return [] }
        guard hasImageReel(for: chunk) else { return [] }
        var urls: [URL] = []
        var seen: Set<String> = []
        for sentence in chunk.sentences {
            guard let path = resolveSentenceImagePath(sentence: sentence, chunk: chunk) else { continue }
            guard !seen.contains(path) else { continue }
            seen.insert(path)
            if let url = viewModel.resolvePath(path) {
                urls.append(url)
            }
            if urls.count >= 7 {
                break
            }
        }
        return urls
    }

    private func resolveSentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String? {
        if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue {
            return path
        }
        guard let rangeFragment = chunk.rangeFragment?.nonEmptyValue else { return nil }
        let sentenceNumber = sentence.displayIndex ?? sentence.id
        guard sentenceNumber > 0 else { return nil }
        let padded = String(format: "%05d", sentenceNumber)
        return "media/images/\(rangeFragment)/sentence_\(padded).png"
    }

    @ViewBuilder
    private func controlBar(_ chunk: InteractiveChunk) -> some View {
        let playbackTime = viewModel.playbackTime(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .center, spacing: 12) {
                chapterPicker()
                sentencePicker(for: chunk)
                textTrackPicker(for: chunk)
                audioPicker(for: chunk)
                readingBedPicker()
                speedPicker()
                Spacer(minLength: 8)
                PlaybackButtonRow(
                    coordinator: audioCoordinator,
                    focusBinding: $focusedArea,
                    onPrevious: { viewModel.skipSentence(forward: false) },
                    onNext: { viewModel.skipSentence(forward: true) }
                )
            }
            #if os(tvOS)
            .transaction { transaction in
                transaction.disablesAnimations = true
            }
            #endif
            if let range = chunk.rangeDescription {
                Text(range)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            if showsScrubber {
                PlaybackScrubberView(
                    coordinator: audioCoordinator,
                    currentTime: playbackTime,
                    duration: playbackDuration,
                    scrubbedTime: $scrubbedTime,
                    onSeek: { target in
                        viewModel.seekPlayback(to: target, in: chunk)
                    }
                )
            }
        }
    }

    private func menuLabel(_ text: String, leadingSystemImage: String? = nil) -> some View {
        HStack(spacing: 6) {
            if let leadingSystemImage {
                Image(systemName: leadingSystemImage)
                    .font(.caption2)
            }
            Text(text)
                .font(.callout)
                .lineLimit(1)
                .truncationMode(.tail)
                .minimumScaleFactor(0.85)
            Image(systemName: "chevron.down")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
    }

    private var scopedChapterEntries: [ChapterNavigationEntry] {
        let chapters = viewModel.chapterEntries
        guard !chapters.isEmpty else { return [] }
        let bounds = jobSentenceBounds
        return chapters.filter { chapter in
            let end = effectiveChapterEnd(for: chapter, boundsEnd: bounds.end)
            if let startBound = bounds.start, end < startBound {
                return false
            }
            if let endBound = bounds.end, chapter.startSentence > endBound {
                return false
            }
            return true
        }
    }

    private var selectedChapterRange: SentenceRange? {
        let chapters = scopedChapterEntries
        guard let chapter = activeChapter(in: chapters) else { return nil }
        return chapterRange(for: chapter, bounds: jobSentenceBounds)
    }

    private var jobSentenceBounds: (start: Int?, end: Int?) {
        guard let context = viewModel.jobContext else { return (nil, nil) }
        var minValue: Int?
        var maxValue: Int?
        for chunk in context.chunks {
            if let start = chunk.startSentence {
                var end = chunk.endSentence ?? start
                if chunk.endSentence == nil {
                    let derivedEnd = chunk.sentences
                        .map { $0.displayIndex ?? $0.id }
                        .max() ?? start
                    end = max(end, derivedEnd)
                }
                minValue = min(minValue ?? start, start)
                maxValue = max(maxValue ?? end, end)
                continue
            }
            for sentence in chunk.sentences {
                let id = sentence.displayIndex ?? sentence.id
                guard id > 0 else { continue }
                minValue = min(minValue ?? id, id)
                maxValue = max(maxValue ?? id, id)
            }
        }
        return (minValue, maxValue)
    }

    private func chapterBinding(entries: [ChapterNavigationEntry]) -> Binding<String> {
        Binding(
            get: {
                activeChapter(in: entries)?.id ?? entries.first?.id ?? ""
            },
            set: { newValue in
                guard let target = entries.first(where: { $0.id == newValue }) else { return }
                selectedSentenceID = target.startSentence
                viewModel.jumpToSentence(target.startSentence, autoPlay: audioCoordinator.isPlaying)
            }
        )
    }

    private func chapterLabel(_ chapter: ChapterNavigationEntry, index: Int) -> String {
        let title = chapter.title.nonEmptyValue ?? "Chapter \(index + 1)"
        let range = chapterRangeLabel(for: chapter)
        if range.isEmpty {
            return title
        }
        return "\(title) • \(range)"
    }

    private func chapterRangeLabel(for chapter: ChapterNavigationEntry) -> String {
        if let end = chapter.endSentence {
            if end > chapter.startSentence {
                return "\(chapter.startSentence)-\(end)"
            }
            return "\(chapter.startSentence)"
        }
        return "\(chapter.startSentence)+"
    }

    private func activeChapter(in chapters: [ChapterNavigationEntry]) -> ChapterNavigationEntry? {
        guard !chapters.isEmpty else { return nil }
        guard let sentenceID = selectedSentenceID else { return chapters.first }
        let boundsEnd = jobSentenceBounds.end
        for chapter in chapters {
            let end = effectiveChapterEnd(for: chapter, boundsEnd: boundsEnd)
            if sentenceID >= chapter.startSentence && sentenceID <= end {
                return chapter
            }
        }
        return chapters.first
    }

    private func chapterRange(
        for chapter: ChapterNavigationEntry,
        bounds: (start: Int?, end: Int?)
    ) -> SentenceRange? {
        let effectiveEnd = effectiveChapterEnd(for: chapter, boundsEnd: bounds.end)
        let start = max(chapter.startSentence, bounds.start ?? chapter.startSentence)
        let end = min(effectiveEnd, bounds.end ?? effectiveEnd)
        guard end >= start else { return nil }
        return SentenceRange(start: start, end: end)
    }

    private func effectiveChapterEnd(for chapter: ChapterNavigationEntry, boundsEnd: Int?) -> Int {
        if let end = chapter.endSentence {
            return max(end, chapter.startSentence)
        }
        if let boundsEnd {
            return max(boundsEnd, chapter.startSentence)
        }
        return chapter.startSentence
    }

    @ViewBuilder
    private func chapterPicker() -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Chapter")
                .font(.caption)
                .foregroundStyle(.secondary)
            let chapters = scopedChapterEntries
            if chapters.isEmpty {
                Picker("Chapter", selection: viewModel.chunkBinding()) {
                    let chunks = viewModel.jobContext?.chunks ?? []
                    ForEach(Array(chunks.enumerated()), id: \.element.id) { index, chunk in
                        Text("Chapter \(index + 1)").tag(chunk.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
            } else {
                Picker("Chapter", selection: chapterBinding(entries: chapters)) {
                    ForEach(Array(chapters.enumerated()), id: \.element.id) { index, chapter in
                        Text(chapterLabel(chapter, index: index)).tag(chapter.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    @ViewBuilder
    private func sentencePicker(for chunk: InteractiveChunk) -> some View {
        let chapterRange = selectedChapterRange
        let entries = sentenceEntries(for: chunk, chapterRange: chapterRange)
        VStack(alignment: .leading, spacing: 4) {
            Text("Sentence")
                .font(.caption)
                .foregroundStyle(.secondary)
            if entries.isEmpty {
                Text("No sentences")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                Picker("Sentence", selection: sentenceBinding(entries: entries, chunk: chunk, chapterRange: chapterRange)) {
                    ForEach(entries) { entry in
                        Text(entry.label).tag(entry.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    @ViewBuilder
    private func textTrackPicker(for chunk: InteractiveChunk) -> some View {
        let available = availableTracks(for: chunk)
        let showImageToggle = hasImageReel(for: chunk) && showImageReel != nil
        VStack(alignment: .leading, spacing: 4) {
            Text("Text")
                .font(.caption)
                .foregroundStyle(.secondary)
            Menu {
                ForEach(available, id: \.self) { kind in
                    trackToggle(label: trackLabel(kind), kind: kind)
                }
                if showImageToggle {
                    imageReelToggle()
                }
            } label: {
                menuLabel(textTrackSummary(for: chunk))
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    @ViewBuilder
    private func audioPicker(for chunk: InteractiveChunk) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Audio")
                .font(.caption)
                .foregroundStyle(.secondary)
            if !chunk.audioOptions.isEmpty {
                #if os(tvOS)
                Menu {
                    ForEach(chunk.audioOptions) { option in
                        Button(option.label) {
                            viewModel.selectAudioTrack(id: option.id)
                        }
                    }
                } label: {
                    menuLabel(selectedAudioLabel(for: chunk))
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused($focusedArea, equals: .controls)
                #else
                Picker("Audio track", selection: viewModel.audioTrackBinding(defaultID: chunk.audioOptions.first?.id)) {
                    ForEach(chunk.audioOptions) { option in
                        Text(option.label).tag(option.id)
                    }
                }
                .pickerStyle(.menu)
                .focused($focusedArea, equals: .controls)
                #endif
            } else {
                Text("No audio")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func selectedAudioLabel(for chunk: InteractiveChunk) -> String {
        guard let selectedID = viewModel.selectedAudioTrackID else {
            return chunk.audioOptions.first?.label ?? "Audio Mode"
        }
        return chunk.audioOptions.first(where: { $0.id == selectedID })?.label ?? "Audio Mode"
    }

    @ViewBuilder
    private func speedPicker() -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Speed")
                .font(.caption)
                .foregroundStyle(.secondary)
            Menu {
                ForEach(playbackRates, id: \.self) { rate in
                    Button {
                        audioCoordinator.setPlaybackRate(rate)
                    } label: {
                        if isCurrentRate(rate) {
                            Label(playbackRateLabel(rate), systemImage: "checkmark")
                        } else {
                            Text(playbackRateLabel(rate))
                        }
                    }
                }
            } label: {
                menuLabel(playbackRateLabel(audioCoordinator.playbackRate))
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    @ViewBuilder
    private func readingBedPicker() -> some View {
        if viewModel.readingBedURL != nil {
            let bedLabel = selectedReadingBedLabel
            VStack(alignment: .leading, spacing: 4) {
                Text("Music")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Menu {
                    Button(action: toggleReadingBed) {
                        if readingBedEnabled {
                            Label("Music On", systemImage: "checkmark")
                        } else {
                            Text("Music Off")
                        }
                    }
                    Divider()
                    Button {
                        viewModel.selectReadingBed(id: nil)
                    } label: {
                        if viewModel.selectedReadingBedID == nil {
                            Label("Default", systemImage: "checkmark")
                        } else {
                            Text("Default")
                        }
                    }
                    ForEach(viewModel.readingBedCatalog?.beds ?? []) { bed in
                        let label = bed.label.isEmpty ? bed.id : bed.label
                        Button {
                            viewModel.selectReadingBed(id: bed.id)
                        } label: {
                            if bed.id == viewModel.selectedReadingBedID {
                                Label(label, systemImage: "checkmark")
                            } else {
                                Text(label)
                            }
                        }
                    }
                } label: {
                    menuLabel(
                        readingBedSummary(label: bedLabel),
                        leadingSystemImage: readingBedEnabled ? "music.note.list" : "music.note"
                    )
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused($focusedArea, equals: .controls)
            }
        }
    }

    private func toggleReadingBed() {
        withAnimation(.none) {
            readingBedEnabled.toggle()
        }
    }

    private var selectedReadingBedLabel: String {
        if let selectedID = viewModel.selectedReadingBedID,
           let beds = viewModel.readingBedCatalog?.beds,
           let match = beds.first(where: { $0.id == selectedID }) {
            return match.label.isEmpty ? match.id : match.label
        }
        return "Default"
    }

    private func readingBedSummary(label: String) -> String {
        let state = readingBedEnabled ? "On" : "Off"
        if label.isEmpty {
            return state
        }
        return "\(state) / \(label)"
    }

    private func configureReadingBed() {
        readingBedCoordinator.setLooping(true)
        readingBedCoordinator.setVolume(readingBedVolume)
        updateReadingBedPlayback()
    }

    private func handleNarrationPlaybackChange(isPlaying: Bool) {
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

    private func updateReadingBedPlayback() {
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

    private func trackLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Transliteration"
        case .translation:
            return "Translation"
        }
    }

    private func trackSummaryLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Translit"
        case .translation:
            return "Translation"
        }
    }

    private func trackToggle(label: String, kind: TextPlayerVariantKind) -> some View {
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

    private func imageReelToggle() -> some View {
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

    private func toggleTrack(_ kind: TextPlayerVariantKind) {
        withAnimation(.none) {
            if visibleTracks.contains(kind) {
                if visibleTracks.count > 1 {
                    visibleTracks.remove(kind)
                }
            } else {
                visibleTracks.insert(kind)
            }
        }
    }

    private func toggleTrackIfAvailable(_ kind: TextPlayerVariantKind) {
        guard let chunk = viewModel.selectedChunk else { return }
        let available = availableTracks(for: chunk)
        guard available.contains(kind) else { return }
        toggleTrack(kind)
    }

    private func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk?) {
        guard let chunk else { return }
        handleWordNavigation(delta, in: chunk)
    }

    private func toggleAudioTrack(_ kind: InteractiveChunk.AudioOption.Kind) {
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

    private func availableTracks(for chunk: InteractiveChunk) -> [TextPlayerVariantKind] {
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

    private func hasImageReel(for chunk: InteractiveChunk) -> Bool {
        chunk.sentences.contains { sentence in
            if let rawPath = sentence.imagePath, rawPath.nonEmptyValue != nil {
                return true
            }
            return false
        }
    }

    private func applyDefaultTrackSelection(for chunk: InteractiveChunk) {
        let available = Set(availableTracks(for: chunk))
        if visibleTracks.isEmpty {
            visibleTracks = available
        } else {
            let intersection = visibleTracks.intersection(available)
            visibleTracks = intersection.isEmpty ? available : intersection
        }
        if let showImageReel {
            showImageReel.wrappedValue = hasImageReel(for: chunk)
        }
    }

    private func sentenceBinding(
        entries: [SentenceOption],
        chunk: InteractiveChunk,
        chapterRange: SentenceRange?
    ) -> Binding<Int> {
        Binding(
            get: {
                if let selected = selectedSentenceID,
                   entries.contains(where: { $0.id == selected }) {
                    return selected
                }
                return entries.first?.id ?? 0
            },
            set: { newValue in
                selectedSentenceID = newValue
                if chapterRange != nil {
                    viewModel.jumpToSentence(newValue, autoPlay: audioCoordinator.isPlaying)
                    return
                }
                guard let target = entries.first(where: { $0.id == newValue }) else { return }
                guard let startTime = target.startTime else { return }
                viewModel.seekPlayback(to: startTime, in: chunk)
            }
        )
    }

    private func sentenceEntries(for chunk: InteractiveChunk, chapterRange: SentenceRange?) -> [SentenceOption] {
        if let chapterRange {
            guard chapterRange.end >= chapterRange.start else { return [] }
            return (chapterRange.start...chapterRange.end).map { sentenceIndex in
                SentenceOption(id: sentenceIndex, label: "\(sentenceIndex)", startTime: nil)
            }
        }
        let sentences = chunk.sentences
        if sentences.isEmpty {
            if let start = chunk.startSentence, let end = chunk.endSentence, start <= end {
                return (start...end).map { SentenceOption(id: $0, label: "\($0)", startTime: nil) }
            }
            return []
        }
        var startTimes: [Int: Double] = [:]
        let activeTimingTrack = viewModel.activeTimingTrack(for: chunk)
        let useCombinedPhases = viewModel.useCombinedPhases(for: chunk)
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: viewModel.playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases
        )
        if let timelineSentences {
            for runtime in timelineSentences {
                guard sentences.indices.contains(runtime.index) else { continue }
                let sentence = sentences[runtime.index]
                let id = sentence.displayIndex ?? sentence.id
                startTimes[id] = runtime.startTime
            }
        }
        let entries = sentences.map { sentence -> SentenceOption in
            let id = sentence.displayIndex ?? sentence.id
            let label = "\(id)"
            return SentenceOption(
                id: id,
                label: label,
                startTime: startTimes[id] ?? sentence.startTime
            )
        }
        return entries.sorted { $0.id < $1.id }
    }

    private func syncSelectedSentence(for chunk: InteractiveChunk) {
        guard !isMenuVisible else { return }
        let time = viewModel.highlightingTime
        guard time.isFinite else { return }
        guard let sentence = viewModel.activeSentence(at: time) else { return }
        let id = sentence.displayIndex ?? sentence.id
        if selectedSentenceID != id {
            selectedSentenceID = id
        }
    }

    private func textTrackSummary(for chunk: InteractiveChunk) -> String {
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

    private func playbackRateLabel(_ rate: Double) -> String {
        let rounded = (rate * 100).rounded() / 100
        let formatted = String(format: rounded.truncatingRemainder(dividingBy: 1) == 0 ? "%.0f" : "%.2f", rounded)
        return "\(formatted)x"
    }

    private func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - audioCoordinator.playbackRate) < 0.01
    }

    private func transcriptSentences(for chunk: InteractiveChunk) -> [TextPlayerSentenceDisplay] {
        let playbackTime = viewModel.highlightingTime
        let activeTimingTrack = viewModel.activeTimingTrack(for: chunk)
        let useCombinedPhases = viewModel.useCombinedPhases(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        let timelineDuration = viewModel.timelineDuration(for: chunk)
        let durationValue: Double? = {
            if useCombinedPhases {
                return timelineDuration
            }
            if let timelineDuration {
                return timelineDuration
            }
            return playbackDuration > 0 ? playbackDuration : nil
        }()
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: durationValue,
            useCombinedPhases: useCombinedPhases
        )
        let isVariantVisible: (TextPlayerVariantKind) -> Bool = { visibleTracks.contains($0) }
        let timelineDisplay = timelineSentences.flatMap { runtime in
            TextPlayerTimeline.buildTimelineDisplay(
                timelineSentences: runtime,
                chunkTime: playbackTime,
                audioDuration: durationValue,
                isVariantVisible: isVariantVisible
            )
        }
        let staticDisplay = TextPlayerTimeline.buildStaticDisplay(
            sentences: chunk.sentences,
            isVariantVisible: isVariantVisible
        )
        return TextPlayerTimeline.selectActiveSentence(
            from: timelineDisplay?.sentences ?? staticDisplay
        )
    }

    private func activeSentenceDisplay(for chunk: InteractiveChunk) -> TextPlayerSentenceDisplay? {
        transcriptSentences(for: chunk).first
    }

    private func preferredNavigationKind(for chunk: InteractiveChunk) -> TextPlayerVariantKind {
        switch viewModel.activeTimingTrack(for: chunk) {
        case .original:
            return .original
        case .translation, .mix:
            return .translation
        }
    }

    private func preferredNavigationVariant(
        for sentence: TextPlayerSentenceDisplay,
        chunk: InteractiveChunk
    ) -> TextPlayerVariantDisplay? {
        let preferredKind = preferredNavigationKind(for: chunk)
        if let preferred = sentence.variants.first(where: { $0.kind == preferredKind }) {
            return preferred
        }
        if let translation = sentence.variants.first(where: { $0.kind == .translation }) {
            return translation
        }
        if let original = sentence.variants.first(where: { $0.kind == .original }) {
            return original
        }
        if let transliteration = sentence.variants.first(where: { $0.kind == .transliteration }) {
            return transliteration
        }
        return sentence.variants.first
    }

    private func resolvedSelection(for chunk: InteractiveChunk) -> TextPlayerWordSelection? {
        guard let sentence = activeSentenceDisplay(for: chunk) else { return nil }
        if let selection = linguistSelection,
           selection.sentenceIndex == sentence.index,
           let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }),
           variant.tokens.indices.contains(selection.tokenIndex) {
            return selection
        }
        guard let variant = preferredNavigationVariant(for: sentence, chunk: chunk),
              !variant.tokens.isEmpty else {
            return nil
        }
        let fallbackIndex = variant.currentIndex ?? 0
        let clampedIndex = max(0, min(fallbackIndex, variant.tokens.count - 1))
        return TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: variant.kind,
            tokenIndex: clampedIndex
        )
    }

    private func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk),
              let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }) else {
            return
        }
        let nextIndex = selection.tokenIndex + delta
        let resolvedIndex = variant.tokens.indices.contains(nextIndex) ? nextIndex : selection.tokenIndex
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: resolvedIndex
        )
        linguistBubble = nil
    }

    private func handleTrackNavigation(_ delta: Int, in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk) else { return }
        let variants = sentence.variants
        guard !variants.isEmpty else { return }
        let currentSelection = resolvedSelection(for: chunk)
        let currentIndex: Int = {
            if let currentSelection,
               let index = variants.firstIndex(where: { $0.kind == currentSelection.variantKind }) {
                return index
            }
            let preferredKind = preferredNavigationKind(for: chunk)
            if let preferredIndex = variants.firstIndex(where: { $0.kind == preferredKind }) {
                return preferredIndex
            }
            return 0
        }()
        let nextIndex = (currentIndex + delta + variants.count) % variants.count
        let targetVariant = variants[nextIndex]
        let fallbackIndex = targetVariant.currentIndex ?? 0
        let preferredTokenIndex = currentSelection?.tokenIndex ?? fallbackIndex
        let clampedIndex = max(0, min(preferredTokenIndex, max(0, targetVariant.tokens.count - 1)))
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: targetVariant.kind,
            tokenIndex: clampedIndex
        )
        linguistBubble = nil
    }

    private func handleLinguistLookup(
        sentenceIndex: Int,
        variantKind: TextPlayerVariantKind,
        tokenIndex: Int,
        token: String
    ) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let query = sanitizeLookupQuery(token) else { return }
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentenceIndex,
            variantKind: variantKind,
            tokenIndex: tokenIndex
        )
        startLinguistLookup(query: query, variantKind: variantKind)
    }

    private func handleLinguistLookup(in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk),
              let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }),
              variant.tokens.indices.contains(selection.tokenIndex) else {
            return
        }
        guard let lookupIndex = nearestLookupTokenIndex(
            in: variant.tokens,
            startingAt: selection.tokenIndex
        ) else {
            return
        }
        let rawToken = variant.tokens[lookupIndex]
        guard let query = sanitizeLookupQuery(rawToken) else { return }
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: lookupIndex
        )
        startLinguistLookup(query: query, variantKind: selection.variantKind)
    }

    private func handleTokenSeek(
        sentenceIndex: Int,
        sentenceNumber: Int?,
        variantKind: TextPlayerVariantKind,
        tokenIndex: Int,
        seekTime: Double?,
        in chunk: InteractiveChunk
    ) {
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentenceIndex,
            variantKind: variantKind,
            tokenIndex: tokenIndex
        )
        linguistBubble = nil
        if let seekTime, seekTime.isFinite {
            viewModel.seekPlayback(to: seekTime, in: chunk)
            return
        }
        if let sentenceNumber, sentenceNumber > 0 {
            viewModel.jumpToSentence(sentenceNumber, autoPlay: audioCoordinator.isPlaybackRequested)
        }
    }

    private func startLinguistLookup(query: String, variantKind: TextPlayerVariantKind) {
        linguistLookupTask?.cancel()
        linguistBubble = MyLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
        let originalLanguage = linguistInputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let translationLanguage = linguistLookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let explanationLanguage = linguistExplanationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let inputLanguage = lookupInputLanguage(
            for: variantKind,
            originalLanguage: originalLanguage,
            translationLanguage: translationLanguage
        )
        let pronunciationLanguage = pronunciationLanguage(
            for: variantKind,
            inputLanguage: originalLanguage,
            lookupLanguage: translationLanguage
        )
        let fallbackLanguage = resolveSpeechLanguage(pronunciationLanguage ?? "")
        startPronunciation(text: query, apiLanguage: pronunciationLanguage, fallbackLanguage: fallbackLanguage)
        linguistLookupTask = Task { @MainActor in
            do {
                let response = try await viewModel.lookupAssistant(
                    query: query,
                    inputLanguage: inputLanguage,
                    lookupLanguage: explanationLanguage.isEmpty ? "English" : explanationLanguage
                )
                linguistBubble = MyLinguistBubbleState(
                    query: query,
                    status: .ready,
                    answer: response.answer,
                    model: response.model
                )
            } catch {
                guard !Task.isCancelled else { return }
                linguistBubble = MyLinguistBubbleState(
                    query: query,
                    status: .error(error.localizedDescription),
                    answer: nil,
                    model: nil
                )
            }
        }
    }

    private func clearLinguistState() {
        linguistLookupTask?.cancel()
        linguistLookupTask = nil
        linguistSpeechTask?.cancel()
        linguistSpeechTask = nil
        linguistBubble = nil
        linguistSelection = nil
        pronunciationSpeaker.stop()
    }

    private func closeLinguistBubble() {
        linguistLookupTask?.cancel()
        linguistLookupTask = nil
        linguistSpeechTask?.cancel()
        linguistSpeechTask = nil
        linguistBubble = nil
        pronunciationSpeaker.stop()
    }

    private func adjustTrackFontScale(by delta: CGFloat) {
        setTrackFontScale(trackFontScale + delta)
    }

    private func adjustLinguistFontScale(by delta: CGFloat) {
        setLinguistFontScale(linguistFontScale + delta)
    }

    private func toggleShortcutHelp() {
        isShortcutHelpPinned.toggle()
    }

    private func showShortcutHelpModifier() {
        isShortcutHelpModifierActive = true
    }

    private func hideShortcutHelpModifier() {
        isShortcutHelpModifierActive = false
    }

    private func dismissShortcutHelp() {
        isShortcutHelpPinned = false
    }

    private func setTrackFontScale(_ value: CGFloat) {
        let updated = min(max(value, trackFontScaleMin), trackFontScaleMax)
        if updated != trackFontScale {
            trackFontScale = updated
        }
    }

    private func setLinguistFontScale(_ value: CGFloat) {
        let updated = min(max(value, linguistFontScaleMin), linguistFontScaleMax)
        if updated != linguistFontScale {
            linguistFontScale = updated
        }
    }

    private var trackFontScale: CGFloat {
        get { CGFloat(trackFontScaleValue) }
        nonmutating set { trackFontScaleValue = Double(newValue) }
    }

    private var linguistFontScale: CGFloat {
        get { CGFloat(linguistFontScaleValue) }
        nonmutating set { linguistFontScaleValue = Double(newValue) }
    }

    private func sanitizeLookupQuery(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let stripped = trimmed.trimmingCharacters(in: .punctuationCharacters.union(.symbols))
        let normalized = stripped.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.isEmpty ? nil : normalized
    }

    private func nearestLookupTokenIndex(in tokens: [String], startingAt index: Int) -> Int? {
        guard !tokens.isEmpty else { return nil }
        let clamped = max(0, min(index, tokens.count - 1))
        if sanitizeLookupQuery(tokens[clamped]) != nil {
            return clamped
        }
        if tokens.count == 1 {
            return nil
        }
        for offset in 1..<tokens.count {
            let forward = clamped + offset
            if forward < tokens.count, sanitizeLookupQuery(tokens[forward]) != nil {
                return forward
            }
            let backward = clamped - offset
            if backward >= 0, sanitizeLookupQuery(tokens[backward]) != nil {
                return backward
            }
        }
        return nil
    }

    private func pronunciationLanguage(
        for variantKind: TextPlayerVariantKind,
        inputLanguage: String,
        lookupLanguage: String
    ) -> String? {
        let preferred = lookupInputLanguage(
            for: variantKind,
            originalLanguage: inputLanguage,
            translationLanguage: lookupLanguage
        )
        let trimmed = preferred.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    private func lookupInputLanguage(
        for variantKind: TextPlayerVariantKind,
        originalLanguage: String,
        translationLanguage: String
    ) -> String {
        let resolvedOriginal = originalLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedTranslation = translationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        switch variantKind {
        case .translation:
            return resolvedTranslation.isEmpty ? resolvedOriginal : resolvedTranslation
        case .original, .transliteration:
            return resolvedOriginal.isEmpty ? resolvedTranslation : resolvedOriginal
        }
    }

    private func resolveSpeechLanguage(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: "_", with: "-")
        if normalized.contains("-") || normalized.count <= 3 {
            return normalized
        }
        switch normalized.lowercased() {
        case "english":
            return "en-US"
        case "japanese":
            return "ja-JP"
        case "spanish":
            return "es-ES"
        case "french":
            return "fr-FR"
        case "german":
            return "de-DE"
        case "italian":
            return "it-IT"
        case "portuguese":
            return "pt-PT"
        case "chinese":
            return "zh-CN"
        case "korean":
            return "ko-KR"
        case "russian":
            return "ru-RU"
        case "arabic":
            return "ar-SA"
        case "hindi":
            return "hi-IN"
        default:
            return nil
        }
    }

    private func startPronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?) {
        linguistSpeechTask?.cancel()
        pronunciationSpeaker.stop()
        linguistSpeechTask = Task { @MainActor in
            do {
                let data = try await viewModel.synthesizePronunciation(text: text, language: apiLanguage)
                guard !Task.isCancelled else { return }
                pronunciationSpeaker.playAudio(data)
            } catch {
                guard !Task.isCancelled else { return }
                if let fallbackLanguage {
                    pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)
                }
            }
        }
    }

}

private struct TextPlayerWordSelection: Equatable {
    let sentenceIndex: Int
    let variantKind: TextPlayerVariantKind
    let tokenIndex: Int
}

private enum MyLinguistBubbleStatus: Equatable {
    case loading
    case ready
    case error(String)
}

private struct MyLinguistBubbleState: Equatable {
    let query: String
    let status: MyLinguistBubbleStatus
    let answer: String?
    let model: String?
}

private struct MyLinguistBubbleView: View {
    let bubble: MyLinguistBubbleState
    let fontScale: CGFloat
    let canIncreaseFont: Bool
    let canDecreaseFont: Bool
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text("MyLinguist")
                    .font(.headline)
                Spacer(minLength: 8)
                if let model = bubble.model, !model.isEmpty {
                    Text("Model: \(model)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                fontSizeControls
                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .font(.caption.weight(.semibold))
                        .padding(6)
                        .background(.black.opacity(0.3), in: Circle())
                }
                .buttonStyle(.plain)
            }

            Text(bubble.query)
                .font(queryFont)
                .lineLimit(2)
                .minimumScaleFactor(0.8)
                #if os(iOS)
                .textSelection(.enabled)
                #endif

            bubbleContent
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(bubbleBackground)
        .overlay(
            RoundedRectangle(cornerRadius: bubbleCornerRadius)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: bubbleCornerRadius))
    }

    @ViewBuilder
    private var bubbleContent: some View {
        switch bubble.status {
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .progressViewStyle(.circular)
                Text("Looking up...")
                    .font(bodyFont)
                    .foregroundStyle(.secondary)
            }
        case let .error(message):
            Text(message)
                .font(bodyFont)
                .foregroundStyle(.red)
        case .ready:
            ScrollView {
                Text(bubble.answer ?? "")
                    .font(bodyFont)
                    .foregroundStyle(.primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    #if os(iOS)
                    .textSelection(.enabled)
                    #endif
            }
            .frame(maxHeight: bubbleMaxHeight)
        }
    }

    private var fontSizeControls: some View {
        HStack(spacing: 4) {
            Button(action: onDecreaseFont) {
                Text("A-")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!canDecreaseFont)
            Button(action: onIncreaseFont) {
                Text("A+")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!canIncreaseFont)
        }
    }

    private var queryFont: Font {
        scaledFont(textStyle: .title3, weight: .semibold)
    }

    private var bodyFont: Font {
        scaledFont(textStyle: .callout, weight: .regular)
    }

    private func scaledFont(textStyle: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * fontScale, weight: weight)
        #else
        return .system(size: 16 * fontScale, weight: weight)
        #endif
    }

    private var bubbleBackground: Color {
        Color.black.opacity(0.75)
    }

    private var bubbleCornerRadius: CGFloat {
        #if os(tvOS)
        return 18
        #else
        return 14
        #endif
    }

    private var bubbleMaxHeight: CGFloat {
        #if os(tvOS)
        return 220
        #else
        return 180
        #endif
    }
}

private struct InteractiveTranscriptView: View {
    let viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?
    let bubble: MyLinguistBubbleState?
    let isMenuVisible: Bool
    let trackFontScale: CGFloat
    let linguistFontScale: CGFloat
    let canIncreaseLinguistFont: Bool
    let canDecreaseLinguistFont: Bool
    @FocusState.Binding var focusedArea: InteractivePlayerFocusArea?
    let onSkipSentence: (Int) -> Void
    let onNavigateTrack: (Int) -> Void
    let onShowMenu: () -> Void
    let onHideMenu: () -> Void
    let onLookup: () -> Void
    let onLookupToken: (Int, TextPlayerVariantKind, Int, String) -> Void
    let onSeekToken: (Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void
    let onIncreaseLinguistFont: () -> Void
    let onDecreaseLinguistFont: () -> Void
    let onSetTrackFontScale: (CGFloat) -> Void
    let onSetLinguistFontScale: (CGFloat) -> Void
    let onCloseBubble: () -> Void
    let onTogglePlayback: () -> Void

    #if os(iOS)
    @State private var trackMagnifyStartScale: CGFloat?
    @State private var bubbleMagnifyStartScale: CGFloat?
    #endif

    var body: some View {
        transcriptContent
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .onChange(of: audioCoordinator.duration) { _, newValue in
                viewModel.recordAudioDuration(newValue, for: audioCoordinator.activeURL)
            }
            .onChange(of: audioCoordinator.activeURL) { _, _ in
                viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
            }
            .onAppear {
                viewModel.recordAudioDuration(audioCoordinator.duration, for: audioCoordinator.activeURL)
            }
    }

    @ViewBuilder
    private var transcriptContent: some View {
        #if os(tvOS)
        let stackSpacing: CGFloat = bubble == nil ? 12 : 10
        VStack(alignment: .leading, spacing: stackSpacing) {
            TextPlayerFrame(
                sentences: sentences,
                selection: selection,
                onTokenLookup: onLookupToken,
                onTokenSeek: onSeekToken,
                fontScale: trackFontScale
            )
                .frame(maxWidth: .infinity, alignment: .top)
                .contentShape(Rectangle())
                .focusable(!isMenuVisible)
                .focused($focusedArea, equals: .transcript)
                .onTapGesture {
                    onLookup()
                }
                .accessibilityAddTraits(.isButton)

            if let bubble {
                MyLinguistBubbleView(
                    bubble: bubble,
                    fontScale: linguistFontScale,
                    canIncreaseFont: canIncreaseLinguistFont,
                    canDecreaseFont: canDecreaseLinguistFont,
                    onIncreaseFont: onIncreaseLinguistFont,
                    onDecreaseFont: onDecreaseLinguistFont,
                    onClose: onCloseBubble
                )
            }
        }
        #else
        GeometryReader { proxy in
            let stackSpacing: CGFloat = bubble == nil ? 12 : (isPad ? 0 : 6)
            if isPhone {
                ZStack(alignment: .bottom) {
                    TextPlayerFrame(
                        sentences: sentences,
                        selection: selection,
                        onTokenLookup: onLookupToken,
                        onTokenSeek: onSeekToken,
                        fontScale: trackFontScale
                    )
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                        .contentShape(Rectangle())
                        .gesture(swipeGesture)
                        .simultaneousGesture(doubleTapGesture, including: .gesture)
                        .highPriorityGesture(trackMagnifyGesture, including: .all)

                    if let bubble {
                        MyLinguistBubbleView(
                            bubble: bubble,
                            fontScale: linguistFontScale,
                            canIncreaseFont: canIncreaseLinguistFont,
                            canDecreaseFont: canDecreaseLinguistFont,
                            onIncreaseFont: onIncreaseLinguistFont,
                            onDecreaseFont: onDecreaseLinguistFont,
                            onClose: onCloseBubble
                        )
                            .frame(maxWidth: .infinity, alignment: .top)
                            .padding(.horizontal)
                            .padding(.bottom, 6)
                            .simultaneousGesture(bubbleMagnifyGesture, including: .all)
                    }
                }
            } else {
                let availableHeight = proxy.size.height
                let textHeight = bubble == nil ? availableHeight : availableHeight * 0.7
                VStack(alignment: .leading, spacing: stackSpacing) {
                    TextPlayerFrame(
                        sentences: sentences,
                        selection: selection,
                        onTokenLookup: onLookupToken,
                        onTokenSeek: onSeekToken,
                        fontScale: trackFontScale
                    )
                        .frame(
                            maxWidth: .infinity,
                            minHeight: bubble == nil ? textHeight : 0,
                            maxHeight: textHeight,
                            alignment: .top
                        )
                        .contentShape(Rectangle())
                        .gesture(swipeGesture)
                        .simultaneousGesture(doubleTapGesture, including: .gesture)
                        .highPriorityGesture(trackMagnifyGesture, including: .all)

                    if let bubble {
                        MyLinguistBubbleView(
                            bubble: bubble,
                            fontScale: linguistFontScale,
                            canIncreaseFont: canIncreaseLinguistFont,
                            canDecreaseFont: canDecreaseLinguistFont,
                            onIncreaseFont: onIncreaseLinguistFont,
                            onDecreaseFont: onDecreaseLinguistFont,
                            onClose: onCloseBubble
                        )
                            .frame(maxWidth: .infinity, alignment: .top)
                            .simultaneousGesture(bubbleMagnifyGesture, including: .all)
                    }
                }
            }
        }
        #endif
    }

    #if !os(tvOS)
    private var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 24, coordinateSpace: .local)
            .onEnded { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                if abs(horizontal) > abs(vertical) {
                    if horizontal < 0 {
                        onSkipSentence(1)
                    } else if horizontal > 0 {
                        onSkipSentence(-1)
                    }
                } else {
                    if vertical > 0 {
                        onShowMenu()
                    } else if vertical < 0 {
                        if isMenuVisible {
                            onHideMenu()
                        } else {
                            onNavigateTrack(-1)
                        }
                    }
                }
            }
    }
    #endif

    #if !os(tvOS)
    private var doubleTapGesture: some Gesture {
        TapGesture(count: 2)
            .onEnded {
                onTogglePlayback()
            }
    }
    #endif

    #if os(iOS)
    private var trackMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                if trackMagnifyStartScale == nil {
                    trackMagnifyStartScale = trackFontScale
                }
                let startScale = trackMagnifyStartScale ?? trackFontScale
                onSetTrackFontScale(startScale * value)
            }
            .onEnded { _ in
                trackMagnifyStartScale = nil
            }
    }

    private var bubbleMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                if bubbleMagnifyStartScale == nil {
                    bubbleMagnifyStartScale = linguistFontScale
                }
                let startScale = bubbleMagnifyStartScale ?? linguistFontScale
                onSetLinguistFontScale(startScale * value)
            }
            .onEnded { _ in
                bubbleMagnifyStartScale = nil
            }
    }
    #endif

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }
}

private final class PronunciationSpeaker: NSObject, ObservableObject, AVAudioPlayerDelegate {
    private let synthesizer = AVSpeechSynthesizer()
    private var audioPlayer: AVAudioPlayer?

    func playAudio(_ data: Data) {
        stop()
        configureAudioSession()
        do {
            let player = try AVAudioPlayer(data: data)
            player.delegate = self
            player.prepareToPlay()
            player.play()
            audioPlayer = player
        } catch {
            audioPlayer = nil
        }
    }

    func speakFallback(_ text: String, language: String?) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        stop()
        configureAudioSession()
        let utterance = AVSpeechUtterance(string: trimmed)
        if let language, let voice = AVSpeechSynthesisVoice(language: language) {
            utterance.voice = voice
        }
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        synthesizer.speak(utterance)
    }

    func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        audioPlayer?.stop()
        audioPlayer = nil
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        audioPlayer = nil
    }

    private func configureAudioSession() {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        let options: AVAudioSession.CategoryOptions = [.allowAirPlay]
        try? session.setCategory(.playback, mode: .spokenAudio, options: options)
        try? session.setActive(true)
        #endif
    }
}

private struct PlaybackButtonRow: View {
    @ObservedObject var coordinator: AudioPlayerCoordinator
    let focusBinding: FocusState<InteractivePlayerFocusArea?>.Binding
    let onPrevious: (() -> Void)?
    let onNext: (() -> Void)?

    var body: some View {
        #if os(tvOS)
        HStack(spacing: 12) {
            if let onPrevious {
                Button(action: onPrevious) {
                    Image(systemName: "backward.end.fill")
                        .font(.title3)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused(focusBinding, equals: .controls)
            }
            Button(action: coordinator.togglePlayback) {
                Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
            .focused(focusBinding, equals: .controls)
            if let onNext {
                Button(action: onNext) {
                    Image(systemName: "forward.end.fill")
                        .font(.title3)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .focused(focusBinding, equals: .controls)
            }
        }
        #else
        HStack(spacing: 14) {
            if let onPrevious {
                Button(action: onPrevious) {
                    Image(systemName: "backward.end.fill")
                        .font(.title3)
                        .padding(8)
                        .background(.thinMaterial, in: Circle())
                }
            }
            Button(action: coordinator.togglePlayback) {
                Image(systemName: coordinator.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
                    .padding(10)
                    .background(.thinMaterial, in: Circle())
            }
            if let onNext {
                Button(action: onNext) {
                    Image(systemName: "forward.end.fill")
                        .font(.title3)
                        .padding(8)
                        .background(.thinMaterial, in: Circle())
                }
            }
        }
        #endif
    }
}

private struct InteractivePlayerImageReel: View {
    let urls: [URL]
    let height: CGFloat

    private let spacing: CGFloat = 8
    private let maxImages = 7
    private let minImages = 1

    var body: some View {
        GeometryReader { proxy in
            let itemHeight = height
            let itemWidth = itemHeight * 0.78
            let maxVisible = max(
                minImages,
                min(maxImages, Int((proxy.size.width + spacing) / (itemWidth + spacing)))
            )
            let visible = Array(urls.prefix(maxVisible))
            HStack(spacing: spacing) {
                ForEach(visible.indices, id: \.self) { index in
                    AsyncImage(url: visible[index]) { phase in
                        if let image = phase.image {
                            image
                                .resizable()
                                .scaledToFill()
                        } else {
                            Color.gray.opacity(0.2)
                        }
                    }
                    .frame(width: itemWidth, height: itemHeight)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                    )
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .trailing)
        }
        .frame(height: height)
    }
}

private struct SentenceOption: Identifiable {
    let id: Int
    let label: String
    let startTime: Double?
}

private struct SentenceRange: Equatable {
    let start: Int
    let end: Int
}

private struct PlaybackScrubberView: View {
    @ObservedObject var coordinator: AudioPlayerCoordinator
    let currentTime: Double
    let duration: Double
    @Binding var scrubbedTime: Double?
    let onSeek: ((Double) -> Void)?

    var body: some View {
        let upperBound = max(duration, scrubbedTime ?? currentTime, 0.1)
        VStack(alignment: .leading, spacing: 4) {
            #if os(tvOS)
            // tvOS does not support Slider. Show a progress bar instead.
            ProgressView(value: min(currentValue / max(upperBound, 0.0001), 1.0))
                .progressViewStyle(.linear)
                .tint(TextPlayerTheme.progress)
            #else
            Slider(
                value: Binding(
                    get: { scrubbedTime ?? currentTime },
                    set: { newValue in
                        scrubbedTime = newValue
                    }
                ),
                in: 0...upperBound,
                onEditingChanged: handleEditingChanged
            )
            .tint(TextPlayerTheme.progress)
            #endif
            Text("\(formatTime(currentValue)) / \(formatTime(duration))")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    private var currentValue: Double {
        scrubbedTime ?? currentTime
    }

    private func handleEditingChanged(_ editing: Bool) {
        if !editing {
            let target = currentValue
            scrubbedTime = nil
            if let onSeek {
                onSeek(target)
            } else {
                coordinator.seek(to: target)
            }
        }
    }

    private func formatTime(_ value: Double) -> String {
        guard value.isFinite else { return "--:--" }
        let totalSeconds = Int(value.rounded())
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
}

private struct TextPlayerFrame: View {
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?
    let onTokenLookup: ((Int, TextPlayerVariantKind, Int, String) -> Void)?
    let onTokenSeek: ((Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void)?
    let fontScale: CGFloat

    var body: some View {
        VStack(spacing: 10) {
            if sentences.isEmpty {
                Text("Waiting for transcript...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
            } else {
                ForEach(sentences) { sentence in
                    TextPlayerSentenceView(
                        sentence: sentence,
                        selection: selection,
                        onTokenLookup: onTokenLookup,
                        onTokenSeek: onTokenSeek,
                        fontScale: fontScale
                    )
                }
            }
        }
        .padding(framePadding)
        .frame(maxWidth: .infinity)
        .background(TextPlayerTheme.frameBackground)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var framePadding: CGFloat {
        #if os(tvOS)
        return 20
        #else
        return 14
        #endif
    }
}

private struct TextPlayerSentenceView: View {
    let sentence: TextPlayerSentenceDisplay
    let selection: TextPlayerWordSelection?
    let onTokenLookup: ((Int, TextPlayerVariantKind, Int, String) -> Void)?
    let onTokenSeek: ((Int, Int?, TextPlayerVariantKind, Int, Double?) -> Void)?
    let fontScale: CGFloat

    var body: some View {
        VStack(spacing: 8) {
            ForEach(sentence.variants) { variant in
                TextPlayerVariantView(
                    variant: variant,
                    sentenceState: sentence.state,
                    selectedTokenIndex: selectedTokenIndex(for: variant),
                    fontScale: fontScale,
                    onTokenLookup: { tokenIndex, token in
                        onTokenLookup?(sentence.index, variant.kind, tokenIndex, token)
                    },
                    onTokenSeek: { tokenIndex, seekTime in
                        onTokenSeek?(sentence.index, sentence.sentenceNumber, variant.kind, tokenIndex, seekTime)
                    }
                )
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .frame(maxWidth: .infinity)
        .background(sentenceBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: sentenceShadow, radius: sentenceShadowRadius, x: 0, y: 6)
        .opacity(sentenceOpacity)
    }

    private var sentenceBackground: Color {
        sentence.state == .active ? TextPlayerTheme.sentenceActiveBackground : TextPlayerTheme.sentenceBackground
    }

    private var sentenceShadow: Color {
        sentence.state == .active ? TextPlayerTheme.sentenceActiveShadow : .clear
    }

    private var sentenceShadowRadius: CGFloat {
        sentence.state == .active ? 18 : 0
    }

    private var sentenceOpacity: Double {
        switch sentence.state {
        case .past:
            return 0.9
        case .future:
            return 0.85
        case .active:
            return 1.0
        }
    }

    private func selectedTokenIndex(for variant: TextPlayerVariantDisplay) -> Int? {
        guard let selection, selection.sentenceIndex == sentence.index else { return nil }
        guard selection.variantKind == variant.kind else { return nil }
        return selection.tokenIndex
    }
}

private struct TokenFlowLayout: Layout {
    let itemSpacing: CGFloat
    let lineSpacing: CGFloat

    private struct Line {
        var indices: [Int] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .greatestFiniteMagnitude
        let lines = buildLines(maxWidth: maxWidth, subviews: subviews)
        let maxLineWidth = lines.map(\.width).max() ?? 0
        let totalHeight = lines.reduce(0) { $0 + $1.height }
            + lineSpacing * max(0, CGFloat(lines.count - 1))
        return CGSize(width: min(maxWidth, maxLineWidth), height: totalHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        guard bounds.width > 0 else { return }
        let lines = buildLines(maxWidth: bounds.width, subviews: subviews)
        var y = bounds.minY
        for line in lines {
            let lineWidth = line.width
            let xStart = bounds.minX + max(0, (bounds.width - lineWidth) / 2)
            var x = xStart
            for index in line.indices {
                let subview = subviews[index]
                let size = subview.sizeThatFits(.unspecified)
                let origin = CGPoint(x: x, y: y + (line.height - size.height) / 2)
                subview.place(at: origin, proposal: ProposedViewSize(width: size.width, height: size.height))
                x += size.width + itemSpacing
            }
            y += line.height + lineSpacing
        }
    }

    private func buildLines(maxWidth: CGFloat, subviews: Subviews) -> [Line] {
        guard !subviews.isEmpty else { return [] }
        let effectiveWidth = maxWidth > 0 ? maxWidth : .greatestFiniteMagnitude
        var lines: [Line] = []
        var current = Line()
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let itemWidth = size.width
            if current.indices.isEmpty {
                current.indices = [index]
                current.width = itemWidth
                current.height = size.height
                continue
            }
            if current.width + itemSpacing + itemWidth <= effectiveWidth {
                current.indices.append(index)
                current.width += itemSpacing + itemWidth
                current.height = max(current.height, size.height)
            } else {
                lines.append(current)
                current = Line(indices: [index], width: itemWidth, height: size.height)
            }
        }
        if !current.indices.isEmpty {
            lines.append(current)
        }
        return lines
    }
}

private struct TokenWordView: View {
    let text: String
    let color: Color
    let isSelected: Bool
    let horizontalPadding: CGFloat
    let verticalPadding: CGFloat
    let cornerRadius: CGFloat
    let onTap: (() -> Void)?
    let onLookup: (() -> Void)?

    var body: some View {
        Text(text)
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .allowsTightening(true)
            .padding(.horizontal, horizontalPadding)
            .padding(.vertical, verticalPadding)
            .foregroundStyle(isSelected ? TextPlayerTheme.selectionText : color)
            .background(
                Group {
                    if isSelected {
                        RoundedRectangle(cornerRadius: cornerRadius)
                            .fill(TextPlayerTheme.selectionGlow)
                    }
                }
            )
            #if !os(tvOS)
            .gesture(tokenTapGesture)
            #endif
            #if os(iOS)
            .contextMenu {
                Button("Look Up") {
                    DictionaryLookupPresenter.show(term: text)
                }
                Button("Copy") {
                    UIPasteboard.general.string = text
                }
            }
            #endif
    }

    #if !os(tvOS)
    private var tokenTapGesture: some Gesture {
        let doubleTap = TapGesture(count: 2)
            .onEnded { onLookup?() }
        let singleTap = TapGesture(count: 1)
            .onEnded { onTap?() }
        return doubleTap.exclusively(before: singleTap)
    }
    #endif
}

#if os(iOS)
private enum DictionaryLookupPresenter {
    static func show(term: String) {
        let trimmed = term.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let controller = UIReferenceLibraryViewController(term: trimmed)
        guard let presenter = topViewController() else { return }
        presenter.present(controller, animated: true)
    }

    private static func topViewController() -> UIViewController? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let windows = scenes.flatMap { $0.windows }
        let root = windows.first(where: { $0.isKeyWindow })?.rootViewController
        return topViewController(from: root)
    }

    private static func topViewController(from root: UIViewController?) -> UIViewController? {
        if let presented = root?.presentedViewController {
            return topViewController(from: presented)
        }
        if let navigation = root as? UINavigationController {
            return topViewController(from: navigation.visibleViewController)
        }
        if let tab = root as? UITabBarController {
            return topViewController(from: tab.selectedViewController)
        }
        return root
    }
}
#endif

private struct ShortcutHelpOverlayView: View {
    let onDismiss: () -> Void

    private let sections: [ShortcutHelpSection] = [
        ShortcutHelpSection(
            title: "Playback",
            items: [
                ShortcutHelpItem(keys: "Space", action: "Play or pause")
            ]
        ),
        ShortcutHelpSection(
            title: "Navigation",
            items: [
                ShortcutHelpItem(keys: "Left Arrow", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Right Arrow", action: "Next sentence"),
                ShortcutHelpItem(keys: "Ctrl + Left Arrow", action: "Previous word"),
                ShortcutHelpItem(keys: "Ctrl + Right Arrow", action: "Next word"),
                ShortcutHelpItem(keys: "Down Arrow", action: "Show menu"),
                ShortcutHelpItem(keys: "Up Arrow", action: "Hide menu")
            ]
        ),
        ShortcutHelpSection(
            title: "Touch",
            items: [
                ShortcutHelpItem(keys: "Tap word", action: "Jump to word"),
                ShortcutHelpItem(keys: "Double tap background", action: "Play or pause"),
                ShortcutHelpItem(keys: "Swipe left", action: "Next sentence"),
                ShortcutHelpItem(keys: "Swipe right", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Pinch text", action: "Resize tracks"),
                ShortcutHelpItem(keys: "Pinch bubble", action: "Resize MyLinguist")
            ]
        ),
        ShortcutHelpSection(
            title: "Text Tracks",
            items: [
                ShortcutHelpItem(keys: "O", action: "Toggle original line"),
                ShortcutHelpItem(keys: "I", action: "Toggle transliteration line"),
                ShortcutHelpItem(keys: "P", action: "Toggle translation line")
            ]
        ),
        ShortcutHelpSection(
            title: "Audio Tracks",
            items: [
                ShortcutHelpItem(keys: "Shift + O", action: "Toggle original audio"),
                ShortcutHelpItem(keys: "Shift + P", action: "Toggle translation audio")
            ]
        ),
        ShortcutHelpSection(
            title: "Font Size",
            items: [
                ShortcutHelpItem(keys: "+ / -", action: "Track font size"),
                ShortcutHelpItem(keys: "Ctrl + +/-", action: "MyLinguist font size")
            ]
        ),
        ShortcutHelpSection(
            title: "Help",
            items: [
                ShortcutHelpItem(keys: "H", action: "Toggle this overlay"),
                ShortcutHelpItem(keys: "Option (hold)", action: "Show shortcuts overlay")
            ]
        )
    ]

    var body: some View {
        ZStack {
            Color.black.opacity(0.55)
                .ignoresSafeArea()
                .onTapGesture {
                    onDismiss()
                }
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("Keyboard Shortcuts")
                        .font(.title3.weight(.semibold))
                    Spacer()
                    Button(action: onDismiss) {
                        Image(systemName: "xmark")
                            .font(.caption.weight(.semibold))
                            .padding(6)
                            .background(.black.opacity(0.3), in: Circle())
                    }
                    .buttonStyle(.plain)
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(sections) { section in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(section.title)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                ForEach(section.items) { item in
                                    HStack(alignment: .top, spacing: 12) {
                                        Text(item.keys)
                                            .font(.callout.monospaced())
                                            .frame(width: 170, alignment: .leading)
                                        Text(item.action)
                                            .font(.callout)
                                        Spacer(minLength: 0)
                                    }
                                }
                            }
                        }
                    }
                }
                .frame(maxHeight: 360)
            }
            .padding(20)
            .frame(maxWidth: 520)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 18))
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
        }
    }

    private struct ShortcutHelpSection: Identifiable {
        let id = UUID()
        let title: String
        let items: [ShortcutHelpItem]
    }

    private struct ShortcutHelpItem: Identifiable {
        let id = UUID()
        let keys: String
        let action: String
    }
}

#if os(iOS)
private struct TrackpadSwipeHandler: UIViewRepresentable {
    let onSwipeDown: () -> Void
    let onSwipeUp: () -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(onSwipeDown: onSwipeDown, onSwipeUp: onSwipeUp)
    }

    func makeUIView(context: Context) -> UIView {
        let view = TrackpadSwipeView()
        view.backgroundColor = .clear
        let pan = UIPanGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handlePan(_:)))
        pan.cancelsTouchesInView = false
        if #available(iOS 13.4, *) {
            pan.allowedScrollTypesMask = [.continuous, .discrete]
            pan.allowedTouchTypes = [NSNumber(value: UITouch.TouchType.indirectPointer.rawValue)]
        }
        view.addGestureRecognizer(pan)
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {}

    private final class TrackpadSwipeView: UIView {
        override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
            guard let event else { return nil }
            guard let touches = event.allTouches, !touches.isEmpty else { return nil }
            let hasPointer = touches.contains { touch in
                if #available(iOS 13.4, *) {
                    return touch.type == .indirectPointer || touch.type == .indirect
                }
                return false
            }
            return hasPointer ? self : nil
        }
    }

    final class Coordinator: NSObject {
        private let onSwipeDown: () -> Void
        private let onSwipeUp: () -> Void
        private let threshold: CGFloat = 24

        init(onSwipeDown: @escaping () -> Void, onSwipeUp: @escaping () -> Void) {
            self.onSwipeDown = onSwipeDown
            self.onSwipeUp = onSwipeUp
        }

        @objc func handlePan(_ gesture: UIPanGestureRecognizer) {
            guard gesture.state == .ended || gesture.state == .cancelled else { return }
            let translation = gesture.translation(in: gesture.view)
            let horizontal = translation.x
            let vertical = translation.y
            guard abs(vertical) > abs(horizontal) else { return }
            if vertical > threshold {
                onSwipeDown()
            } else if vertical < -threshold {
                onSwipeUp()
            }
        }
    }
}

private struct KeyboardCommandHandler: UIViewControllerRepresentable {
    let onPlayPause: () -> Void
    let onPrevious: () -> Void
    let onNext: () -> Void
    let onPreviousWord: () -> Void
    let onNextWord: () -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onToggleOriginal: () -> Void
    let onToggleTransliteration: () -> Void
    let onToggleTranslation: () -> Void
    let onToggleOriginalAudio: () -> Void
    let onToggleTranslationAudio: () -> Void
    let onIncreaseLinguistFont: () -> Void
    let onDecreaseLinguistFont: () -> Void
    let onToggleShortcutHelp: () -> Void
    let onOptionKeyDown: () -> Void
    let onOptionKeyUp: () -> Void
    let onShowMenu: () -> Void
    let onHideMenu: () -> Void

    func makeUIViewController(context: Context) -> KeyCommandController {
        let controller = KeyCommandController()
        controller.onPlayPause = onPlayPause
        controller.onPrevious = onPrevious
        controller.onNext = onNext
        controller.onPreviousWord = onPreviousWord
        controller.onNextWord = onNextWord
        controller.onIncreaseFont = onIncreaseFont
        controller.onDecreaseFont = onDecreaseFont
        controller.onToggleOriginal = onToggleOriginal
        controller.onToggleTransliteration = onToggleTransliteration
        controller.onToggleTranslation = onToggleTranslation
        controller.onToggleOriginalAudio = onToggleOriginalAudio
        controller.onToggleTranslationAudio = onToggleTranslationAudio
        controller.onIncreaseLinguistFont = onIncreaseLinguistFont
        controller.onDecreaseLinguistFont = onDecreaseLinguistFont
        controller.onToggleShortcutHelp = onToggleShortcutHelp
        controller.onOptionKeyDown = onOptionKeyDown
        controller.onOptionKeyUp = onOptionKeyUp
        controller.onShowMenu = onShowMenu
        controller.onHideMenu = onHideMenu
        return controller
    }

    func updateUIViewController(_ uiViewController: KeyCommandController, context: Context) {
        uiViewController.onPlayPause = onPlayPause
        uiViewController.onPrevious = onPrevious
        uiViewController.onNext = onNext
        uiViewController.onPreviousWord = onPreviousWord
        uiViewController.onNextWord = onNextWord
        uiViewController.onIncreaseFont = onIncreaseFont
        uiViewController.onDecreaseFont = onDecreaseFont
        uiViewController.onToggleOriginal = onToggleOriginal
        uiViewController.onToggleTransliteration = onToggleTransliteration
        uiViewController.onToggleTranslation = onToggleTranslation
        uiViewController.onToggleOriginalAudio = onToggleOriginalAudio
        uiViewController.onToggleTranslationAudio = onToggleTranslationAudio
        uiViewController.onIncreaseLinguistFont = onIncreaseLinguistFont
        uiViewController.onDecreaseLinguistFont = onDecreaseLinguistFont
        uiViewController.onToggleShortcutHelp = onToggleShortcutHelp
        uiViewController.onOptionKeyDown = onOptionKeyDown
        uiViewController.onOptionKeyUp = onOptionKeyUp
        uiViewController.onShowMenu = onShowMenu
        uiViewController.onHideMenu = onHideMenu
    }

    final class KeyCommandController: UIViewController {
        var onPlayPause: (() -> Void)?
        var onPrevious: (() -> Void)?
        var onNext: (() -> Void)?
        var onPreviousWord: (() -> Void)?
        var onNextWord: (() -> Void)?
        var onIncreaseFont: (() -> Void)?
        var onDecreaseFont: (() -> Void)?
        var onToggleOriginal: (() -> Void)?
        var onToggleTransliteration: (() -> Void)?
        var onToggleTranslation: (() -> Void)?
        var onToggleOriginalAudio: (() -> Void)?
        var onToggleTranslationAudio: (() -> Void)?
        var onIncreaseLinguistFont: (() -> Void)?
        var onDecreaseLinguistFont: (() -> Void)?
        var onToggleShortcutHelp: (() -> Void)?
        var onOptionKeyDown: (() -> Void)?
        var onOptionKeyUp: (() -> Void)?
        var onShowMenu: (() -> Void)?
        var onHideMenu: (() -> Void)?
        private var isOptionKeyDown = false

        override var canBecomeFirstResponder: Bool {
            true
        }

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            becomeFirstResponder()
        }

        override var keyCommands: [UIKeyCommand]? {
            let commands = [
                makeCommand(input: " ", action: #selector(handlePlayPause)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, action: #selector(handlePrevious)),
                makeCommand(input: UIKeyCommand.inputRightArrow, action: #selector(handleNext)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, modifiers: [.control], action: #selector(handlePreviousWord)),
                makeCommand(input: UIKeyCommand.inputRightArrow, modifiers: [.control], action: #selector(handleNextWord)),
                makeCommand(input: UIKeyCommand.inputDownArrow, action: #selector(handleShowMenu)),
                makeCommand(input: UIKeyCommand.inputUpArrow, action: #selector(handleHideMenu)),
                makeCommand(input: "h", action: #selector(handleToggleHelp)),
                makeCommand(input: "h", modifiers: [.shift], action: #selector(handleToggleHelp)),
                makeCommand(input: "o", action: #selector(handleToggleOriginal)),
                makeCommand(input: "o", modifiers: [.shift], action: #selector(handleToggleOriginalAudio)),
                makeCommand(input: "i", action: #selector(handleToggleTransliteration)),
                makeCommand(input: "i", modifiers: [.shift], action: #selector(handleToggleTransliteration)),
                makeCommand(input: "p", action: #selector(handleToggleTranslation)),
                makeCommand(input: "p", modifiers: [.shift], action: #selector(handleToggleTranslationAudio)),
                makeCommand(input: "=", modifiers: [.control], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "=", modifiers: [.control, .shift], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "+", modifiers: [.control], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "-", modifiers: [.control], action: #selector(handleDecreaseLinguistFont)),
                makeCommand(input: "=", modifiers: [], action: #selector(handleIncreaseFont)),
                makeCommand(input: "=", modifiers: [.shift], action: #selector(handleIncreaseFont)),
                makeCommand(input: "+", modifiers: [], action: #selector(handleIncreaseFont)),
                makeCommand(input: "-", modifiers: [], action: #selector(handleDecreaseFont)),
            ]
            return commands
        }

        @objc private func handlePlayPause() {
            onPlayPause?()
        }

        @objc private func handlePrevious() {
            onPrevious?()
        }

        @objc private func handleNext() {
            onNext?()
        }

        @objc private func handlePreviousWord() {
            onPreviousWord?()
        }

        @objc private func handleNextWord() {
            onNextWord?()
        }

        @objc private func handleIncreaseFont() {
            onIncreaseFont?()
        }

        @objc private func handleDecreaseFont() {
            onDecreaseFont?()
        }

        @objc private func handleToggleOriginal() {
            onToggleOriginal?()
        }

        @objc private func handleToggleTransliteration() {
            onToggleTransliteration?()
        }

        @objc private func handleToggleTranslation() {
            onToggleTranslation?()
        }

        @objc private func handleToggleOriginalAudio() {
            onToggleOriginalAudio?()
        }

        @objc private func handleToggleTranslationAudio() {
            onToggleTranslationAudio?()
        }

        @objc private func handleIncreaseLinguistFont() {
            onIncreaseLinguistFont?()
        }

        @objc private func handleDecreaseLinguistFont() {
            onDecreaseLinguistFont?()
        }

        @objc private func handleToggleHelp() {
            onToggleShortcutHelp?()
        }

        @objc private func handleShowMenu() {
            onShowMenu?()
        }

        @objc private func handleHideMenu() {
            onHideMenu?()
        }

        override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), !isOptionKeyDown {
                isOptionKeyDown = true
                onOptionKeyDown?()
            }
            super.pressesBegan(presses, with: event)
        }

        override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesEnded(presses, with: event)
        }

        override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesCancelled(presses, with: event)
        }

        private func makeCommand(
            input: String,
            modifiers: UIKeyModifierFlags = [],
            action: Selector
        ) -> UIKeyCommand {
            let command = UIKeyCommand(input: input, modifierFlags: modifiers, action: action)
            command.wantsPriorityOverSystemBehavior = true
            return command
        }

        private func shouldHandleOptionKey(_ presses: Set<UIPress>) -> Bool {
            for press in presses {
                guard let key = press.key else { continue }
                if key.keyCode == .keyboardLeftAlt || key.keyCode == .keyboardRightAlt {
                    return true
                }
                if key.characters.isEmpty,
                   key.charactersIgnoringModifiers.isEmpty,
                   key.modifierFlags.contains(.alternate) {
                    return true
                }
            }
            return false
        }
    }
}
#endif

private struct TextPlayerVariantView: View {
    let variant: TextPlayerVariantDisplay
    let sentenceState: TextPlayerSentenceState
    let selectedTokenIndex: Int?
    let fontScale: CGFloat
    let onTokenLookup: ((Int, String) -> Void)?
    let onTokenSeek: ((Int, Double?) -> Void)?

    var body: some View {
        VStack(spacing: 6) {
            Text(variant.label)
                .font(labelFont)
                .foregroundStyle(TextPlayerTheme.lineLabel)
                .textCase(.uppercase)
                .tracking(1.2)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .allowsTightening(true)
                .frame(maxWidth: .infinity)
            tokenFlow
                .font(lineFont)
                .frame(maxWidth: .infinity)
                .layoutPriority(1)
        }
    }

    private var labelFont: Font {
        #if os(tvOS)
        return .caption
        #else
        return .caption
        #endif
    }

    private var lineFont: Font {
        #if os(tvOS)
        return sentenceState == .active ? .title2 : .title3
        #elseif os(iOS)
        let isPad = UIDevice.current.userInterfaceIdiom == .pad
        let textStyle: UIFont.TextStyle = {
            if isPad {
                return sentenceState == .active ? .title1 : .title2
            }
            return sentenceState == .active ? .title2 : .title3
        }()
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * fontScale)
        #else
        return sentenceState == .active ? .title2 : .title3
        #endif
    }

    private var tokenFlow: some View {
        TokenFlowLayout(itemSpacing: tokenItemSpacing, lineSpacing: tokenLineSpacing) {
            ForEach(displayTokenIndices, id: \.self) { index in
                let token = variant.tokens[index]
                TokenWordView(
                    text: token,
                    color: tokenColor(for: tokenState(for: index)),
                    isSelected: index == selectedTokenIndex,
                    horizontalPadding: tokenHorizontalPadding,
                    verticalPadding: tokenVerticalPadding,
                    cornerRadius: tokenCornerRadius,
                    onTap: {
                        onTokenSeek?(index, tokenSeekTime(for: index))
                    },
                    onLookup: {
                        onTokenLookup?(index, token)
                    }
                )
            }
        }
    }

    private var displayTokenIndices: [Int] {
        shouldReverseTokens
            ? Array(variant.tokens.indices.reversed())
            : Array(variant.tokens.indices)
    }

    private var tokenItemSpacing: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 8
        #endif
    }

    private var tokenLineSpacing: CGFloat {
        #if os(tvOS)
        return 8
        #else
        return 6
        #endif
    }

    private var tokenHorizontalPadding: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 3
        #endif
    }

    private var tokenVerticalPadding: CGFloat {
        #if os(tvOS)
        return 2
        #else
        return 1
        #endif
    }

    private var tokenCornerRadius: CGFloat {
        #if os(tvOS)
        return 6
        #else
        return 4
        #endif
    }

    private func tokenSeekTime(for index: Int) -> Double? {
        guard let seekTimes = variant.seekTimes,
              seekTimes.indices.contains(index) else {
            return nil
        }
        let value = seekTimes[index]
        return value.isFinite ? value : nil
    }

    private var shouldReverseTokens: Bool {
        guard variant.kind == .translation else { return false }
        return variant.tokens.contains(where: containsRTLCharacters)
    }

    private func containsRTLCharacters(_ value: String) -> Bool {
        for scalar in value.unicodeScalars {
            let point = scalar.value
            if (0x0590...0x08FF).contains(point) || (0xFB1D...0xFEFF).contains(point) {
                return true
            }
        }
        return false
    }

    private func tokenState(for index: Int) -> TokenState {
        if sentenceState == .future {
            return .future
        }
        if sentenceState == .past {
            return .past
        }
        if variant.revealedCount == 0 {
            return .future
        }
        if index < variant.revealedCount - 1 {
            return .past
        }
        if index == variant.revealedCount - 1 {
            return .current
        }
        return .future
    }

    private func tokenColor(for state: TokenState) -> Color {
        switch state {
        case .past:
            return TextPlayerTheme.progress
        case .current:
            switch variant.kind {
            case .original:
                return TextPlayerTheme.originalCurrent
            case .translation:
                return TextPlayerTheme.translationCurrent
            case .transliteration:
                return TextPlayerTheme.transliterationCurrent
            }
        case .future:
            switch variant.kind {
            case .original:
                return TextPlayerTheme.original
            case .translation:
                return TextPlayerTheme.translation
            case .transliteration:
                return TextPlayerTheme.transliteration
            }
        }
    }

    private var highlightShadowColor: Color {
        switch variant.kind {
        case .original:
            return TextPlayerTheme.progress.opacity(0.7)
        case .translation:
            return TextPlayerTheme.translation.opacity(0.55)
        case .transliteration:
            return TextPlayerTheme.transliteration.opacity(0.55)
        }
    }

    private enum TokenState {
        case past
        case current
        case future
    }
}

private extension View {
    @ViewBuilder
    func applyIf<T: View>(_ condition: Bool, transform: (Self) -> T) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
}

private enum TextPlayerTheme {
    static let frameBackground = Color.black
    static let sentenceBackground = Color(red: 1.0, green: 0.878, blue: 0.521).opacity(0.04)
    static let sentenceActiveBackground = Color(red: 1.0, green: 0.647, blue: 0.0).opacity(0.16)
    static let sentenceActiveShadow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.18)
    static let lineLabel = Color.white.opacity(0.45)
    static let original = Color(red: 1.0, green: 0.831, blue: 0.0)
    static let translation = Color(red: 0.204, green: 0.827, blue: 0.6)
    static let transliteration = Color(red: 0.176, green: 0.831, blue: 0.749)
    static let progress = Color(red: 1.0, green: 0.549, blue: 0.0)
    static let selectionGlow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.6)
    static let selectionText = Color.black
    static let originalCurrent = Color.white
    static let translationCurrent = Color(red: 0.996, green: 0.941, blue: 0.541)
    static let transliterationCurrent = Color(red: 0.996, green: 0.976, blue: 0.765)
}

#if os(iOS) || os(tvOS)
private extension UIFont.TextStyle {
    static var title: UIFont.TextStyle {
        .title1
    }
}
#endif
