import SwiftUI

struct LibraryPlaybackHeader: View {
    let item: LibraryItem
    let coverURL: URL?
    let itemTypeLabel: String
    let showImageReel: Bool
    let imageReelURLs: [URL]
    let coverWidth: CGFloat
    let coverHeight: CGFloat
    let titleFont: Font
    let authorFont: Font
    let metaFont: Font
    let titleLineLimit: Int
    let headerSpacing: CGFloat
    let headerTextSpacing: CGFloat

    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif

    private var showsImageReel: Bool {
        showImageReel && !imageReelURLs.isEmpty
    }

    var body: some View {
        #if os(tvOS)
        regularLayout
        #else
        if horizontalSizeClass == .regular {
            regularLayout
        } else {
            compactLayout
        }
        #endif
    }

    private var regularLayout: some View {
        HStack(alignment: .top, spacing: headerSpacing) {
            LibraryPlaybackHeaderInfo(
                item: item,
                coverURL: coverURL,
                itemTypeLabel: itemTypeLabel,
                coverWidth: coverWidth,
                coverHeight: coverHeight,
                titleFont: titleFont,
                authorFont: authorFont,
                metaFont: metaFont,
                titleLineLimit: titleLineLimit,
                headerSpacing: headerSpacing,
                headerTextSpacing: headerTextSpacing
            )
            .frame(maxWidth: 520, alignment: .leading)
            if showsImageReel {
                Spacer(minLength: 12)
                LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            } else {
                Spacer()
            }
        }
    }

    private var compactLayout: some View {
        VStack(alignment: .leading, spacing: headerSpacing) {
            LibraryPlaybackHeaderInfo(
                item: item,
                coverURL: coverURL,
                itemTypeLabel: itemTypeLabel,
                coverWidth: coverWidth,
                coverHeight: coverHeight,
                titleFont: titleFont,
                authorFont: authorFont,
                metaFont: metaFont,
                titleLineLimit: titleLineLimit,
                headerSpacing: headerSpacing,
                headerTextSpacing: headerTextSpacing
            )
            .frame(maxWidth: .infinity, alignment: .leading)
            if showsImageReel {
                LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}

private struct LibraryPlaybackHeaderInfo: View {
    let item: LibraryItem
    let coverURL: URL?
    let itemTypeLabel: String
    let coverWidth: CGFloat
    let coverHeight: CGFloat
    let titleFont: Font
    let authorFont: Font
    let metaFont: Font
    let titleLineLimit: Int
    let headerSpacing: CGFloat
    let headerTextSpacing: CGFloat

    var body: some View {
        HStack(alignment: .center, spacing: headerSpacing) {
            LibraryPlaybackCoverView(
                coverURL: coverURL,
                title: titleText,
                itemTypeLabel: itemTypeLabel,
                width: coverWidth,
                height: coverHeight
            )

            VStack(alignment: .leading, spacing: headerTextSpacing) {
                Text(titleText)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(0.84)
                    .truncationMode(.tail)
                Text(authorText)
                    .font(authorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)
                    .foregroundStyle(.secondary)
                ViewThatFits(in: .horizontal) {
                    HStack(spacing: 6) {
                        LibraryPlaybackInfoPill(
                            label: itemTypeLabel,
                            systemImage: systemImage(for: itemTypeLabel),
                            font: metaFont
                        )
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        LibraryPlaybackInfoPill(
                            label: itemTypeLabel,
                            systemImage: systemImage(for: itemTypeLabel),
                            font: metaFont
                        )
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(LibraryPlaybackIdentityBannerBackground())
    }

    private var titleText: String {
        item.bookTitle.isEmpty ? "Untitled" : item.bookTitle
    }

    private var authorText: String {
        item.author.isEmpty ? "Unknown author" : item.author
    }

    private func systemImage(for label: String) -> String {
        let normalized = label.lowercased()
        if normalized.contains("video") || normalized.contains("youtube") {
            return "play.rectangle"
        }
        if normalized.contains("subtitle") || normalized.contains("caption") {
            return "captions.bubble"
        }
        return "book.closed"
    }
}

private struct LibraryPlaybackCoverView: View {
    let coverURL: URL?
    let title: String
    let itemTypeLabel: String
    let width: CGFloat
    let height: CGFloat

    var body: some View {
        Group {
            if let coverURL {
                AsyncImage(url: coverURL) { phase in
                    if let image = phase.image {
                        image.resizable().scaledToFill()
                    } else {
                        placeholder
                    }
                }
            } else {
                placeholder
            }
        }
        .frame(width: width, height: height)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(Color.white.opacity(0.20), lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.22), radius: 10, x: 0, y: 6)
        .accessibilityHidden(true)
    }

    private var placeholder: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.accentColor.opacity(0.35),
                            Color.secondary.opacity(0.16)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            VStack(spacing: 4) {
                Image(systemName: systemImage)
                    .font(.system(size: max(18, height * 0.22), weight: .semibold))
                Text(String(title.prefix(1)).uppercased())
                    .font(.system(size: max(16, height * 0.20), weight: .bold))
            }
            .foregroundStyle(.white.opacity(0.78))
        }
    }

    private var systemImage: String {
        let normalized = itemTypeLabel.lowercased()
        if normalized.contains("video") || normalized.contains("youtube") {
            return "play.rectangle"
        }
        if normalized.contains("subtitle") || normalized.contains("caption") {
            return "captions.bubble"
        }
        return "book.closed"
    }
}

private struct LibraryPlaybackInfoPill: View {
    let label: String
    let systemImage: String
    let font: Font

    var body: some View {
        Label(label, systemImage: systemImage)
            .labelStyle(.titleAndIcon)
            .font(font.weight(.semibold))
            .lineLimit(1)
            .minimumScaleFactor(0.78)
            .foregroundStyle(Color.primary.opacity(0.82))
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .background(
                Capsule(style: .continuous)
                    .fill(.thinMaterial)
                    .overlay(
                        Capsule(style: .continuous)
                            .fill(Color.accentColor.opacity(0.12))
                    )
                    .overlay(
                        Capsule(style: .continuous)
                            .strokeBorder(Color.accentColor.opacity(0.20), lineWidth: 1)
                    )
            )
    }
}

private struct LibraryPlaybackIdentityBannerBackground: View {
    var body: some View {
        RoundedRectangle(cornerRadius: 16, style: .continuous)
            .fill(.regularMaterial)
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color.white.opacity(0.18),
                                Color.accentColor.opacity(0.08),
                                Color.black.opacity(0.04)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .strokeBorder(Color.primary.opacity(0.08), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.08), radius: 12, x: 0, y: 6)
    }
}

struct LibraryPlaybackLoadingView: View {
    let usesDarkBackground: Bool

    var body: some View {
        VStack(spacing: 12) {
            ProgressView()
                .tint(usesDarkBackground ? .white : nil)
            Text("Loading media...")
                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }
}

struct LibraryPlaybackErrorView: View {
    let message: String
    let usesDarkBackground: Bool

    var body: some View {
        ContentUnavailableView {
            Label("Unable to load media", systemImage: "exclamationmark.triangle.fill")
        } description: {
            Text(message)
        }
        .foregroundStyle(usesDarkBackground ? .white : .primary)
    }
}

struct LibraryPlaybackUnavailableView: View {
    let usesDarkBackground: Bool

    var body: some View {
        ContentUnavailableView {
            Label("No playable media", systemImage: "play.slash")
        } description: {
            Text("This entry does not include a playable reader, audio, or video asset.")
        }
        .foregroundStyle(usesDarkBackground ? .white : .primary)
    }
}

private struct LibraryImageReel: View {
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

#if DEBUG
struct MusicBedSyncE2EControls: View {
    @ObservedObject var musicOwnership: MusicKitCoordinator
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let readerTransportCommandCount: Int
    let foregroundPlayPauseCount: Int
    let interactiveAutoplayPendingSentence: Int?
    let interactiveAutoplaySettledCount: Int
    let lastReaderTransportAction: String
    let lastReaderTransportSource: String
    let hasReaderContext: Bool
    let isVideoPreferred: Bool
    let isNarrationAudibleForReaderTransport: Bool
    let isReaderSequenceTransitioning: Bool
    let onReaderPlayCommand: () -> Void
    let onReaderPauseCommand: () -> Void
    let onReaderToggleCommand: () -> Void

    var body: some View {
        if ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" {
            HStack(spacing: 10) {
                Button("E2E Music Pause") {
                    musicOwnership.simulateObservedNonPlayingPauseForE2E()
                }
                .accessibilityIdentifier("e2eMusicBedPauseButton")
                .accessibilityLabel("e2eMusicBedPauseButton")

                Button("E2E Music Play") {
                    musicOwnership.simulateReadingBedPlayForE2E()
                }
                .accessibilityIdentifier("e2eMusicBedPlayButton")
                .accessibilityLabel("e2eMusicBedPlayButton")

                Button("E2E Observed Pause") {
                    musicOwnership.simulateObservedNonPlayingPauseForE2E()
                }
                .accessibilityIdentifier("e2eObservedMusicPauseButton")
                .accessibilityLabel("e2eObservedMusicPauseButton")

                Button("E2E Reader Play") {
                    onReaderPlayCommand()
                }
                .accessibilityIdentifier("e2eReaderPlayCommandButton")
                .accessibilityLabel("e2eReaderPlayCommandButton")

                Button("E2E Reader Pause") {
                    onReaderPauseCommand()
                }
                .accessibilityIdentifier("e2eReaderPauseCommandButton")
                .accessibilityLabel("e2eReaderPauseCommandButton")

                Button("E2E Reader Toggle") {
                    onReaderToggleCommand()
                }
                .accessibilityIdentifier("e2eReaderToggleCommandButton")
                .accessibilityLabel("e2eReaderToggleCommandButton")

                Button("E2E Keyboard Space") {
                    NotificationCenter.default.post(name: .keyboardShortcutPlayPause, object: nil)
                }
                .accessibilityIdentifier("e2eKeyboardSpaceCommandButton")
                .accessibilityLabel("e2eKeyboardSpaceCommandButton")

                Button("E2E Keyboard Left") {
                    NotificationCenter.default.post(name: .keyboardShortcutPrevious, object: nil)
                }
                .accessibilityIdentifier("e2eKeyboardLeftCommandButton")
                .accessibilityLabel("e2eKeyboardLeftCommandButton")

                Button("E2E Keyboard Right") {
                    NotificationCenter.default.post(name: .keyboardShortcutNext, object: nil)
                }
                .accessibilityIdentifier("e2eKeyboardRightCommandButton")
                .accessibilityLabel("e2eKeyboardRightCommandButton")

                Button("E2E Keyboard Lookup") {
                    NotificationCenter.default.post(name: .keyboardShortcutLookup, object: nil)
                }
                .accessibilityIdentifier("e2eKeyboardLookupCommandButton")
                .accessibilityLabel("e2eKeyboardLookupCommandButton")

                Button("E2E Auto Resume") {
                    musicOwnership.simulateAlreadyPlayingAutoResumeForE2E()
                }
                .accessibilityIdentifier("e2eMusicBedAutoResumeButton")
                .accessibilityLabel("e2eMusicBedAutoResumeButton")

                Button("E2E Reader Transition") {
                    musicOwnership.simulateSentenceTransitionForE2E()
                    audioCoordinator.simulateRequestedTransitionPauseForMusicBedE2E()
                }
                .accessibilityIdentifier("e2eReaderTransitionButton")
                .accessibilityLabel("e2eReaderTransitionButton")

                Button("E2E Reader Transition Resume") {
                    audioCoordinator.simulateRequestedTransitionResumeForMusicBedE2E()
                    musicOwnership.simulateSentenceTransitionForE2E(phase: "sentenceTransitionResume")
                }
                .accessibilityIdentifier("e2eReaderTransitionResumeButton")
                .accessibilityLabel("e2eReaderTransitionResumeButton")

                #if os(iOS)
                Button("E2E Bubble Resume") {
                    NotificationCenter.default.post(name: .e2eBubblePronunciationResume, object: nil)
                }
                .accessibilityIdentifier("e2eBubblePronunciationResumeButton")
                .accessibilityLabel("e2eBubblePronunciationResumeButton")
                #endif

                Text(statusText)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 6)
                    .background(.black.opacity(0.72), in: RoundedRectangle(cornerRadius: 6))
                    .accessibilityIdentifier("e2eMusicBedSyncStatus")
                    .accessibilityLabel(statusText)
                    .accessibilityValue(statusText)
            }
            .font(.caption)
            .buttonStyle(.borderedProminent)
            .padding(10)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 8))
            .padding()
            .task {
                await runAutoSequenceIfNeeded()
            }
            #if os(tvOS)
            .onChange(of: musicOwnership.e2eMusicBedSyncPhase) { _, phase in
                scheduleTVOSSetupResumeIfNeeded(phase: phase)
            }
            #endif
        }
    }

    #if os(tvOS)
    @MainActor
    private func scheduleTVOSSetupResumeIfNeeded(phase: String) {
        guard phase == "observedPauseImmediate" else { return }
        guard readerTransportCommandCount == 0 else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 8.0) {
            guard musicOwnership.e2eMusicBedSyncPhase == "observedPauseImmediate" else { return }
            guard readerTransportCommandCount == 0 else { return }
            musicOwnership.simulateReadingBedPlayForE2E()
        }
    }
    #endif

    @MainActor
    private func runAutoSequenceIfNeeded() async {
        guard !MusicBedSyncE2EState.didRunAutoSequence else { return }
        MusicBedSyncE2EState.didRunAutoSequence = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 8.0) {
            #if os(tvOS)
            musicOwnership.simulateObservedNonPlayingPauseForE2E()
            #else
            musicOwnership.simulateReadingBedPauseForE2E()
            #endif
        }
        #if os(tvOS)
        DispatchQueue.main.asyncAfter(deadline: .now() + 20.0) {
            musicOwnership.simulateReadingBedPlayForE2E()
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 70.0) {
            musicOwnership.simulateObservedNonPlayingPauseForE2E()
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 100.0) {
            musicOwnership.simulateReadingBedPlayForE2E()
        }
        #endif
        DispatchQueue.main.asyncAfter(deadline: .now() + 45.0) {
            guard !musicOwnership.isPausedByReaderTransport,
                  !musicOwnership.isReaderTransportPauseGuardActive
            else { return }
            musicOwnership.simulateReadingBedPlayForE2E()
        }
    }

    private var statusText: String {
        musicOwnership.ensureReadingBedPlayStateForE2E()
        var fields = [
            "reader=\(audioCoordinator.isPlaying ? "playing" : "paused")",
            "requested=\(audioCoordinator.isPlaybackRequested ? "true" : "false")",
            "audible=\(isNarrationAudibleForReaderTransport ? "true" : "false")",
            "transitioning=\(isReaderSequenceTransitioning ? "true" : "false")",
            "volume=\(audioCoordinator.volume > 0.001 ? "on" : "muted")",
            "music=\(musicOwnership.isPlaying ? "playing" : "paused")",
            "player=\(audioCoordinator.nowPlayingPlayer == nil ? "missing" : "ready")",
            "context=\(hasReaderContext ? "ready" : "missing")",
            "video=\(isVideoPreferred ? "true" : "false")",
            "readerTransportCommands=\(readerTransportCommandCount)",
            "foregroundPlayPause=\(foregroundPlayPauseCount)",
            "autoplayPending=\(interactiveAutoplayPendingSentence.map(String.init) ?? "none")",
            "autoplaySettled=\(interactiveAutoplaySettledCount)",
            "lastAction=\(lastReaderTransportAction)",
            "lastSource=\(lastReaderTransportSource)",
            "readerPause=\(musicOwnership.isPausedByReaderTransport ? "true" : "false")",
            "manual=\(musicOwnership.isManuallyPaused ? "true" : "false")",
            "guard=\(musicOwnership.isReaderTransportPauseGuardActive ? "true" : "false")",
            "owner=\(musicOwnership.ownershipState)",
            "surface=\(musicOwnership.isReaderPlaybackSurfaceActive ? "reader" : "music")",
            "fullscreen=\(musicOwnership.isFullscreenMusicArtworkSuppressed ? "blocked" : "available")",
            "sessionStable=\(audioCoordinator.isAudioSessionStableForMusicBed ? "true" : "false")",
            "sessionLabel=\(audioCoordinator.audioSessionLastLabel)",
            "sessionApply=\(audioCoordinator.audioSessionApplyCount)",
            "sessionSkip=\(audioCoordinator.audioSessionSkipCount)",
            "autoResumeAlreadyPlaying=\(musicOwnership.e2eMusicBedAlreadyPlayingResumeSkipCount)",
            "transitionPauses=\(audioCoordinator.e2eRequestedTransitionPauseCount)",
            "stickySequenceResumes=\(audioCoordinator.e2eStickySequenceResumeCount)",
            "phase=\(musicOwnership.e2eMusicBedSyncPhase)"
        ]
        #if os(iOS)
        fields.append(InteractivePlayerE2EState.statusText)
        #endif
        return fields.joined(separator: " ")
    }
}

@MainActor
private enum MusicBedSyncE2EState {
    static var didRunAutoSequence = false
}
#endif
