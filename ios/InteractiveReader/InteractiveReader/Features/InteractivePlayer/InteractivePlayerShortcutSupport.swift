import SwiftUI
#if os(iOS)
import GameController
import UIKit
#endif

#if os(iOS)
struct TrackpadSwipeHandler: UIViewRepresentable {
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

struct KeyboardCommandHandler: UIViewControllerRepresentable {
    let onPlayPause: () -> Void
    let onPrevious: () -> Void
    let onNext: () -> Void
    let onPreviousWord: () -> Void
    let onNextWord: () -> Void
    /// Navigate to previous sentence (Ctrl+Left when paused)
    let onPreviousSentence: () -> Void
    /// Navigate to next sentence (Ctrl+Right when paused)
    let onNextSentence: () -> Void
    let onExtendSelectionBackward: () -> Void
    let onExtendSelectionForward: () -> Void
    let onLookup: () -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onToggleOriginal: () -> Void
    let onToggleTransliteration: () -> Void
    let onToggleTranslation: () -> Void
    let onToggleOriginalAudio: () -> Void
    let onToggleTranslationAudio: () -> Void
    let onToggleReadingBed: () -> Void
    let onIncreaseLinguistFont: () -> Void
    let onDecreaseLinguistFont: () -> Void
    let onToggleShortcutHelp: () -> Void
    let onToggleHeader: () -> Void
    let onIncreaseHeaderScale: () -> Void
    let onDecreaseHeaderScale: () -> Void
    let onOptionKeyDown: () -> Void
    let onOptionKeyUp: () -> Void
    let onShowMenu: () -> Void
    let onHideMenu: () -> Void
    var onBubbleNavigateLeft: (() -> Void)? = nil
    var onBubbleNavigateRight: (() -> Void)? = nil

    func makeUIViewController(context: Context) -> KeyCommandController {
        let controller = KeyCommandController()
        controller.onPlayPause = onPlayPause
        controller.onPrevious = onPrevious
        controller.onNext = onNext
        controller.onPreviousWord = onPreviousWord
        controller.onNextWord = onNextWord
        controller.onPreviousSentence = onPreviousSentence
        controller.onNextSentence = onNextSentence
        controller.onExtendSelectionBackward = onExtendSelectionBackward
        controller.onExtendSelectionForward = onExtendSelectionForward
        controller.onLookup = onLookup
        controller.onIncreaseFont = onIncreaseFont
        controller.onDecreaseFont = onDecreaseFont
        controller.onToggleOriginal = onToggleOriginal
        controller.onToggleTransliteration = onToggleTransliteration
        controller.onToggleTranslation = onToggleTranslation
        controller.onToggleOriginalAudio = onToggleOriginalAudio
        controller.onToggleTranslationAudio = onToggleTranslationAudio
        controller.onToggleReadingBed = onToggleReadingBed
        controller.onIncreaseLinguistFont = onIncreaseLinguistFont
        controller.onDecreaseLinguistFont = onDecreaseLinguistFont
        controller.onToggleShortcutHelp = onToggleShortcutHelp
        controller.onToggleHeader = onToggleHeader
        controller.onIncreaseHeaderScale = onIncreaseHeaderScale
        controller.onDecreaseHeaderScale = onDecreaseHeaderScale
        controller.onOptionKeyDown = onOptionKeyDown
        controller.onOptionKeyUp = onOptionKeyUp
        controller.onShowMenu = onShowMenu
        controller.onHideMenu = onHideMenu
        controller.onBubbleNavigateLeft = onBubbleNavigateLeft
        controller.onBubbleNavigateRight = onBubbleNavigateRight
        return controller
    }

    func updateUIViewController(_ uiViewController: KeyCommandController, context: Context) {
        uiViewController.onPlayPause = onPlayPause
        uiViewController.onPrevious = onPrevious
        uiViewController.onNext = onNext
        uiViewController.onPreviousWord = onPreviousWord
        uiViewController.onNextWord = onNextWord
        uiViewController.onPreviousSentence = onPreviousSentence
        uiViewController.onNextSentence = onNextSentence
        uiViewController.onExtendSelectionBackward = onExtendSelectionBackward
        uiViewController.onExtendSelectionForward = onExtendSelectionForward
        uiViewController.onLookup = onLookup
        uiViewController.onIncreaseFont = onIncreaseFont
        uiViewController.onDecreaseFont = onDecreaseFont
        uiViewController.onToggleOriginal = onToggleOriginal
        uiViewController.onToggleTransliteration = onToggleTransliteration
        uiViewController.onToggleTranslation = onToggleTranslation
        uiViewController.onToggleOriginalAudio = onToggleOriginalAudio
        uiViewController.onToggleTranslationAudio = onToggleTranslationAudio
        uiViewController.onToggleReadingBed = onToggleReadingBed
        uiViewController.onIncreaseLinguistFont = onIncreaseLinguistFont
        uiViewController.onDecreaseLinguistFont = onDecreaseLinguistFont
        uiViewController.onToggleShortcutHelp = onToggleShortcutHelp
        uiViewController.onToggleHeader = onToggleHeader
        uiViewController.onIncreaseHeaderScale = onIncreaseHeaderScale
        uiViewController.onDecreaseHeaderScale = onDecreaseHeaderScale
        uiViewController.onOptionKeyDown = onOptionKeyDown
        uiViewController.onOptionKeyUp = onOptionKeyUp
        uiViewController.onShowMenu = onShowMenu
        uiViewController.onHideMenu = onHideMenu
        uiViewController.onBubbleNavigateLeft = onBubbleNavigateLeft
        uiViewController.onBubbleNavigateRight = onBubbleNavigateRight
        uiViewController.refreshHardwareKeyboardFallback()
    }

    final class KeyCommandController: UIViewController {
        var onPlayPause: (() -> Void)?
        var onPrevious: (() -> Void)?
        var onNext: (() -> Void)?
        var onPreviousWord: (() -> Void)?
        var onNextWord: (() -> Void)?
        var onPreviousSentence: (() -> Void)?
        var onNextSentence: (() -> Void)?
        var onExtendSelectionBackward: (() -> Void)?
        var onExtendSelectionForward: (() -> Void)?
        var onLookup: (() -> Void)?
        var onIncreaseFont: (() -> Void)?
        var onDecreaseFont: (() -> Void)?
        var onToggleOriginal: (() -> Void)?
        var onToggleTransliteration: (() -> Void)?
        var onToggleTranslation: (() -> Void)?
        var onToggleOriginalAudio: (() -> Void)?
        var onToggleTranslationAudio: (() -> Void)?
        var onToggleReadingBed: (() -> Void)?
        var onIncreaseLinguistFont: (() -> Void)?
        var onDecreaseLinguistFont: (() -> Void)?
        var onToggleShortcutHelp: (() -> Void)?
        var onToggleHeader: (() -> Void)?
        var onIncreaseHeaderScale: (() -> Void)?
        var onDecreaseHeaderScale: (() -> Void)?
        var onOptionKeyDown: (() -> Void)?
        var onOptionKeyUp: (() -> Void)?
        var onShowMenu: (() -> Void)?
        var onHideMenu: (() -> Void)?
        var onBubbleNavigateLeft: (() -> Void)?
        var onBubbleNavigateRight: (() -> Void)?
        private var isOptionKeyDown = false
        private var lastShortcutDispatch: (shortcut: ShortcutDispatch, timestamp: TimeInterval)?
        private var pendingUIKitFallbacks: [ShortcutDispatch: DispatchWorkItem] = [:]

        override func loadView() {
            let hostView: KeyCommandHostView
            if #available(iOS 18.0, *) {
                hostView = DeferralSafeKeyCommandHostView()
            } else {
                hostView = KeyCommandHostView()
            }
            hostView.controller = self
            hostView.backgroundColor = .clear
            view = hostView
        }

        override var canBecomeFirstResponder: Bool {
            true
        }

        override var preferredFocusEnvironments: [UIFocusEnvironment] {
            [view]
        }

        override func viewWillAppear(_ animated: Bool) {
            super.viewWillAppear(animated)
            // Also try early: some iPad multitasking layouts delay viewDidAppear,
            // leaving a window where hardware-key events miss.
            performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
        }

        // Periodic reclaim: iPadOS routes arrow keys to whatever scrollable
        // view was most recently tapped (for trackpad/keyboard scrolling). A
        // tap on a ScrollView, a dictionary lookup closing, or any other
        // SwiftUI-internal focus shift silently pulls first responder away
        // from us — there is no public notification for that, so we poll.
        private var reclaimTimer: Timer?
        // Tracks whether the software keyboard is visible so we don't yank
        // focus away from a user who is actively typing in a text field.
        private var softwareKeyboardVisible = false
        // Block-based notification observer tokens for app-level shortcut
        // notifications posted by AppDelegate.
        private var shortcutObserverTokens: [NSObjectProtocol] = []

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
            refreshHardwareKeyboardFallback()
            installFocusObservers()
            startReclaimTimer()
            installWindowTouchObserver()
        }

        override func viewWillDisappear(_ animated: Bool) {
            super.viewWillDisappear(animated)
            removeFocusObservers()
            stopReclaimTimer()
            removeWindowTouchObserver()
            cancelPendingUIKitFallbacks()
            PlayerKeyboardShortcutBroker.shared.clearActions(owner: self)
        }

        // ── Window-level touch observer ───────────────────────────────────
        // The periodic timer alone is not enough: SwiftUI buttons and focused
        // views often take first-responder priority right after a user tap
        // (e.g. tapping Play starts playback but leaves the button focused
        // and consuming the Space key). We attach a transparent gesture
        // recognizer to the key window that watches every touches-ended and
        // reclaims first responder right after — the same action the user
        // had to do manually with an extra tap.
        private var windowTouchObserver: WindowTouchCatcher?

        private func installWindowTouchObserver() {
            guard windowTouchObserver == nil else { return }
            guard let window = view.window else { return }
            let catcher = WindowTouchCatcher()
            catcher.onTouchesEnded = { [weak self] in
                self?.reclaimFirstResponderNow()
            }
            window.addGestureRecognizer(catcher)
            windowTouchObserver = catcher
        }

        private func removeWindowTouchObserver() {
            if let catcher = windowTouchObserver,
               let window = catcher.view {
                window.removeGestureRecognizer(catcher)
            }
            windowTouchObserver = nil
        }

        private func installFocusObservers() {
            let center = NotificationCenter.default
            center.addObserver(
                self,
                selector: #selector(reclaimFirstResponderNow),
                name: UIApplication.didBecomeActiveNotification,
                object: nil
            )
            center.addObserver(
                self,
                selector: #selector(reclaimFirstResponderNow),
                name: UIWindow.didBecomeKeyNotification,
                object: nil
            )
            center.addObserver(
                self,
                selector: #selector(handleKeyboardWillShow),
                name: UIResponder.keyboardWillShowNotification,
                object: nil
            )
            center.addObserver(
                self,
                selector: #selector(handleKeyboardDidHide),
                name: UIResponder.keyboardDidHideNotification,
                object: nil
            )
            center.addObserver(
                self,
                selector: #selector(forceReclaimFirstResponderNow),
                name: .keyboardShortcutReclaimFocus,
                object: nil
            )
            // App-level keyboard shortcuts posted by AppDelegate via
            // buildMenu — these always fire regardless of first-responder
            // state, so the handlers below are the guaranteed path to our
            // callbacks. The local UIKeyCommand set still handles the same
            // keys when we do happen to hold first responder; either path
            // invokes the same handlers.
            let shortcuts: [(Notification.Name, () -> Void)] = [
                (.keyboardShortcutPlayPause, { [weak self] in self?.handlePlayPause() }),
                (.keyboardShortcutPrevious, { [weak self] in self?.handlePrevious() }),
                (.keyboardShortcutNext, { [weak self] in self?.handleNext() }),
                (.keyboardShortcutPreviousSentence, { [weak self] in self?.handlePreviousWord() }),
                (.keyboardShortcutNextSentence, { [weak self] in self?.handleNextWord() }),
                (.keyboardShortcutLookup, { [weak self] in self?.handleLookup() }),
                (.keyboardShortcutShowMenu, { [weak self] in self?.handleShowMenu() }),
                (.keyboardShortcutHideMenu, { [weak self] in self?.handleHideMenu() }),
            ]
            for (name, handler) in shortcuts {
                let token = center.addObserver(forName: name, object: nil, queue: .main) { _ in
                    handler()
                }
                shortcutObserverTokens.append(token)
            }
        }

        private func removeFocusObservers() {
            NotificationCenter.default.removeObserver(self)
            for token in shortcutObserverTokens {
                NotificationCenter.default.removeObserver(token)
            }
            shortcutObserverTokens.removeAll()
        }

        @objc private func handleKeyboardWillShow() {
            softwareKeyboardVisible = true
        }

        @objc private func handleKeyboardDidHide() {
            softwareKeyboardVisible = false
            // Keyboard just dismissed → snap focus back right away, don't
            // wait for the next timer tick.
            reclaimFirstResponderNow()
        }

        private func startReclaimTimer() {
            stopReclaimTimer()
            reclaimTimer = Timer.scheduledTimer(
                withTimeInterval: 0.5,
                repeats: true
            ) { [weak self] _ in
                self?.reclaimFirstResponderNow()
            }
            if let t = reclaimTimer {
                RunLoop.main.add(t, forMode: .common)
            }
        }

        private func stopReclaimTimer() {
            reclaimTimer?.invalidate()
            reclaimTimer = nil
        }

        @objc private func reclaimFirstResponderNow() {
            performFirstResponderReclaim(ignoringSoftwareKeyboard: false)
        }

        @objc private func forceReclaimFirstResponderNow() {
            performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
                self?.performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { [weak self] in
                self?.performFirstResponderReclaim(ignoringSoftwareKeyboard: true)
            }
        }

        private func performFirstResponderReclaim(ignoringSoftwareKeyboard: Bool) {
            DispatchQueue.main.async { [weak self] in
                guard let self else { return }
                guard self.view.window != nil else { return }
                // Skip only when the user is visibly typing — detected via
                // the software-keyboard notifications rather than by walking
                // the subview tree (which caught stale text fields that had
                // already resigned but were still attached, e.g. inside a
                // closed lookup bubble).
                if self.softwareKeyboardVisible && !ignoringSoftwareKeyboard {
                    return
                }
                // Always call becomeFirstResponder: even when isFirstResponder
                // reports true UIKit occasionally has a stale chain where our
                // keyCommands aren't actually being consulted. becomeFirstResponder
                // is idempotent if we really are still first responder.
                self.focusShortcutResponder()
            }
        }

        @discardableResult
        private func focusShortcutResponder() -> Bool {
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

        private func focusShortcutItem(_ hostView: KeyCommandHostView) {
            hostView.setNeedsFocusUpdate()
            if let focusSystem = hostView.window?.windowScene?.focusSystem {
                focusSystem.requestFocusUpdate(to: hostView)
                focusSystem.updateFocusIfNeeded()
            } else {
                hostView.updateFocusIfNeeded()
            }
        }

        // MARK: - Hardware Keyboard Fallback

        private enum ShortcutDispatch: Hashable, CustomStringConvertible {
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
                }
            }
        }

        private var hardwareKeyboardInput: GCKeyboardInput?
        private var hardwareKeyboardObserverTokens: [NSObjectProtocol] = []
        private var gcLeftControlDown = false
        private var gcRightControlDown = false
        private var gcLeftShiftDown = false
        private var gcRightShiftDown = false
        private var gcLeftAltDown = false
        private var gcRightAltDown = false
        private static weak var activeHardwareKeyboardController: KeyCommandController?

        private var gcControlDown: Bool { gcLeftControlDown || gcRightControlDown }
        private var gcShiftDown: Bool { gcLeftShiftDown || gcRightShiftDown }
        private var gcAltDown: Bool { gcLeftAltDown || gcRightAltDown }

        private func installHardwareKeyboardFallback() {
            attachHardwareKeyboardIfAvailable()
            guard hardwareKeyboardObserverTokens.isEmpty else { return }
            let center = NotificationCenter.default
            let connect = center.addObserver(
                forName: NSNotification.Name.GCKeyboardDidConnect,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                self?.attachHardwareKeyboardIfAvailable()
            }
            let disconnect = center.addObserver(
                forName: NSNotification.Name.GCKeyboardDidDisconnect,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                self?.detachHardwareKeyboard()
                self?.attachHardwareKeyboardIfAvailable()
            }
            hardwareKeyboardObserverTokens.append(connect)
            hardwareKeyboardObserverTokens.append(disconnect)
        }

        private func removeHardwareKeyboardFallback() {
            detachHardwareKeyboard()
            cancelPendingUIKitFallbacks()
            for token in hardwareKeyboardObserverTokens {
                NotificationCenter.default.removeObserver(token)
            }
            hardwareKeyboardObserverTokens.removeAll()
        }

        private func attachHardwareKeyboardIfAvailable() {
            guard let input = GCKeyboard.coalesced?.keyboardInput else { return }
            guard hardwareKeyboardInput !== input || Self.activeHardwareKeyboardController !== self else {
                return
            }
            hardwareKeyboardInput?.keyChangedHandler = nil
            hardwareKeyboardInput = input
            Self.activeHardwareKeyboardController = self
            input.keyChangedHandler = { [weak self] _, _, keyCode, pressed in
                DispatchQueue.main.async {
                    guard let self, Self.activeHardwareKeyboardController === self else { return }
                    self.handleHardwareKeyboardKey(keyCode, pressed: pressed)
                }
            }
            #if DEBUG
            keyboardShortcutDebugLog("[KeyboardShortcut] GameController attached owner=\(ObjectIdentifier(self))")
            #endif
        }

        private func detachHardwareKeyboard() {
            if Self.activeHardwareKeyboardController === self {
                hardwareKeyboardInput?.keyChangedHandler = nil
                Self.activeHardwareKeyboardController = nil
                #if DEBUG
                keyboardShortcutDebugLog("[KeyboardShortcut] GameController detached owner=\(ObjectIdentifier(self))")
                #endif
            }
            hardwareKeyboardInput = nil
            gcLeftControlDown = false
            gcRightControlDown = false
            gcLeftShiftDown = false
            gcRightShiftDown = false
            gcLeftAltDown = false
            gcRightAltDown = false
            if isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
        }

        func refreshHardwareKeyboardFallback() {
            // Hardware keyboard events are owned by PlayerKeyboardShortcutBroker.
            // This method remains as a harmless update hook for older call sites.
            let actions = PlayerKeyboardShortcutActions(
                playPause: { [weak self] in
                    self?.dispatchShortcut(.playPause, source: "broker") { [weak self] in
                        self?.onPlayPause?()
                    }
                },
                previous: { [weak self] in
                    self?.dispatchShortcut(.previous, source: "broker") { [weak self] in
                        self?.onPrevious?()
                    }
                },
                next: { [weak self] in
                    self?.dispatchShortcut(.next, source: "broker") { [weak self] in
                        self?.onNext?()
                    }
                },
                previousSentence: { [weak self] in
                    self?.dispatchShortcut(.previousSentence, source: "broker") { [weak self] in
                        self?.onPreviousSentence?()
                    }
                },
                nextSentence: { [weak self] in
                    self?.dispatchShortcut(.nextSentence, source: "broker") { [weak self] in
                        self?.onNextSentence?()
                    }
                },
                lookup: { [weak self] in
                    self?.dispatchShortcut(.lookup, source: "broker") { [weak self] in
                        self?.onLookup?()
                    }
                },
                showMenu: { [weak self] in
                    self?.dispatchShortcut(.showMenu, source: "broker") { [weak self] in
                        self?.onShowMenu?()
                    }
                },
                hideMenu: { [weak self] in
                    self?.dispatchShortcut(.hideMenu, source: "broker") { [weak self] in
                        self?.onHideMenu?()
                    }
                }
            )
            PlayerKeyboardShortcutBroker.shared.setActions(actions, owner: self)
        }

        private func handleHardwareKeyboardKey(_ keyCode: GCKeyCode, pressed: Bool) {
            if updateHardwareModifier(keyCode, pressed: pressed) {
                return
            }
            guard pressed else { return }
            #if DEBUG
            if isTrackedHardwareShortcutKey(keyCode) {
                keyboardShortcutDebugLog(
                    "[KeyboardShortcut] GameController keyDown code=\(keyCode.rawValue) " +
                    "ctrl=\(gcControlDown) shift=\(gcShiftDown) alt=\(gcAltDown)"
                )
            }
            #endif
            if let blockReason = hardwareKeyboardShortcutBlockReason(
                allowingTextInput: allowsTransportShortcutThroughTextInput(keyCode)
            ) {
                #if DEBUG
                if isTrackedHardwareShortcutKey(keyCode) {
                    keyboardShortcutDebugLog("[KeyboardShortcut] GameController ignored code=\(keyCode.rawValue) reason=\(blockReason)")
                }
                #endif
                return
            }

            let controlDown = gcControlDown
            let shiftDown = gcShiftDown
            switch keyCode {
            case .spacebar:
                dispatchShortcut(.playPause, source: "gc") { self.onPlayPause?() }
            case .leftArrow:
                if shiftDown {
                    dispatchShortcut(.extendSelectionBackward, source: "gc") { self.onExtendSelectionBackward?() }
                } else if controlDown {
                    dispatchShortcut(.previousSentence, source: "gc") { self.onPreviousSentence?() }
                } else {
                    dispatchShortcut(.previous, source: "gc") { self.onPrevious?() }
                }
            case .rightArrow:
                if shiftDown {
                    dispatchShortcut(.extendSelectionForward, source: "gc") { self.onExtendSelectionForward?() }
                } else if controlDown {
                    dispatchShortcut(.nextSentence, source: "gc") { self.onNextSentence?() }
                } else {
                    dispatchShortcut(.next, source: "gc") { self.onNext?() }
                }
            case .returnOrEnter, .keypadEnter:
                dispatchShortcut(.lookup, source: "gc") { self.onLookup?() }
            case .downArrow:
                dispatchShortcut(.showMenu, source: "gc") { self.onShowMenu?() }
            case .upArrow:
                dispatchShortcut(.hideMenu, source: "gc") { self.onHideMenu?() }
            case .keyH:
                if shiftDown {
                    dispatchShortcut(.toggleHeader, source: "gc") { self.onToggleHeader?() }
                } else {
                    dispatchShortcut(.toggleShortcutHelp, source: "gc") { self.onToggleShortcutHelp?() }
                }
            case .keyO:
                if shiftDown {
                    dispatchShortcut(.toggleOriginalAudio, source: "gc") { self.onToggleOriginalAudio?() }
                } else {
                    dispatchShortcut(.toggleOriginal, source: "gc") { self.onToggleOriginal?() }
                }
            case .keyI:
                if shiftDown {
                    dispatchShortcut(.toggleReadingBed, source: "gc") { self.onToggleReadingBed?() }
                } else {
                    dispatchShortcut(.toggleTransliteration, source: "gc") { self.onToggleTransliteration?() }
                }
            case .keyP:
                if shiftDown {
                    dispatchShortcut(.toggleTranslationAudio, source: "gc") { self.onToggleTranslationAudio?() }
                } else {
                    dispatchShortcut(.toggleTranslation, source: "gc") { self.onToggleTranslation?() }
                }
            case .equalSign, .keypadEqualSign, .keypadPlus:
                if controlDown {
                    dispatchShortcut(.increaseLinguistFont, source: "gc") { self.onIncreaseLinguistFont?() }
                } else if shiftDown {
                    dispatchShortcut(.increaseHeaderScale, source: "gc") { self.onIncreaseHeaderScale?() }
                } else {
                    dispatchShortcut(.increaseFont, source: "gc") { self.onIncreaseFont?() }
                }
            case .hyphen, .keypadHyphen:
                if controlDown {
                    dispatchShortcut(.decreaseLinguistFont, source: "gc") { self.onDecreaseLinguistFont?() }
                } else if shiftDown {
                    dispatchShortcut(.decreaseHeaderScale, source: "gc") { self.onDecreaseHeaderScale?() }
                } else {
                    dispatchShortcut(.decreaseFont, source: "gc") { self.onDecreaseFont?() }
                }
            default:
                break
            }
        }

        private func isTrackedHardwareShortcutKey(_ keyCode: GCKeyCode) -> Bool {
            switch keyCode {
            case .spacebar, .leftArrow, .rightArrow, .returnOrEnter, .keypadEnter,
                    .downArrow, .upArrow, .keyH, .keyO, .keyI, .keyP,
                    .equalSign, .keypadEqualSign, .keypadPlus, .hyphen, .keypadHyphen:
                return true
            default:
                return false
            }
        }

        private func updateHardwareModifier(_ keyCode: GCKeyCode, pressed: Bool) -> Bool {
            switch keyCode {
            case .leftControl:
                gcLeftControlDown = pressed
            case .rightControl:
                gcRightControlDown = pressed
            case .leftShift:
                gcLeftShiftDown = pressed
            case .rightShift:
                gcRightShiftDown = pressed
            case .leftAlt:
                gcLeftAltDown = pressed
                handleHardwareOptionStateChange()
            case .rightAlt:
                gcRightAltDown = pressed
                handleHardwareOptionStateChange()
            default:
                return false
            }
            return true
        }

        private func handleHardwareOptionStateChange() {
            if gcAltDown, !isOptionKeyDown {
                isOptionKeyDown = true
                onOptionKeyDown?()
            } else if !gcAltDown, isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
        }

        private var hardwareKeyboardShortcutBlockReason: String? {
            hardwareKeyboardShortcutBlockReason(allowingTextInput: false)
        }

        private func hardwareKeyboardShortcutBlockReason(allowingTextInput: Bool) -> String? {
            guard UIApplication.shared.applicationState == .active else { return "app inactive" }
            guard view.window != nil else { return "controller not in window" }
            if !allowingTextInput, let responder = textInputFirstResponder() {
                return "text input first responder: \(type(of: responder))"
            }
            return nil
        }

        private func allowsTransportShortcutThroughTextInput(_ keyCode: GCKeyCode) -> Bool {
            switch keyCode {
            case .spacebar, .leftArrow, .rightArrow, .returnOrEnter, .keypadEnter,
                    .downArrow, .upArrow:
                return true
            default:
                return false
            }
        }

        private func textInputFirstResponder() -> UIResponder? {
            guard let responder = UIResponder.interactiveReaderCurrentFirstResponder else {
                return nil
            }
            if responder is UITextField || responder is UITextView || responder is UISearchBar {
                return responder
            }
            return nil
        }

        private func dispatchShortcut(
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

        private func cancelPendingUIKitFallbacks() {
            for fallback in pendingUIKitFallbacks.values {
                fallback.cancel()
            }
            pendingUIKitFallbacks.removeAll()
        }

        override var keyCommands: [UIKeyCommand]? {
            let commands = [
                makeCommand(input: " ", action: #selector(handlePlayPause)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, action: #selector(handlePrevious)),
                makeCommand(input: UIKeyCommand.inputRightArrow, action: #selector(handleNext)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, modifiers: [.control], action: #selector(handlePreviousWord)),
                makeCommand(input: UIKeyCommand.inputRightArrow, modifiers: [.control], action: #selector(handleNextWord)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, modifiers: [.shift], action: #selector(handleExtendSelectionBackward)),
                makeCommand(input: UIKeyCommand.inputRightArrow, modifiers: [.shift], action: #selector(handleExtendSelectionForward)),
                makeCommand(input: "\r", action: #selector(handleLookup)),
                makeCommand(input: "\n", action: #selector(handleLookup)),
                makeCommand(input: UIKeyCommand.inputDownArrow, action: #selector(handleShowMenu)),
                makeCommand(input: UIKeyCommand.inputUpArrow, action: #selector(handleHideMenu)),
                makeCommand(input: "h", action: #selector(handleToggleHelp)),
                makeCommand(input: "h", modifiers: [.shift], action: #selector(handleToggleHeader)),
                makeCommand(input: "o", action: #selector(handleToggleOriginal)),
                makeCommand(input: "o", modifiers: [.shift], action: #selector(handleToggleOriginalAudio)),
                makeCommand(input: "i", action: #selector(handleToggleTransliteration)),
                makeCommand(input: "i", modifiers: [.shift], action: #selector(handleToggleReadingBed)),
                makeCommand(input: "p", action: #selector(handleToggleTranslation)),
                makeCommand(input: "p", modifiers: [.shift], action: #selector(handleToggleTranslationAudio)),
                makeCommand(input: "=", modifiers: [.control], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "=", modifiers: [.control, .shift], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "+", modifiers: [.control], action: #selector(handleIncreaseLinguistFont)),
                makeCommand(input: "-", modifiers: [.control], action: #selector(handleDecreaseLinguistFont)),
                makeCommand(input: "=", modifiers: [.shift], action: #selector(handleIncreaseHeaderScale)),
                makeCommand(input: "+", modifiers: [.shift], action: #selector(handleIncreaseHeaderScale)),
                makeCommand(input: "-", modifiers: [.shift], action: #selector(handleDecreaseHeaderScale)),
                makeCommand(input: "_", modifiers: [.shift], action: #selector(handleDecreaseHeaderScale)),
                makeCommand(input: "=", modifiers: [], action: #selector(handleIncreaseFont)),
                makeCommand(input: "+", modifiers: [], action: #selector(handleIncreaseFont)),
                makeCommand(input: "-", modifiers: [], action: #selector(handleDecreaseFont)),
            ]
            return commands
        }

        @objc private func handlePlayPause() {
            dispatchShortcut(.playPause, source: "ui") { self.onPlayPause?() }
        }

        @objc private func handlePrevious() {
            dispatchShortcut(.previous, source: "ui") { self.onPrevious?() }
        }

        @objc private func handleNext() {
            dispatchShortcut(.next, source: "ui") { self.onNext?() }
        }

        @objc private func handlePreviousWord() {
            // Ctrl+Left: sentence navigation when paused, word navigation when playing
            dispatchShortcut(.previousSentence, source: "ui") { self.onPreviousSentence?() }
        }

        @objc private func handleNextWord() {
            // Ctrl+Right: sentence navigation when paused, word navigation when playing
            dispatchShortcut(.nextSentence, source: "ui") { self.onNextSentence?() }
        }

        @objc private func handleExtendSelectionBackward() {
            dispatchShortcut(.extendSelectionBackward, source: "ui") { self.onExtendSelectionBackward?() }
        }

        @objc private func handleExtendSelectionForward() {
            dispatchShortcut(.extendSelectionForward, source: "ui") { self.onExtendSelectionForward?() }
        }

        @objc private func handleLookup() {
            dispatchShortcut(.lookup, source: "ui") { self.onLookup?() }
        }

        @objc private func handleIncreaseFont() {
            dispatchShortcut(.increaseFont, source: "ui") { self.onIncreaseFont?() }
        }

        @objc private func handleDecreaseFont() {
            dispatchShortcut(.decreaseFont, source: "ui") { self.onDecreaseFont?() }
        }

        @objc private func handleToggleOriginal() {
            dispatchShortcut(.toggleOriginal, source: "ui") { self.onToggleOriginal?() }
        }

        @objc private func handleToggleTransliteration() {
            dispatchShortcut(.toggleTransliteration, source: "ui") { self.onToggleTransliteration?() }
        }

        @objc private func handleToggleTranslation() {
            dispatchShortcut(.toggleTranslation, source: "ui") { self.onToggleTranslation?() }
        }

        @objc private func handleToggleOriginalAudio() {
            dispatchShortcut(.toggleOriginalAudio, source: "ui") { self.onToggleOriginalAudio?() }
        }

        @objc private func handleToggleTranslationAudio() {
            dispatchShortcut(.toggleTranslationAudio, source: "ui") { self.onToggleTranslationAudio?() }
        }

        @objc private func handleToggleReadingBed() {
            dispatchShortcut(.toggleReadingBed, source: "ui") { self.onToggleReadingBed?() }
        }

        @objc private func handleIncreaseLinguistFont() {
            dispatchShortcut(.increaseLinguistFont, source: "ui") { self.onIncreaseLinguistFont?() }
        }

        @objc private func handleDecreaseLinguistFont() {
            dispatchShortcut(.decreaseLinguistFont, source: "ui") { self.onDecreaseLinguistFont?() }
        }

        @objc private func handleToggleHelp() {
            dispatchShortcut(.toggleShortcutHelp, source: "ui") { self.onToggleShortcutHelp?() }
        }

        @objc private func handleToggleHeader() {
            dispatchShortcut(.toggleHeader, source: "ui") { self.onToggleHeader?() }
        }

        @objc private func handleIncreaseHeaderScale() {
            dispatchShortcut(.increaseHeaderScale, source: "ui") { self.onIncreaseHeaderScale?() }
        }

        @objc private func handleDecreaseHeaderScale() {
            dispatchShortcut(.decreaseHeaderScale, source: "ui") { self.onDecreaseHeaderScale?() }
        }

        @objc private func handleShowMenu() {
            dispatchShortcut(.showMenu, source: "ui") { self.onShowMenu?() }
        }

        @objc private func handleHideMenu() {
            dispatchShortcut(.hideMenu, source: "ui") { self.onHideMenu?() }
        }

        override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            let handled = handleHostPressesBegan(presses, with: event)
            if !handled {
                super.pressesBegan(presses, with: event)
            }
        }

        override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            let handled = handleHostPressesEnded(presses, with: event)
            if !handled {
                super.pressesEnded(presses, with: event)
            }
        }

        override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            let handled = handleHostPressesCancelled(presses, with: event)
            if !handled {
                super.pressesCancelled(presses, with: event)
            }
        }

        @discardableResult
        func handleHostPressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) -> Bool {
            var handled = false
            if shouldHandleOptionKey(presses), !isOptionKeyDown {
                isOptionKeyDown = true
                onOptionKeyDown?()
                handled = true
            }
            for press in presses {
                handled = handleRawUIPressShortcut(press) || handled
            }
            return handled
        }

        @discardableResult
        func handleHostPressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) -> Bool {
            guard shouldHandleOptionKey(presses), isOptionKeyDown else {
                return false
            }
            isOptionKeyDown = false
            onOptionKeyUp?()
            return true
        }

        @discardableResult
        func handleHostPressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) -> Bool {
            guard isOptionKeyDown else { return false }
            isOptionKeyDown = false
            onOptionKeyUp?()
            return true
        }

        @discardableResult
        func handleHostInsertedText(_ text: String) -> Bool {
            guard !text.isEmpty else { return false }
            var handled = false
            for character in text {
                switch character {
                case " ":
                    dispatchShortcut(.playPause, source: "input") { self.onPlayPause?() }
                    handled = true
                case "\n", "\r":
                    dispatchShortcut(.lookup, source: "input") { self.onLookup?() }
                    handled = true
                case "h":
                    dispatchShortcut(.toggleShortcutHelp, source: "input") { self.onToggleShortcutHelp?() }
                    handled = true
                case "H":
                    dispatchShortcut(.toggleHeader, source: "input") { self.onToggleHeader?() }
                    handled = true
                case "o":
                    dispatchShortcut(.toggleOriginal, source: "input") { self.onToggleOriginal?() }
                    handled = true
                case "O":
                    dispatchShortcut(.toggleOriginalAudio, source: "input") { self.onToggleOriginalAudio?() }
                    handled = true
                case "i":
                    dispatchShortcut(.toggleTransliteration, source: "input") { self.onToggleTransliteration?() }
                    handled = true
                case "I":
                    dispatchShortcut(.toggleReadingBed, source: "input") { self.onToggleReadingBed?() }
                    handled = true
                case "p":
                    dispatchShortcut(.toggleTranslation, source: "input") { self.onToggleTranslation?() }
                    handled = true
                case "P":
                    dispatchShortcut(.toggleTranslationAudio, source: "input") { self.onToggleTranslationAudio?() }
                    handled = true
                case "=", "+":
                    dispatchShortcut(.increaseFont, source: "input") { self.onIncreaseFont?() }
                    handled = true
                case "-", "_":
                    dispatchShortcut(.decreaseFont, source: "input") { self.onDecreaseFont?() }
                    handled = true
                default:
                    break
                }
            }
            #if DEBUG
            if handled {
                keyboardShortcutDebugLog("[KeyboardShortcut] input handled text=\(String(reflecting: text))")
            }
            #endif
            return handled
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

        private func handleRawUIPressShortcut(_ press: UIPress) -> Bool {
            guard let key = press.key else { return false }
            let isTrackedKey = isTrackedUIPressShortcutKey(key.keyCode)
            if let blockReason = hardwareKeyboardShortcutBlockReason(
                allowingTextInput: allowsTransportShortcutThroughTextInput(key.keyCode)
            ) {
                #if DEBUG
                if isTrackedKey {
                    keyboardShortcutDebugLog("[KeyboardShortcut] UIPress ignored code=\(key.keyCode.rawValue) reason=\(blockReason)")
                }
                #endif
                return isTrackedKey
            }

            #if DEBUG
            if isTrackedKey {
                keyboardShortcutDebugLog(
                    "[KeyboardShortcut] UIPress keyDown code=\(key.keyCode.rawValue) " +
                    "ctrl=\(key.modifierFlags.contains(.control)) " +
                    "shift=\(key.modifierFlags.contains(.shift)) " +
                    "alt=\(key.modifierFlags.contains(.alternate))"
                )
            }
            #endif

            let controlDown = key.modifierFlags.contains(.control)
            let shiftDown = key.modifierFlags.contains(.shift)
            switch key.keyCode {
            case .keyboardSpacebar:
                dispatchShortcut(.playPause, source: "press") { self.onPlayPause?() }
                return true
            case .keyboardLeftArrow:
                if shiftDown {
                    dispatchShortcut(.extendSelectionBackward, source: "press") { self.onExtendSelectionBackward?() }
                } else if controlDown {
                    dispatchShortcut(.previousSentence, source: "press") { self.onPreviousSentence?() }
                } else {
                    dispatchShortcut(.previous, source: "press") { self.onPrevious?() }
                }
                return true
            case .keyboardRightArrow:
                if shiftDown {
                    dispatchShortcut(.extendSelectionForward, source: "press") { self.onExtendSelectionForward?() }
                } else if controlDown {
                    dispatchShortcut(.nextSentence, source: "press") { self.onNextSentence?() }
                } else {
                    dispatchShortcut(.next, source: "press") { self.onNext?() }
                }
                return true
            case .keyboardReturnOrEnter, .keypadEnter, .keyboardReturn:
                dispatchShortcut(.lookup, source: "press") { self.onLookup?() }
                return true
            case .keyboardDownArrow:
                dispatchShortcut(.showMenu, source: "press") { self.onShowMenu?() }
                return true
            case .keyboardUpArrow:
                dispatchShortcut(.hideMenu, source: "press") { self.onHideMenu?() }
                return true
            case .keyboardH:
                if shiftDown {
                    dispatchShortcut(.toggleHeader, source: "press") { self.onToggleHeader?() }
                } else {
                    dispatchShortcut(.toggleShortcutHelp, source: "press") { self.onToggleShortcutHelp?() }
                }
                return true
            case .keyboardO:
                if shiftDown {
                    dispatchShortcut(.toggleOriginalAudio, source: "press") { self.onToggleOriginalAudio?() }
                } else {
                    dispatchShortcut(.toggleOriginal, source: "press") { self.onToggleOriginal?() }
                }
                return true
            case .keyboardI:
                if shiftDown {
                    dispatchShortcut(.toggleReadingBed, source: "press") { self.onToggleReadingBed?() }
                } else {
                    dispatchShortcut(.toggleTransliteration, source: "press") { self.onToggleTransliteration?() }
                }
                return true
            case .keyboardP:
                if shiftDown {
                    dispatchShortcut(.toggleTranslationAudio, source: "press") { self.onToggleTranslationAudio?() }
                } else {
                    dispatchShortcut(.toggleTranslation, source: "press") { self.onToggleTranslation?() }
                }
                return true
            case .keyboardEqualSign, .keypadEqualSign, .keypadPlus:
                if controlDown {
                    dispatchShortcut(.increaseLinguistFont, source: "press") { self.onIncreaseLinguistFont?() }
                } else if shiftDown {
                    dispatchShortcut(.increaseHeaderScale, source: "press") { self.onIncreaseHeaderScale?() }
                } else {
                    dispatchShortcut(.increaseFont, source: "press") { self.onIncreaseFont?() }
                }
                return true
            case .keyboardHyphen, .keypadHyphen:
                if controlDown {
                    dispatchShortcut(.decreaseLinguistFont, source: "press") { self.onDecreaseLinguistFont?() }
                } else if shiftDown {
                    dispatchShortcut(.decreaseHeaderScale, source: "press") { self.onDecreaseHeaderScale?() }
                } else {
                    dispatchShortcut(.decreaseFont, source: "press") { self.onDecreaseFont?() }
                }
                return true
            default:
                return false
            }
        }

        private func isTrackedUIPressShortcutKey(_ keyCode: UIKeyboardHIDUsage) -> Bool {
            switch keyCode {
            case .keyboardSpacebar, .keyboardLeftArrow, .keyboardRightArrow,
                    .keyboardReturnOrEnter, .keypadEnter, .keyboardReturn,
                    .keyboardDownArrow, .keyboardUpArrow, .keyboardH,
                    .keyboardO, .keyboardI, .keyboardP,
                    .keyboardEqualSign, .keypadEqualSign, .keypadPlus,
                    .keyboardHyphen, .keypadHyphen:
                return true
            default:
                return false
            }
        }

        private func allowsTransportShortcutThroughTextInput(_ keyCode: UIKeyboardHIDUsage) -> Bool {
            switch keyCode {
            case .keyboardSpacebar, .keyboardLeftArrow, .keyboardRightArrow,
                    .keyboardReturnOrEnter, .keypadEnter, .keyboardReturn,
                    .keyboardDownArrow, .keyboardUpArrow:
                return true
            default:
                return false
            }
        }

        private class KeyCommandHostView: UITextField {
            weak var controller: KeyCommandController?
            private var hasLoggedFocus = false
            private let hiddenInputView = UIView(frame: .zero)

            override init(frame: CGRect) {
                super.init(frame: frame)
                configureInputCapture()
            }

            required init?(coder: NSCoder) {
                super.init(coder: coder)
                configureInputCapture()
            }

            private func configureInputCapture() {
                isUserInteractionEnabled = true
                hiddenInputView.backgroundColor = .clear
                backgroundColor = .clear
                borderStyle = .none
                textColor = .clear
                tintColor = .clear
                autocorrectionType = .no
                autocapitalizationType = .none
                spellCheckingType = .no
                smartDashesType = .no
                smartQuotesType = .no
                smartInsertDeleteType = .no
                inputView = hiddenInputView
                inputAssistantItem.leadingBarButtonGroups = []
                inputAssistantItem.trailingBarButtonGroups = []
            }

            override var canBecomeFirstResponder: Bool {
                true
            }

            override var canBecomeFocused: Bool {
                true
            }

            override var focusEffect: UIFocusEffect? {
                get { nil }
                set { }
            }

            override var keyCommands: [UIKeyCommand]? {
                controller?.keyCommands
            }

            override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
                bounds.contains(point)
            }

            override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
                nil
            }

            override func insertText(_ text: String) {
                _ = controller?.handleHostInsertedText(text)
                self.text = ""
            }

            override func deleteBackward() {
                self.text = ""
            }

            override func didMoveToWindow() {
                super.didMoveToWindow()
                guard window != nil else { return }
                DispatchQueue.main.async { [weak self] in
                    guard let self else { return }
                    _ = becomeFirstResponder()
                    #if DEBUG
                    logFocusClaimIfNeeded()
                    #endif
                }
            }

            override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
                guard controller?.handleHostPressesBegan(presses, with: event) == true else {
                    super.pressesBegan(presses, with: event)
                    return
                }
            }

            override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
                guard controller?.handleHostPressesEnded(presses, with: event) == true else {
                    super.pressesEnded(presses, with: event)
                    return
                }
            }

            override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
                guard controller?.handleHostPressesCancelled(presses, with: event) == true else {
                    super.pressesCancelled(presses, with: event)
                    return
                }
            }

            #if DEBUG
            func logFocusClaimIfNeeded() {
                guard isFirstResponder, !hasLoggedFocus else { return }
                hasLoggedFocus = true
                keyboardShortcutDebugLog("[KeyboardShortcut] Key command host became first responder")
            }
            #endif
        }

        @available(iOS 18.0, *)
        private final class DeferralSafeKeyCommandHostView: KeyCommandHostView {
            override var focusItemDeferralMode: UIFocusItemDeferralMode {
                .never
            }
        }
    }
}

/// Gesture recognizer that observes every touches-ended without consuming
/// the touch. Attached to the key window so the shortcut controller can
/// snap first responder back after any user tap (Play button, lookup
/// bubble, transcript, sheet dismissal). Always reports `.failed` so no
/// other gesture is disturbed.
import UIKit.UIGestureRecognizerSubclass

final class WindowTouchCatcher: UIGestureRecognizer {
    var onTouchesEnded: (() -> Void)?

    override init(target: Any?, action: Selector?) {
        super.init(target: target, action: action)
        cancelsTouchesInView = false
        delaysTouchesBegan = false
        delaysTouchesEnded = false
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        super.touchesBegan(touches, with: event)
        state = .possible
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) {
        super.touchesEnded(touches, with: event)
        onTouchesEnded?()
        state = .failed
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) {
        super.touchesCancelled(touches, with: event)
        state = .failed
    }
}

private weak var interactiveReaderCapturedFirstResponder: UIResponder?

private extension UIResponder {
    static var interactiveReaderCurrentFirstResponder: UIResponder? {
        interactiveReaderCapturedFirstResponder = nil
        UIApplication.shared.sendAction(
            #selector(captureInteractiveReaderFirstResponder),
            to: nil,
            from: nil,
            for: nil
        )
        return interactiveReaderCapturedFirstResponder
    }

    @objc func captureInteractiveReaderFirstResponder() {
        interactiveReaderCapturedFirstResponder = self
    }
}

#endif
