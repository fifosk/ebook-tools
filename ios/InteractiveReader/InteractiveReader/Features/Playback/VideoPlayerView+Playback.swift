import AVFoundation
import Foundation
import SwiftUI

extension VideoPlayerView {
    func applyPendingResumeIfPossible() {
        guard let pendingResumeTime else { return }
        guard let player = coordinator.playerInstance() else { return }
        let isReady = player.currentItem?.status == .readyToPlay
        guard isReady || coordinator.duration > 0 else { return }
        let clamped = max(0, pendingResumeTime)
        coordinator.seek(to: clamped)
        if autoPlay {
            coordinator.play()
        }
        self.pendingResumeTime = nil
    }

    func applyPendingBookmarkIfPossible() {
        guard let pendingBookmarkSeek else { return }
        if let segmentId = pendingBookmarkSeek.segmentId,
           segmentId != selectedSegmentID {
            return
        }
        guard let player = coordinator.playerInstance() else { return }
        let isReady = player.currentItem?.status == .readyToPlay
        guard isReady || coordinator.duration > 0 else { return }
        applyBookmarkSeek(time: pendingBookmarkSeek.time, shouldPlay: pendingBookmarkSeek.shouldPlay)
        self.pendingBookmarkSeek = nil
    }

    func applyBookmarkSeek(time: Double, shouldPlay: Bool) {
        let clamped = max(0, time)
        coordinator.seek(to: clamped)
        if shouldPlay {
            coordinator.play()
        }
    }

    func handleUserInteraction() {
        #if os(tvOS)
        if !showTVControls {
            withAnimation(.easeInOut(duration: 0.2)) {
                showTVControls = true
            }
        }
        scheduleControlsAutoHide()
        #endif
    }

    var videoScrubberRange: ClosedRange<Double>? {
        guard coordinator.duration.isFinite, coordinator.duration > 0 else { return nil }
        return 0...coordinator.duration
    }

    var videoScrubberDisplayValue: Double {
        guard let range = videoScrubberRange else { return 0 }
        let source = isScrubbing ? scrubberValue : coordinator.currentTime
        return min(max(source, range.lowerBound), range.upperBound)
    }

    var videoScrubberLeadingLabel: String {
        guard let range = videoScrubberRange else { return "Video progress" }
        let played = VideoPlayerTimeFormatter.formatDuration(videoScrubberDisplayValue)
        let remaining = VideoPlayerTimeFormatter.formatDuration(max(range.upperBound - videoScrubberDisplayValue, 0))
        return "\(played) · \(remaining) remaining"
    }

    var videoScrubberAccessibilityValue: String {
        guard let range = videoScrubberRange else { return "No duration" }
        return "\(VideoPlayerTimeFormatter.formatDuration(videoScrubberDisplayValue)) of \(VideoPlayerTimeFormatter.formatDuration(range.upperBound))"
    }

    func handleVideoScrubberValueChange(_ value: Double) {
        guard let range = videoScrubberRange else { return }
        let clamped = min(max(value, range.lowerBound), range.upperBound)
        scrubberValue = clamped
        if isScrubbing {
            coordinator.seek(to: clamped)
        }
    }

    func handleVideoScrubberEditingChanged(_ editing: Bool) {
        handleUserInteraction()
        if editing {
            isScrubbing = true
            scrubberValue = videoScrubberDisplayValue
        } else {
            handleVideoScrubberSeek(scrubberValue)
        }
    }

    func handleVideoScrubberSeek(_ time: Double) {
        guard let range = videoScrubberRange else { return }
        let clamped = min(max(time, range.lowerBound), range.upperBound)
        scrubberValue = clamped
        isScrubbing = false
        coordinator.seek(to: clamped)
        reportPlaybackProgress(time: clamped, isPlaying: coordinator.isPlaying, force: true)
        handleUserInteraction()
    }

    func toggleHeaderCollapsed() {
        withAnimation(.easeInOut(duration: 0.2)) {
            isHeaderCollapsed.toggle()
        }
    }

    #if os(tvOS)
    func handleExitCommand() {
        if subtitleBubble != nil {
            closeSubtitleBubble()
            return
        }
        if showSubtitleSettings {
            showSubtitleSettings = false
            return
        }
        if !coordinator.isPlaying {
            #if os(tvOS)
            forceHideControlsOnPlay = true
            controlsHideTask?.cancel()
            #endif
            coordinator.play()
            withAnimation(.easeInOut(duration: 0.2)) {
                showTVControls = false
            }
            return
        }
        reportPlaybackProgress(time: resolvedPlaybackTime(), isPlaying: coordinator.isPlaying)
        dismiss()
    }
    #endif

    func reportPlaybackProgress(time: Double, isPlaying: Bool, force: Bool = false) {
        guard let onPlaybackProgress else { return }
        if isTearingDown && !force { return }
        if Thread.isMainThread {
            onPlaybackProgress(time, isPlaying)
        } else {
            DispatchQueue.main.async {
                onPlaybackProgress(time, isPlaying)
            }
        }
    }

    func resolvedPlaybackTime() -> Double {
        if let player = coordinator.playerInstance() {
            let seconds = player.currentTime().seconds
            if seconds.isFinite {
                return max(0, seconds)
            }
        }
        return coordinator.currentTime
    }

    func scheduleControlsAutoHide() {
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

    var shouldAutoHideControls: Bool {
        guard let player = coordinator.playerInstance() else { return false }
        let isActive = player.timeControlStatus == .playing || player.rate > 0
        return isActive && !showSubtitleSettings && !isScrubbing
    }
}
