#if os(iOS)
import UIKit

extension KeyboardCommandHandler.KeyCommandController {
    // The periodic timer alone is not enough: SwiftUI buttons and focused
    // views often take first-responder priority right after a user tap.
    func installWindowTouchObserver() {
        guard windowTouchObserver == nil else { return }
        guard let window = view.window else { return }
        let catcher = WindowTouchCatcher()
        catcher.onTouchesEnded = { [weak self] in
            self?.reclaimFirstResponderNow()
        }
        window.addGestureRecognizer(catcher)
        windowTouchObserver = catcher
    }

    func removeWindowTouchObserver() {
        if let catcher = windowTouchObserver,
           let window = catcher.view {
            window.removeGestureRecognizer(catcher)
        }
        windowTouchObserver = nil
    }

    @objc func handleKeyboardWillShow() {
        softwareKeyboardVisible = true
    }

    @objc func handleKeyboardDidHide() {
        softwareKeyboardVisible = false
        reclaimFirstResponderNow()
    }

    func startReclaimTimer() {
        stopReclaimTimer()
        reclaimTimer = Timer.scheduledTimer(
            withTimeInterval: 0.5,
            repeats: true
        ) { [weak self] _ in
            self?.reclaimFirstResponderNow()
        }
        if let timer = reclaimTimer {
            RunLoop.main.add(timer, forMode: .common)
        }
    }

    func stopReclaimTimer() {
        reclaimTimer?.invalidate()
        reclaimTimer = nil
    }

    @objc func reclaimFirstResponderNow() {
        performFirstResponderReclaim(ignoringSoftwareKeyboard: false)
    }

    @objc func forceReclaimFirstResponderNow() {
        refreshHardwareKeyboardFallback()
        performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
            self?.refreshHardwareKeyboardFallback()
            self?.performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { [weak self] in
            self?.refreshHardwareKeyboardFallback()
            self?.performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
        }
    }

    func performFirstResponderReclaim(ignoringSoftwareKeyboard: Bool) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            guard self.view.window != nil else { return }
            if self.softwareKeyboardVisible && !ignoringSoftwareKeyboard {
                return
            }
            self.focusShortcutResponder()
        }
    }

    @discardableResult
    func focusShortcutResponder() -> Bool {
        if let hostView = view as? KeyCommandHostView {
            focusShortcutItem(hostView)
            let claimed = hostView.becomeFirstResponder()
            #if DEBUG
            if claimed || hostView.isFirstResponder {
                hostView.logFocusClaimIfNeeded()
            }
            #endif
            return claimed || hostView.isFirstResponder
        }

        let claimed = becomeFirstResponder()
        view.window?.windowScene?.focusSystem?.requestFocusUpdate(to: view)
        view.window?.windowScene?.focusSystem?.updateFocusIfNeeded()
        #if DEBUG
        if claimed || isFirstResponder {
            keyboardShortcutDebugLog("[KeyboardShortcut] Key command controller became first responder")
        }
        #endif
        return claimed || isFirstResponder
    }

    func focusShortcutItem(_ hostView: KeyCommandHostView) {
        hostView.setNeedsFocusUpdate()
        if let focusSystem = hostView.window?.windowScene?.focusSystem {
            focusSystem.requestFocusUpdate(to: hostView)
            focusSystem.updateFocusIfNeeded()
        } else {
            hostView.updateFocusIfNeeded()
        }
    }
}
#endif
