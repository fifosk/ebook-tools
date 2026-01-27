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
        // On tvOS, controls are shown only when user swipes down from subtitles while paused
        // This function is called to reset auto-hide timer when controls are already visible
        if showTVControls {
            scheduleControlsAutoHide()
        }
        #endif
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
