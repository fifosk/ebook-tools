import AVKit
import SwiftUI

struct VideoPlayerControllerView: UIViewControllerRepresentable {
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
        controller.view.isUserInteractionEnabled = false
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
        controller.view.isUserInteractionEnabled = false
        #endif
    }
}

#if os(tvOS)
final class FocusablePlayerViewController: AVPlayerViewController {
    var onShowControls: (() -> Void)?

    override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
        for press in presses {
            switch press.type {
            case .playPause, .upArrow, .downArrow, .leftArrow, .rightArrow:
                onShowControls?()
            default:
                break
            }
        }
        super.pressesBegan(presses, with: event)
    }
}
#endif
