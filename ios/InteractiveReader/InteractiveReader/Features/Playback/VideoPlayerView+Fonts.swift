import SwiftUI

extension VideoPlayerView {
    func adjustSubtitleFontScale(by delta: CGFloat) {
        setSubtitleFontScale(subtitleFontScale + delta)
    }

    var canIncreaseSubtitleLinguistFont: Bool {
        subtitleLinguistFontScale + subtitleLinguistFontScaleStep <= subtitleLinguistFontScaleMax
    }

    var canDecreaseSubtitleLinguistFont: Bool {
        subtitleLinguistFontScale - subtitleLinguistFontScaleStep >= subtitleLinguistFontScaleMin
    }

    func adjustSubtitleLinguistFontScale(by delta: CGFloat) {
        setSubtitleLinguistFontScale(subtitleLinguistFontScale + delta)
    }

    func setSubtitleFontScale(_ value: CGFloat) {
        let updated = min(max(value, subtitleFontScaleMin), subtitleFontScaleMax)
        if updated != subtitleFontScale {
            subtitleFontScale = updated
        }
    }

    func resetSubtitleFontScale() {
        setSubtitleFontScale(VideoPlayerView.defaultSubtitleFontScale)
    }

    func setSubtitleLinguistFontScale(_ value: CGFloat) {
        let updated = min(max(value, subtitleLinguistFontScaleMin), subtitleLinguistFontScaleMax)
        if updated != subtitleLinguistFontScale {
            subtitleLinguistFontScale = updated
        }
    }

    func resetSubtitleLinguistFontScale() {
        setSubtitleLinguistFontScale(1.0)
    }

    func toggleShortcutHelp() {
        isShortcutHelpPinned.toggle()
    }

    func showShortcutHelpModifier() {
        isShortcutHelpModifierActive = true
    }

    func hideShortcutHelpModifier() {
        isShortcutHelpModifierActive = false
    }

    func dismissShortcutHelp() {
        isShortcutHelpPinned = false
    }

    var subtitleFontScale: CGFloat {
        get { CGFloat(subtitleFontScaleValue) }
        nonmutating set { subtitleFontScaleValue = Double(newValue) }
    }

    var subtitleLinguistFontScale: CGFloat {
        get { CGFloat(subtitleLinguistFontScaleValue) }
        nonmutating set { subtitleLinguistFontScaleValue = Double(newValue) }
    }
}
