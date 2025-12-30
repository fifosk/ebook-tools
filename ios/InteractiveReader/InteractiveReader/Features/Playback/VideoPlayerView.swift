import AVKit
import SwiftUI
import Foundation
#if os(tvOS)
import UIKit
#endif

#if canImport(MediaPlayer)
import MediaPlayer
#endif

struct VideoPlaybackMetadata {
    let title: String
    let subtitle: String?
    let artist: String?
    let album: String?
    let artworkURL: URL?
}

struct VideoPlayerView: View {
    let videoURL: URL
    let subtitleTracks: [VideoSubtitleTrack]
    let metadata: VideoPlaybackMetadata
    let autoPlay: Bool
    let nowPlaying: NowPlayingCoordinator

    @StateObject private var coordinator = VideoPlayerCoordinator()
    @State private var cues: [VideoSubtitleCue] = []
    @State private var subtitleError: String?
    @State private var selectedTrack: VideoSubtitleTrack?
    @State private var subtitleCache: [URL: [VideoSubtitleCue]] = [:]
    @State private var subtitleTask: Task<Void, Never>?
    @State private var subtitleVisibility = SubtitleVisibility()
    @State private var showSubtitleSettings = false
    @State private var showTVControls = true
    @State private var scrubberValue: Double = 0
    @State private var isScrubbing = false
    @State private var controlsHideTask: Task<Void, Never>?

    var body: some View {
        ZStack {
            if let player = coordinator.playerInstance() {
                VideoPlayerControllerView(
                    player: player,
                    onShowControls: handleUserInteraction
                )
                VideoPlayerOverlayView(
                    cues: cues,
                    currentTime: coordinator.currentTime,
                    duration: coordinator.duration,
                    subtitleError: subtitleError,
                    tracks: orderedTracks,
                    selectedTrack: $selectedTrack,
                    subtitleVisibility: $subtitleVisibility,
                    showSubtitleSettings: $showSubtitleSettings,
                    showTVControls: $showTVControls,
                    scrubberValue: $scrubberValue,
                    isScrubbing: $isScrubbing,
                    metadata: metadata,
                    isPlaying: coordinator.isPlaying,
                    onPlayPause: {
                        handleUserInteraction()
                        coordinator.togglePlayback()
                    },
                    onSkipForward: {
                        handleUserInteraction()
                        coordinator.skip(by: 15)
                    },
                    onSkipBackward: {
                        handleUserInteraction()
                        coordinator.skip(by: -15)
                    },
                    onSeek: { time in
                        handleUserInteraction()
                        coordinator.seek(to: time)
                    },
                    onUserInteraction: handleUserInteraction
                )
            } else {
                ProgressView("Preparing video…")
            }
        }
        .onAppear {
            coordinator.load(url: videoURL, autoPlay: autoPlay)
            configureNowPlaying()
            updateNowPlayingMetadata()
            updateNowPlayingPlayback()
            selectDefaultTrackIfNeeded()
            scrubberValue = 0
            isScrubbing = false
            showTVControls = true
            scheduleControlsAutoHide()
        }
        .onChange(of: videoURL) { _, newURL in
            coordinator.load(url: newURL, autoPlay: autoPlay)
            updateNowPlayingMetadata()
            updateNowPlayingPlayback()
            selectDefaultTrackIfNeeded()
            scrubberValue = 0
            isScrubbing = false
            showTVControls = true
            scheduleControlsAutoHide()
        }
        .onChange(of: subtitleTracks) { _, _ in
            selectDefaultTrackIfNeeded()
        }
        .onChange(of: selectedTrack?.id) { _, _ in
            loadSubtitles()
        }
        .onChange(of: showSubtitleSettings) { _, isVisible in
            #if os(tvOS)
            if isVisible {
                showTVControls = true
                controlsHideTask?.cancel()
            } else {
                scheduleControlsAutoHide()
            }
            #endif
        }
        .onChange(of: isScrubbing) { _, scrubbing in
            #if os(tvOS)
            if scrubbing {
                showTVControls = true
                controlsHideTask?.cancel()
            } else {
                scheduleControlsAutoHide()
            }
            #endif
        }
        .onReceive(coordinator.$currentTime) { _ in
            updateNowPlayingPlayback()
            if !isScrubbing {
                scrubberValue = coordinator.currentTime
            }
        }
        .onReceive(coordinator.$isPlaying) { isPlaying in
            updateNowPlayingPlayback()
            #if os(tvOS)
            if isPlaying {
                scheduleControlsAutoHide()
            } else {
                controlsHideTask?.cancel()
                showTVControls = true
            }
            #endif
        }
        .onReceive(coordinator.$duration) { _ in
            updateNowPlayingPlayback()
            if coordinator.duration.isFinite, coordinator.duration > 0 {
                scrubberValue = min(scrubberValue, coordinator.duration)
            } else {
                scrubberValue = 0
            }
        }
        .onDisappear {
            subtitleTask?.cancel()
            subtitleTask = nil
            showSubtitleSettings = false
            controlsHideTask?.cancel()
            controlsHideTask = nil
            coordinator.reset()
            nowPlaying.clear()
        }
    }

    private var orderedTracks: [VideoSubtitleTrack] {
        subtitleTracks.sorted { lhs, rhs in
            if lhs.format.priority == rhs.format.priority {
                return lhs.label.localizedCaseInsensitiveCompare(rhs.label) == .orderedAscending
            }
            return lhs.format.priority < rhs.format.priority
        }
    }

    private func selectDefaultTrackIfNeeded() {
        guard let current = selectedTrack else {
            selectedTrack = orderedTracks.first
            return
        }
        if !orderedTracks.contains(where: { $0.id == current.id }) {
            selectedTrack = orderedTracks.first
        }
    }

    private func loadSubtitles() {
        subtitleTask?.cancel()
        subtitleError = nil
        guard let track = selectedTrack else {
            cues = []
            return
        }
        if let cached = subtitleCache[track.url] {
            cues = cached
            return
        }
        cues = []
        subtitleTask = Task {
            do {
                let (data, _) = try await URLSession.shared.data(from: track.url)
                let content = String(data: data, encoding: .utf8) ?? ""
                let parsed = SubtitleParser.parse(from: content, format: track.format)
                await MainActor.run {
                    subtitleCache[track.url] = parsed
                    cues = parsed
                }
            } catch {
                await MainActor.run {
                    subtitleError = "Unable to load subtitles"
                }
            }
        }
    }

    private func configureNowPlaying() {
        nowPlaying.configureRemoteCommands(
            onPlay: { coordinator.play() },
            onPause: { coordinator.pause() },
            onNext: nil,
            onPrevious: nil,
            onSeek: { coordinator.seek(to: $0) },
            onToggle: { coordinator.togglePlayback() },
            onSkipForward: { coordinator.skip(by: 15) },
            onSkipBackward: { coordinator.skip(by: -15) },
            skipIntervalSeconds: 15
        )
    }

    private func updateNowPlayingMetadata() {
        nowPlaying.updateMetadata(
            title: metadata.title,
            artist: metadata.artist,
            album: metadata.album,
            artworkURL: metadata.artworkURL,
            mediaType: .video
        )
    }

    private func updateNowPlayingPlayback() {
        nowPlaying.updatePlaybackState(
            isPlaying: coordinator.isPlaying,
            position: coordinator.currentTime,
            duration: coordinator.duration
        )
    }

    private func handleUserInteraction() {
        #if os(tvOS)
        showTVControls = true
        scheduleControlsAutoHide()
        #endif
    }

    private func scheduleControlsAutoHide() {
        #if os(tvOS)
        controlsHideTask?.cancel()
        guard shouldAutoHideControls else { return }
        controlsHideTask = Task {
            try? await Task.sleep(nanoseconds: 8_000_000_000)
            await MainActor.run {
                if shouldAutoHideControls {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        showTVControls = false
                    }
                }
            }
        }
        #endif
    }

    private var shouldAutoHideControls: Bool {
        guard let player = coordinator.playerInstance() else { return false }
        let isActive = player.timeControlStatus == .playing || player.rate > 0
        return isActive && !showSubtitleSettings && !isScrubbing
    }
}

private struct VideoPlayerOverlayView: View {
    let cues: [VideoSubtitleCue]
    let currentTime: Double
    let duration: Double
    let subtitleError: String?
    let tracks: [VideoSubtitleTrack]
    @Binding var selectedTrack: VideoSubtitleTrack?
    @Binding var subtitleVisibility: SubtitleVisibility
    @Binding var showSubtitleSettings: Bool
    @Binding var showTVControls: Bool
    @Binding var scrubberValue: Double
    @Binding var isScrubbing: Bool
    let metadata: VideoPlaybackMetadata
    let isPlaying: Bool
    let onPlayPause: () -> Void
    let onSkipForward: () -> Void
    let onSkipBackward: () -> Void
    let onSeek: (Double) -> Void
    let onUserInteraction: () -> Void
    #if !os(tvOS)
    @Environment(\.dismiss) private var dismiss
    #endif
    #if os(tvOS)
    @FocusState private var focusedControl: TVFocusTarget?
    #endif
    var body: some View {
        ZStack {
            #if os(tvOS)
            tvOverlay
            #else
            iosOverlay
            #endif
            if showSubtitleSettings {
                subtitleSettingsOverlay
            }
        }
        .animation(.easeInOut(duration: 0.2), value: showSubtitleSettings)
        #if os(tvOS)
        .onExitCommand {
            if showSubtitleSettings {
                showSubtitleSettings = false
            }
        }
        .onAppear {
            if showTVControls {
                focusedControl = .playPause
            }
        }
        .onChange(of: showSubtitleSettings) { _, isVisible in
            if !isVisible, showTVControls {
                focusedControl = .playPause
            }
        }
        .onChange(of: showTVControls) { _, isVisible in
            if isVisible {
                focusedControl = .playPause
            } else {
                focusedControl = nil
            }
        }
        #endif
    }

    private var iosOverlay: some View {
        VStack {
            topBar
            Spacer()
            subtitleStack
        }
    }

    #if os(tvOS)
    @ViewBuilder
    private var tvOverlay: some View {
        if showTVControls {
            VStack(spacing: 16) {
                Spacer()
                subtitleStack
                tvBottomBar
            }
            .padding(.horizontal, 60)
            .padding(.bottom, 36)
            .onPlayPauseCommand {
                onPlayPause()
                onUserInteraction()
            }
        } else {
            VStack(spacing: 16) {
                Spacer()
                subtitleStack
            }
            .padding(.horizontal, 60)
            .padding(.bottom, 36)
            .contentShape(Rectangle())
            .onTapGesture {
                onUserInteraction()
            }
            .onPlayPauseCommand {
                onPlayPause()
                onUserInteraction()
            }
        }
    }
    #endif

    @ViewBuilder
    private var subtitleStack: some View {
        SubtitleOverlayView(
            cues: cues,
            currentTime: currentTime,
            visibility: subtitleVisibility
        )
        .padding(.horizontal)
        .allowsHitTesting(false)
        if let subtitleError {
            Text(subtitleError)
                .font(.caption)
                .foregroundStyle(.white)
                .padding(8)
                .background(.black.opacity(0.7), in: RoundedRectangle(cornerRadius: 8))
                .padding(.bottom, 12)
                .allowsHitTesting(false)
        }
    }

    @ViewBuilder
    private var subtitleSettingsOverlay: some View {
        Color.black.opacity(0.55)
            .ignoresSafeArea()
            .onTapGesture {
                showSubtitleSettings = false
            }
        #if os(tvOS)
        VStack {
            Spacer()
            SubtitleSettingsPanel(
                tracks: tracks,
                selectedTrack: $selectedTrack,
                visibility: $subtitleVisibility,
                onClose: { showSubtitleSettings = false }
            )
            .frame(maxWidth: 680)
            .padding(.bottom, 36)
        }
        .padding(.horizontal, 60)
        .transition(.move(edge: .bottom).combined(with: .opacity))
        #else
        SubtitleSettingsPanel(
            tracks: tracks,
            selectedTrack: $selectedTrack,
            visibility: $subtitleVisibility,
            onClose: { showSubtitleSettings = false }
        )
        .padding(.horizontal, 24)
        .transition(.opacity)
        #endif
    }

    @ViewBuilder
    private var topBar: some View {
        HStack(alignment: .top, spacing: 12) {
            #if !os(tvOS)
            Button(action: { dismiss() }) {
                Image(systemName: "xmark")
                    .font(.caption.weight(.semibold))
                    .padding(8)
                    .background(.black.opacity(0.45), in: Circle())
                    .foregroundStyle(.white)
            }
            #endif
            if hasMetadata {
                metadataView
            }

            Spacer()

            #if os(tvOS)
            tvControls
            #else
            if hasTracks {
                subtitleButton
            }
            #endif
        }
        .padding(.top, 10)
        .padding(.horizontal, 12)
    }

    private var metadataView: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(metadata.title)
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(.white)
                .lineLimit(1)
            if let subtitle = metadata.subtitle, !subtitle.isEmpty {
                Text(subtitle)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.8))
                    .lineLimit(1)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
    }

    private var subtitleButton: some View {
        Button {
            showSubtitleSettings = true
        } label: {
            Label(
                selectedTrackLabel,
                systemImage: "captions.bubble"
            )
            .labelStyle(.titleAndIcon)
            .font(.caption)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
            .foregroundStyle(.white)
        }
    }

    #if os(tvOS)
    private var tvControls: some View {
        HStack(spacing: 14) {
            tvControlButton(systemName: "gobackward.15", action: onSkipBackward)
                .focused($focusedControl, equals: .skipBackward)
            tvControlButton(systemName: isPlaying ? "pause.fill" : "play.fill", action: onPlayPause)
                .focused($focusedControl, equals: .playPause)
            tvControlButton(systemName: "goforward.15", action: onSkipForward)
                .focused($focusedControl, equals: .skipForward)
            if hasTracks {
                tvControlButton(systemName: "captions.bubble", label: "Options") {
                    showSubtitleSettings = true
                }
                .focused($focusedControl, equals: .captions)
            }
        }
    }

    private func tvControlButton(
        systemName: String,
        label: String? = nil,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            if let label {
                Label(label, systemImage: systemName)
                    .labelStyle(.titleAndIcon)
            } else {
                Image(systemName: systemName)
            }
        }
        .font(.title3.weight(.semibold))
        .foregroundStyle(.white)
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 12))
    }

    private var tvBottomBar: some View {
        VStack(spacing: 10) {
            HStack(alignment: .center, spacing: 18) {
                if hasMetadata {
                    tvMetadataView
                }
                Spacer(minLength: 20)
                tvControls
            }
            if duration > 0 {
                HStack(spacing: 12) {
                    Text(formattedTime(displayTime))
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.8))
                        .frame(width: 64, alignment: .leading)
                    TVScrubber(
                        value: $scrubberValue,
                        range: 0...max(duration, 1),
                        onEditingChanged: { editing in
                            isScrubbing = editing
                            onUserInteraction()
                        },
                        onCommit: { newValue in
                            onSeek(newValue)
                        },
                        onUserInteraction: onUserInteraction
                    )
                    Text(formattedTime(duration))
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.8))
                        .frame(width: 64, alignment: .trailing)
                }
            }
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .background(
            LinearGradient(
                colors: [Color.black.opacity(0.75), Color.black.opacity(0.35)],
                startPoint: .bottom,
                endPoint: .top
            ),
            in: RoundedRectangle(cornerRadius: 20)
        )
        .opacity(showTVControls ? 1 : 0)
        .allowsHitTesting(showTVControls)
        .animation(.easeInOut(duration: 0.2), value: showTVControls)
        .focusSection()
    }

    private var tvMetadataView: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(metadata.title)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.white)
                .lineLimit(1)
            if let subtitle = metadata.subtitle, !subtitle.isEmpty {
                Text(subtitle)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.75))
                    .lineLimit(1)
            }
        }
    }

    private var displayTime: Double {
        isScrubbing ? scrubberValue : currentTime
    }

    private func formattedTime(_ seconds: Double) -> String {
        guard seconds.isFinite else { return "--:--" }
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
    #endif

    private var selectedTrackLabel: String {
        if let selectedTrack {
            return selectedTrack.label
        }
        return "Subtitles Off"
    }

    private var hasMetadata: Bool {
        !metadata.title.isEmpty || (metadata.subtitle?.isEmpty == false)
    }

    private var hasTracks: Bool {
        !tracks.isEmpty
    }
}

#if os(tvOS)
private enum TVFocusTarget: Hashable {
    case playPause
    case skipBackward
    case skipForward
    case captions
}

private struct TVScrubber: View {
    @Binding var value: Double
    let range: ClosedRange<Double>
    let onEditingChanged: (Bool) -> Void
    let onCommit: (Double) -> Void
    let onUserInteraction: () -> Void

    @FocusState private var isFocused: Bool
    @State private var commitTask: Task<Void, Never>?
    @State private var isEditing = false

    var body: some View {
        GeometryReader { proxy in
            let progress = normalizedProgress
            let width = max(proxy.size.width, 1)
            let barHeight: CGFloat = 6
            let thumbSize: CGFloat = isFocused ? 18 : 14
            let xOffset = max(0, min(width - thumbSize, width * progress - thumbSize / 2))
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color.white.opacity(0.25))
                    .frame(height: barHeight)
                Capsule()
                    .fill(Color.white)
                    .frame(width: max(thumbSize, width * progress), height: barHeight)
                Circle()
                    .fill(Color.white)
                    .frame(width: thumbSize, height: thumbSize)
                    .offset(x: xOffset)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(height: 24)
        .focusable(true)
        .focused($isFocused)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isFocused ? Color.white.opacity(0.8) : .clear, lineWidth: 1)
        )
        .onChange(of: isFocused) { _, focused in
            onUserInteraction()
            if !focused {
                commitScrub()
            }
        }
        .onMoveCommand { direction in
            guard isFocused else { return }
            onUserInteraction()
            beginScrubbing()
            let step = stepSize
            switch direction {
            case .left:
                value = max(range.lowerBound, value - step)
            case .right:
                value = min(range.upperBound, value + step)
            default:
                break
            }
            scheduleCommit()
        }
        .onTapGesture {
            onUserInteraction()
            beginScrubbing()
            scheduleCommit()
        }
    }

    private var normalizedProgress: CGFloat {
        let span = max(range.upperBound - range.lowerBound, 1)
        let clamped = min(max(value, range.lowerBound), range.upperBound)
        return CGFloat((clamped - range.lowerBound) / span)
    }

    private var stepSize: Double {
        let span = max(range.upperBound - range.lowerBound, 1)
        return max(span / 300, 1)
    }

    private func scheduleCommit() {
        commitTask?.cancel()
        commitTask = Task {
            try? await Task.sleep(nanoseconds: 600_000_000)
            await MainActor.run {
                commitScrub()
            }
        }
    }

    private func commitScrub() {
        commitTask?.cancel()
        commitTask = nil
        if isEditing {
            onEditingChanged(false)
            isEditing = false
        }
        onCommit(value)
    }

    private func beginScrubbing() {
        guard !isEditing else { return }
        isEditing = true
        onEditingChanged(true)
    }
}
#endif

private struct SubtitleSettingsPanel: View {
    let tracks: [VideoSubtitleTrack]
    @Binding var selectedTrack: VideoSubtitleTrack?
    @Binding var visibility: SubtitleVisibility
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Subtitles")
                    .font(.headline)
                Spacer()
                Button("Done") {
                    onClose()
                }
                .font(.subheadline.weight(.semibold))
            }
            Divider()
                .overlay(Color.white.opacity(0.25))

            VStack(alignment: .leading, spacing: 8) {
                Text("Tracks")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.7))
                Button {
                    selectedTrack = nil
                } label: {
                    trackRow(label: "Subtitles Off", selected: selectedTrack == nil)
                }
                if tracks.isEmpty {
                    Text("No subtitle tracks available.")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.7))
                        .padding(.vertical, 4)
                } else {
                    ForEach(tracks) { track in
                        Button {
                            selectedTrack = track
                        } label: {
                            let label = "\(track.label) (\(track.format.label))"
                            trackRow(label: label, selected: selectedTrack?.id == track.id)
                        }
                    }
                }
            }

            Divider()
                .overlay(Color.white.opacity(0.25))

            VStack(alignment: .leading, spacing: 8) {
                Text("Lines")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.7))
                Toggle("Original", isOn: $visibility.showOriginal)
                Toggle("Translation", isOn: $visibility.showTranslation)
                Toggle("Transliteration", isOn: $visibility.showTransliteration)
            }
            .disabled(selectedTrack == nil)
        }
        .padding(16)
        .frame(maxWidth: panelMaxWidth)
        .background(.black.opacity(0.85), in: RoundedRectangle(cornerRadius: 16))
        .foregroundStyle(.white)
    }

    private func trackRow(label: String, selected: Bool) -> some View {
        HStack {
            Text(label)
                .lineLimit(1)
            Spacer()
            if selected {
                Image(systemName: "checkmark")
            }
        }
        .padding(.vertical, 4)
    }

    private var panelMaxWidth: CGFloat {
        #if os(tvOS)
        return 640
        #else
        return 480
        #endif
    }
}

private struct VideoPlayerControllerView: UIViewControllerRepresentable {
    let player: AVPlayer
    let onShowControls: () -> Void

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        #if os(tvOS)
        let controller = FocusablePlayerViewController()
        #else
        let controller = AVPlayerViewController()
        #endif
        controller.player = player
        #if os(tvOS)
        controller.showsPlaybackControls = false
        #else
        controller.showsPlaybackControls = true
        #endif
        controller.videoGravity = .resizeAspect
        controller.allowsPictureInPicturePlayback = true
        #if os(iOS)
        if #available(iOS 14.2, *) {
            controller.canStartPictureInPictureAutomaticallyFromInline = true
        }
        #endif
        #if os(tvOS)
        controller.onShowControls = onShowControls
        #endif
        return controller
    }

    func updateUIViewController(_ controller: AVPlayerViewController, context: Context) {
        controller.player = player
        #if os(tvOS)
        if let controller = controller as? FocusablePlayerViewController {
            controller.onShowControls = onShowControls
        }
        #endif
    }
}

#if os(tvOS)
private final class FocusablePlayerViewController: AVPlayerViewController {
    var onShowControls: (() -> Void)?

    override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
        for press in presses {
            switch press.type {
            case .select, .playPause, .upArrow, .downArrow, .leftArrow, .rightArrow:
                onShowControls?()
            default:
                break
            }
        }
        super.pressesBegan(presses, with: event)
    }
}
#endif
