#if os(iOS)
import Foundation

extension KeyboardCommandHandler.KeyCommandController {
    enum ShortcutDispatch: Hashable, CustomStringConvertible {
        case playPause
        case previous
        case next
        case previousSentence
        case nextSentence
        case extendSelectionBackward
        case extendSelectionForward
        case lookup
        case increaseFont
        case decreaseFont
        case toggleOriginal
        case toggleTransliteration
        case toggleTranslation
        case toggleOriginalAudio
        case toggleTranslationAudio
        case toggleReadingBed
        case increaseLinguistFont
        case decreaseLinguistFont
        case toggleShortcutHelp
        case toggleHeader
        case increaseHeaderScale
        case decreaseHeaderScale
        case showMenu
        case hideMenu
        case bubbleNavigateLeft
        case bubbleNavigateRight

        var description: String {
            switch self {
            case .playPause: "playPause"
            case .previous: "previous"
            case .next: "next"
            case .previousSentence: "previousSentence"
            case .nextSentence: "nextSentence"
            case .extendSelectionBackward: "extendSelectionBackward"
            case .extendSelectionForward: "extendSelectionForward"
            case .lookup: "lookup"
            case .increaseFont: "increaseFont"
            case .decreaseFont: "decreaseFont"
            case .toggleOriginal: "toggleOriginal"
            case .toggleTransliteration: "toggleTransliteration"
            case .toggleTranslation: "toggleTranslation"
            case .toggleOriginalAudio: "toggleOriginalAudio"
            case .toggleTranslationAudio: "toggleTranslationAudio"
            case .toggleReadingBed: "toggleReadingBed"
            case .increaseLinguistFont: "increaseLinguistFont"
            case .decreaseLinguistFont: "decreaseLinguistFont"
            case .toggleShortcutHelp: "toggleShortcutHelp"
            case .toggleHeader: "toggleHeader"
            case .increaseHeaderScale: "increaseHeaderScale"
            case .decreaseHeaderScale: "decreaseHeaderScale"
            case .showMenu: "showMenu"
            case .hideMenu: "hideMenu"
            case .bubbleNavigateLeft: "bubbleNavigateLeft"
            case .bubbleNavigateRight: "bubbleNavigateRight"
            }
        }
    }

    var shouldRoutePlainArrowToBubbleWords: Bool {
        shouldNavigateBubbleWords?() == true
    }

    func dispatchPreviousArrowShortcut(source: String) {
        if shouldRoutePlainArrowToBubbleWords, onBubbleNavigateLeft != nil {
            dispatchShortcut(.bubbleNavigateLeft, source: source) { self.onBubbleNavigateLeft?() }
        } else {
            dispatchShortcut(.previous, source: source) { self.onPrevious?() }
        }
    }

    func dispatchNextArrowShortcut(source: String) {
        if shouldRoutePlainArrowToBubbleWords, onBubbleNavigateRight != nil {
            dispatchShortcut(.bubbleNavigateRight, source: source) { self.onBubbleNavigateRight?() }
        } else {
            dispatchShortcut(.next, source: source) { self.onNext?() }
        }
    }

    func dispatchShortcut(
        _ shortcut: ShortcutDispatch,
        source: String,
        action: @escaping () -> Void
    ) {
        if source != "gc", source != "broker", hardwareKeyboardInput != nil {
            scheduleUIKitFallback(shortcut, action: action)
            return
        }
        if source == "gc" {
            cancelPendingUIKitFallback(shortcut)
        }
        let now = ProcessInfo.processInfo.systemUptime
        if source != "gc",
           let lastShortcutDispatch,
           lastShortcutDispatch.shortcut == shortcut,
           now - lastShortcutDispatch.timestamp < 0.16 {
            return
        }
        lastShortcutDispatch = (shortcut, now)
        #if DEBUG
        if source == "gc" || source == "broker" || source == "press" || source == "input" {
            keyboardShortcutDebugLog("[KeyboardShortcut] \(source) handled \(shortcut)")
        }
        #endif
        action()
    }

    func cancelPendingUIKitFallbacks() {
        for fallback in pendingUIKitFallbacks.values {
            fallback.cancel()
        }
        pendingUIKitFallbacks.removeAll()
    }

    private func scheduleUIKitFallback(
        _ shortcut: ShortcutDispatch,
        action: @escaping () -> Void
    ) {
        let now = ProcessInfo.processInfo.systemUptime
        if let lastShortcutDispatch,
           lastShortcutDispatch.shortcut == shortcut,
           now - lastShortcutDispatch.timestamp < 0.16 {
            #if DEBUG
            keyboardShortcutDebugLog("[KeyboardShortcut] UIKit ignored \(shortcut) after recent GameController dispatch")
            #endif
            return
        }
        pendingUIKitFallbacks[shortcut]?.cancel()
        let workItem = DispatchWorkItem { [weak self] in
            guard let self else { return }
            let now = ProcessInfo.processInfo.systemUptime
            if let lastShortcutDispatch = self.lastShortcutDispatch,
               lastShortcutDispatch.shortcut == shortcut,
               now - lastShortcutDispatch.timestamp < 0.16 {
                return
            }
            self.lastShortcutDispatch = (shortcut, now)
            self.pendingUIKitFallbacks[shortcut] = nil
            #if DEBUG
            keyboardShortcutDebugLog("[KeyboardShortcut] UIKit backup handled \(shortcut)")
            #endif
            action()
        }
        pendingUIKitFallbacks[shortcut] = workItem
        #if DEBUG
        keyboardShortcutDebugLog("[KeyboardShortcut] UIKit deferred \(shortcut) because GameController is active")
        #endif
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05, execute: workItem)
    }

    private func cancelPendingUIKitFallback(_ shortcut: ShortcutDispatch) {
        pendingUIKitFallbacks[shortcut]?.cancel()
        pendingUIKitFallbacks[shortcut] = nil
    }
}
#endif
