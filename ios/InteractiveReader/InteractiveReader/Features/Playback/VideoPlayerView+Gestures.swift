import SwiftUI
#if os(iOS)
import UIKit
#endif

extension VideoPlayerView {
    #if os(iOS)
    var videoTapGesture: some Gesture {
        TapGesture()
            .onEnded {
                coordinator.togglePlayback()
            }
    }

    var videoScrubGesture: some Gesture {
        DragGesture(minimumDistance: 12, coordinateSpace: .local)
            .onChanged { value in
                guard !showSubtitleSettings else { return }
                guard abs(value.translation.width) >= abs(value.translation.height) else { return }
                beginVideoScrubGestureIfNeeded()
                let duration = coordinator.duration
                guard duration > 0 else { return }
                let width = max(videoScrubWidth, 1)
                let delta = Double(value.translation.width / width) * duration
                let target = min(max(videoScrubStartTime + delta, 0), duration)
                scrubberValue = target
                coordinator.seek(to: target)
            }
            .onEnded { _ in
                endVideoScrubGesture()
            }
    }

    var videoViewportReader: some View {
        GeometryReader { proxy in
            Color.clear
                .onAppear {
                    videoViewportSize = proxy.size
                }
                .onChange(of: proxy.size) { _, newValue in
                    videoViewportSize = newValue
                }
        }
        .allowsHitTesting(false)
    }

    var videoScrubWidth: CGFloat {
        if videoViewportSize.width > 0 {
            return videoViewportSize.width
        }
        return UIScreen.main.bounds.width
    }

    func beginVideoScrubGestureIfNeeded() {
        guard !isVideoScrubGestureActive else { return }
        isVideoScrubGestureActive = true
        isScrubbing = true
        videoScrubStartTime = coordinator.currentTime
        scrubberValue = coordinator.currentTime
    }

    func endVideoScrubGesture() {
        guard isVideoScrubGestureActive else { return }
        isVideoScrubGestureActive = false
        isScrubbing = false
        coordinator.seek(to: scrubberValue)
    }
    #endif
}
