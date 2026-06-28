import Foundation
#if os(iOS) || os(tvOS)
import GameController
import ObjectiveC.runtime
import OSLog
import UIKit
#endif

#if os(iOS) || os(tvOS)
func keyboardShortcutDebugLog(_ message: @autoclosure () -> String) {
    #if DEBUG
    KeyboardShortcutDebugLogger.shared.log(message())
    #else
    _ = message
    #endif
}

func resetKeyboardShortcutDebugLog() {
    #if DEBUG
    KeyboardShortcutDebugLogger.shared.reset()
    #endif
}

#if DEBUG
private final class KeyboardShortcutDebugLogger {
    static let shared = KeyboardShortcutDebugLogger()

    private let queue = DispatchQueue(label: "com.interactivereader.keyboard-debug-log")
    private let logger = Logger(subsystem: "InteractiveReader", category: "KeyboardShortcuts")
    private let fileURL: URL?
    private var didPrepareFile = false

    private init() {
        fileURL = FileManager.default
            .urls(for: .cachesDirectory, in: .userDomainMask)
            .first?
            .appendingPathComponent("interactive-reader-keyboard.log")
    }

    func reset() {
        queue.async { [fileURL] in
            guard let fileURL else { return }
            try? FileManager.default.removeItem(at: fileURL)
            FileManager.default.createFile(atPath: fileURL.path, contents: nil)
            self.didPrepareFile = true
        }
    }

    func log(_ message: String) {
        logger.debug("\(message, privacy: .private)")
        queue.async { [fileURL] in
            guard let fileURL else { return }
            if !self.didPrepareFile {
                self.prepareFileIfNeeded(fileURL)
            }
            let timestamp = String(format: "%.3f", Date().timeIntervalSince1970)
            let line = "\(timestamp) \(message)\n"
            guard let data = line.data(using: .utf8) else { return }
            if !FileManager.default.fileExists(atPath: fileURL.path) {
                FileManager.default.createFile(atPath: fileURL.path, contents: nil)
            }
            guard let handle = try? FileHandle(forWritingTo: fileURL) else { return }
            handle.seekToEndOfFile()
            handle.write(data)
            try? handle.close()
        }
    }

    private func prepareFileIfNeeded(_ fileURL: URL) {
        defer { didPrepareFile = true }
        guard
            let attributes = try? FileManager.default.attributesOfItem(atPath: fileURL.path),
            let size = attributes[.size] as? NSNumber,
            size.intValue > 512_000
        else {
            return
        }
        try? FileManager.default.removeItem(at: fileURL)
        FileManager.default.createFile(atPath: fileURL.path, contents: nil)
    }
}
#endif
#else
func keyboardShortcutDebugLog(_ message: @autoclosure () -> String) {
    _ = message
}

func resetKeyboardShortcutDebugLog() {}
#endif

/// Notification names for app-level keyboard shortcuts.
///
/// Shortcuts are registered by the SwiftUI scene via `.commands`, then
/// forwarded through notifications so the active player can decide how to
/// handle them. This complements the player-local UIKit hardware-key path,
/// the app-level `UIApplication.sendEvent` press interceptor, and the
/// GameController broker below.
///
/// Using notifications rather than a dedicated first-responder controller
/// sidesteps the recurring problem where SwiftUI Buttons / ScrollViews
/// take first responder away from us after user interaction, leaving
/// Space/arrows silently dead until the next tap.
extension Notification.Name {
    static let keyboardShortcutPlayPause = Notification.Name(
        "com.interactivereader.keyboard.playPause"
    )
    static let keyboardShortcutPrevious = Notification.Name(
        "com.interactivereader.keyboard.previous"
    )
    static let keyboardShortcutNext = Notification.Name(
        "com.interactivereader.keyboard.next"
    )
    static let keyboardShortcutPreviousSentence = Notification.Name(
        "com.interactivereader.keyboard.previousSentence"
    )
    static let keyboardShortcutNextSentence = Notification.Name(
        "com.interactivereader.keyboard.nextSentence"
    )
    static let keyboardShortcutLookup = Notification.Name(
        "com.interactivereader.keyboard.lookup"
    )
    static let keyboardShortcutShowMenu = Notification.Name(
        "com.interactivereader.keyboard.showMenu"
    )
    static let keyboardShortcutHideMenu = Notification.Name(
        "com.interactivereader.keyboard.hideMenu"
    )
    static let keyboardShortcutReclaimFocus = Notification.Name(
        "com.interactivereader.keyboard.reclaimFocus"
    )
}

#if os(iOS) || os(tvOS)
@MainActor
struct PlayerKeyboardShortcutActions {
    var playPause: () -> Void
    var previous: () -> Void
    var next: () -> Void
    var previousSentence: () -> Void
    var nextSentence: () -> Void
    var lookup: () -> Void
    var showMenu: () -> Void
    var hideMenu: () -> Void
    var shouldNavigateBubbleWords: () -> Bool = { false }
    var bubbleNavigateLeft: (() -> Void)?
    var bubbleNavigateRight: (() -> Void)?
}

@MainActor
final class PlayerKeyboardShortcutBroker {
    static let shared = PlayerKeyboardShortcutBroker()

    private var isActive = false
    private var actions: PlayerKeyboardShortcutActions?
    private weak var actionsOwner: AnyObject?
    private var keyboardInput: GCKeyboardInput?
    private var observerTokens: [NSObjectProtocol] = []
    private var leftControlDown = false
    private var rightControlDown = false
    private var leftShiftDown = false
    private var rightShiftDown = false
    private var lastDispatch: (name: Notification.Name, timestamp: TimeInterval)?

    private var controlDown: Bool { leftControlDown || rightControlDown }
    private var shiftDown: Bool { leftShiftDown || rightShiftDown }

    private init() {}

    func setActions(_ actions: PlayerKeyboardShortcutActions, owner: AnyObject) {
        let ownerChanged = actionsOwner !== owner
        self.actions = actions
        actionsOwner = owner
        if !isActive {
            setActive(true)
        }
        #if DEBUG
        if ownerChanged {
            keyboardShortcutDebugLog("[KeyboardShortcut] App broker registered player actions owner=\(ObjectIdentifier(owner))")
        }
        #endif
    }

    func clearActions(owner: AnyObject) {
        guard actionsOwner === owner else { return }
        actions = nil
        actionsOwner = nil
        #if DEBUG
        keyboardShortcutDebugLog("[KeyboardShortcut] App broker cleared player actions owner=\(ObjectIdentifier(owner))")
        #endif
    }

    func setActive(_ active: Bool) {
        guard isActive != active else {
            if active {
                attachKeyboardIfAvailable()
            }
            return
        }
        isActive = active
        if active {
            resetDispatchDebounce()
            installObservers()
            attachKeyboardIfAvailable()
        } else {
            removeObservers()
            detachKeyboard()
        }
    }

    func resetDispatchDebounce() {
        lastDispatch = nil
    }

    func resetModifierState() {
        leftControlDown = false
        rightControlDown = false
        leftShiftDown = false
        rightShiftDown = false
    }

    func handleApplicationEvent(_ event: UIEvent) {
        guard isActive else { return }
        guard let pressesEvent = event as? UIPressesEvent else { return }
        for press in pressesEvent.allPresses {
            guard let key = press.key else {
                if press.phase == .began {
                    handleRemotePress(press)
                }
                continue
            }
            switch press.phase {
            case .began, .changed, .stationary:
                if updateModifier(key.keyCode, pressed: true) {
                    continue
                }
                if press.phase == .began {
                    handlePress(press)
                }
            case .ended, .cancelled:
                _ = updateModifier(key.keyCode, pressed: false)
            @unknown default:
                break
            }
        }
    }

    @discardableResult
    func handleCommandIfActive(_ name: Notification.Name) -> Bool {
        guard isActive else { return false }
        post(name)
        return true
    }

    func handleCommand(_ name: Notification.Name) {
        _ = handleCommandIfActive(name)
    }

    private func installObservers() {
        guard observerTokens.isEmpty else { return }
        let center = NotificationCenter.default
        let connect = center.addObserver(
            forName: NSNotification.Name.GCKeyboardDidConnect,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.attachKeyboardIfAvailable() }
        }
        let disconnect = center.addObserver(
            forName: NSNotification.Name.GCKeyboardDidDisconnect,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.detachKeyboard()
                self?.attachKeyboardIfAvailable()
            }
        }
        observerTokens = [connect, disconnect]
    }

    private func removeObservers() {
        for token in observerTokens {
            NotificationCenter.default.removeObserver(token)
        }
        observerTokens.removeAll()
    }

    private func attachKeyboardIfAvailable() {
        guard isActive else { return }
        guard let input = GCKeyboard.coalesced?.keyboardInput else { return }
        guard keyboardInput !== input else { return }
        keyboardInput?.keyChangedHandler = nil
        keyboardInput = input
        input.keyChangedHandler = { [weak self] _, _, keyCode, pressed in
            Task { @MainActor in
                self?.handleKey(keyCode, pressed: pressed)
            }
        }
        #if DEBUG
        keyboardShortcutDebugLog("[KeyboardShortcut] App broker attached GameController keyboard")
        #endif
    }

    private func detachKeyboard() {
        keyboardInput?.keyChangedHandler = nil
        keyboardInput = nil
        leftControlDown = false
        rightControlDown = false
        leftShiftDown = false
        rightShiftDown = false
        #if DEBUG
        keyboardShortcutDebugLog("[KeyboardShortcut] App broker detached GameController keyboard")
        #endif
    }

    private func handleKey(_ keyCode: GCKeyCode, pressed: Bool) {
        guard isActive else { return }
        if updateModifier(keyCode, pressed: pressed) {
            return
        }
        guard pressed else { return }
        refreshModifierStateFromKeyboardInput()

        #if DEBUG
        if isTrackedKey(keyCode) {
            keyboardShortcutDebugLog(
                "[KeyboardShortcut] App broker keyDown code=\(keyCode.rawValue) " +
                "ctrl=\(controlDown) shift=\(shiftDown)"
            )
        }
        #endif

        let textResponder = textInputFirstResponder()
        if let responder = textResponder,
           !allowsTransportShortcutThroughTextInput(keyCode) {
            #if DEBUG
            if isTrackedKey(keyCode) {
                keyboardShortcutDebugLog("[KeyboardShortcut] App broker ignored code=\(keyCode.rawValue) text input first responder=\(type(of: responder))")
            }
            #endif
            return
        } else if let responder = textResponder {
            #if DEBUG
            if isTrackedKey(keyCode) {
                keyboardShortcutDebugLog("[KeyboardShortcut] App broker bypassed text input first responder=\(type(of: responder)) for code=\(keyCode.rawValue)")
            }
            #endif
        }

        switch keyCode {
        case .spacebar:
            post(.keyboardShortcutPlayPause)
        case .leftArrow:
            post(controlDown ? .keyboardShortcutPreviousSentence : .keyboardShortcutPrevious)
        case .rightArrow:
            post(controlDown ? .keyboardShortcutNextSentence : .keyboardShortcutNext)
        case .returnOrEnter, .keypadEnter:
            post(.keyboardShortcutLookup)
        case .downArrow:
            post(.keyboardShortcutShowMenu)
        case .upArrow:
            post(.keyboardShortcutHideMenu)
        default:
            break
        }
    }

    private func refreshModifierStateFromKeyboardInput() {
        guard let keyboardInput else { return }
        leftControlDown = keyboardInput.button(forKeyCode: .leftControl)?.isPressed == true
        rightControlDown = keyboardInput.button(forKeyCode: .rightControl)?.isPressed == true
        leftShiftDown = keyboardInput.button(forKeyCode: .leftShift)?.isPressed == true
        rightShiftDown = keyboardInput.button(forKeyCode: .rightShift)?.isPressed == true
    }

    private func handlePress(_ press: UIPress) {
        guard let key = press.key else { return }
        guard isTrackedPressKey(key.keyCode) else { return }
        syncModifierState(from: key.modifierFlags)

        #if DEBUG
        keyboardShortcutDebugLog(
            "[KeyboardShortcut] App event keyDown code=\(key.keyCode.rawValue) " +
            "ctrl=\(key.modifierFlags.contains(.control)) " +
            "shift=\(key.modifierFlags.contains(.shift))"
        )
        #endif

        let textResponder = textInputFirstResponder()
        if let responder = textResponder,
           !allowsTransportShortcutThroughTextInput(key.keyCode) {
            #if DEBUG
            keyboardShortcutDebugLog("[KeyboardShortcut] App event ignored code=\(key.keyCode.rawValue) text input first responder=\(type(of: responder))")
            #endif
            return
        } else if let responder = textResponder {
            #if DEBUG
            keyboardShortcutDebugLog("[KeyboardShortcut] App event bypassed text input first responder=\(type(of: responder)) for code=\(key.keyCode.rawValue)")
            #endif
        }

        let controlDown = resolvedControlModifierState(for: key)
        switch key.keyCode {
        case .keyboardSpacebar:
            post(.keyboardShortcutPlayPause)
        case .keyboardLeftArrow:
            post(controlDown ? .keyboardShortcutPreviousSentence : .keyboardShortcutPrevious)
        case .keyboardRightArrow:
            post(controlDown ? .keyboardShortcutNextSentence : .keyboardShortcutNext)
        case .keyboardReturnOrEnter, .keypadEnter, .keyboardReturn:
            post(.keyboardShortcutLookup)
        case .keyboardDownArrow:
            post(.keyboardShortcutShowMenu)
        case .keyboardUpArrow:
            post(.keyboardShortcutHideMenu)
        default:
            break
        }
    }

    private func handleRemotePress(_ press: UIPress) {
        #if os(tvOS)
        switch press.type {
        case .playPause:
            keyboardShortcutDebugLog("[KeyboardShortcut] App event remote playPause")
            post(.keyboardShortcutPlayPause)
        default:
            break
        }
        #endif
    }

    private func updateModifier(_ keyCode: GCKeyCode, pressed: Bool) -> Bool {
        switch keyCode {
        case .leftControl:
            leftControlDown = pressed
        case .rightControl:
            rightControlDown = pressed
        case .leftShift:
            leftShiftDown = pressed
        case .rightShift:
            rightShiftDown = pressed
        default:
            return false
        }
        return true
    }

    private func updateModifier(_ keyCode: UIKeyboardHIDUsage, pressed: Bool) -> Bool {
        switch keyCode {
        case .keyboardLeftControl:
            leftControlDown = pressed
        case .keyboardRightControl:
            rightControlDown = pressed
        case .keyboardLeftShift:
            leftShiftDown = pressed
        case .keyboardRightShift:
            rightShiftDown = pressed
        default:
            return false
        }
        return true
    }

    private func syncModifierState(from flags: UIKeyModifierFlags) {
        if !flags.contains(.control) {
            leftControlDown = false
            rightControlDown = false
        }
        if !flags.contains(.shift) {
            leftShiftDown = false
            rightShiftDown = false
        }
    }

    private func resolvedControlModifierState(for key: UIKey) -> Bool {
        if keyboardInput != nil {
            refreshModifierStateFromKeyboardInput()
            return controlDown
        }
        return key.modifierFlags.contains(.control)
    }

    private func isTrackedKey(_ keyCode: GCKeyCode) -> Bool {
        switch keyCode {
        case .spacebar, .leftArrow, .rightArrow, .returnOrEnter,
                .keypadEnter, .downArrow, .upArrow:
            return true
        default:
            return false
        }
    }

    private func allowsTransportShortcutThroughTextInput(_ keyCode: GCKeyCode) -> Bool {
        switch keyCode {
        case .spacebar, .leftArrow, .rightArrow, .returnOrEnter,
                .keypadEnter, .downArrow, .upArrow:
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

    private func isTrackedPressKey(_ keyCode: UIKeyboardHIDUsage) -> Bool {
        switch keyCode {
        case .keyboardSpacebar, .keyboardLeftArrow, .keyboardRightArrow,
                .keyboardReturnOrEnter, .keypadEnter, .keyboardReturn,
                .keyboardDownArrow, .keyboardUpArrow:
            return true
        default:
            return false
        }
    }

    private func post(_ name: Notification.Name) {
        let now = ProcessInfo.processInfo.systemUptime
        if let lastDispatch,
           lastDispatch.name == name,
           now - lastDispatch.timestamp < 0.12 {
            return
        }
        lastDispatch = (name, now)
        if invokeRegisteredAction(for: name) {
            return
        }
        NotificationCenter.default.post(name: name, object: self)
    }

    private func invokeRegisteredAction(for name: Notification.Name) -> Bool {
        guard let actions else { return false }
        switch name {
        case .keyboardShortcutPlayPause:
            actions.playPause()
        case .keyboardShortcutPrevious:
            if actions.shouldNavigateBubbleWords(), let bubbleNavigateLeft = actions.bubbleNavigateLeft {
                bubbleNavigateLeft()
            } else {
                actions.previous()
            }
        case .keyboardShortcutNext:
            if actions.shouldNavigateBubbleWords(), let bubbleNavigateRight = actions.bubbleNavigateRight {
                bubbleNavigateRight()
            } else {
                actions.next()
            }
        case .keyboardShortcutPreviousSentence:
            actions.previousSentence()
        case .keyboardShortcutNextSentence:
            actions.nextSentence()
        case .keyboardShortcutLookup:
            actions.lookup()
        case .keyboardShortcutShowMenu:
            actions.showMenu()
        case .keyboardShortcutHideMenu:
            actions.hideMenu()
        default:
            return false
        }
        #if DEBUG
        keyboardShortcutDebugLog("[KeyboardShortcut] App broker handled \(name.rawValue) directly")
        #endif
        return true
    }

    private func textInputFirstResponder() -> UIResponder? {
        guard let responder = UIResponder.interactiveReaderKeyboardBrokerCurrentFirstResponder else {
            return nil
        }
        if responder is UITextField || responder is UITextView || responder is UISearchBar {
            return responder
        }
        return nil
    }
}

private weak var interactiveReaderKeyboardBrokerCapturedFirstResponder: UIResponder?

private extension UIResponder {
    static var interactiveReaderKeyboardBrokerCurrentFirstResponder: UIResponder? {
        interactiveReaderKeyboardBrokerCapturedFirstResponder = nil
        UIApplication.shared.sendAction(
            #selector(captureInteractiveReaderKeyboardBrokerFirstResponder),
            to: nil,
            from: nil,
            for: nil
        )
        return interactiveReaderKeyboardBrokerCapturedFirstResponder
    }

    @objc func captureInteractiveReaderKeyboardBrokerFirstResponder() {
        interactiveReaderKeyboardBrokerCapturedFirstResponder = self
    }
}

extension UIApplication {
    static func installInteractiveReaderKeyboardEventInterceptor() {
        InteractiveReaderKeyboardEventInterceptor.install()
    }

    @objc fileprivate func interactiveReaderSendEvent(_ event: UIEvent) {
        PlayerKeyboardShortcutBroker.shared.handleApplicationEvent(event)
        interactiveReaderSendEvent(event)
    }
}

private enum InteractiveReaderKeyboardEventInterceptor {
    private static var isInstalled = false

    static func install() {
        guard !isInstalled else { return }
        isInstalled = true
        guard
            let original = class_getInstanceMethod(
                UIApplication.self,
                #selector(UIApplication.sendEvent(_:))
            ),
            let replacement = class_getInstanceMethod(
                UIApplication.self,
                #selector(UIApplication.interactiveReaderSendEvent(_:))
            )
        else {
            #if DEBUG
            keyboardShortcutDebugLog("[KeyboardShortcut] App event interceptor failed to install")
            #endif
            return
        }
        method_exchangeImplementations(original, replacement)
        #if DEBUG
        keyboardShortcutDebugLog("[KeyboardShortcut] App event interceptor installed")
        #endif
    }
}
#endif
