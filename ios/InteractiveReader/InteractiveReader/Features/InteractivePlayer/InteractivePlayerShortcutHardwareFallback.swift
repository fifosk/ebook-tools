#if os(iOS)
import GameController
import UIKit

extension KeyboardCommandHandler.KeyCommandController {
    func installHardwareKeyboardFallback() {
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

    func removeHardwareKeyboardFallback() {
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
                self?.dispatchPreviousArrowShortcut(source: "broker")
            },
            next: { [weak self] in
                self?.dispatchNextArrowShortcut(source: "broker")
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
            },
            shouldNavigateBubbleWords: { [weak self] in
                self?.shouldRoutePlainArrowToBubbleWords == true
            },
            bubbleNavigateLeft: { [weak self] in
                self?.dispatchShortcut(.bubbleNavigateLeft, source: "broker") { [weak self] in
                    self?.onBubbleNavigateLeft?()
                }
            },
            bubbleNavigateRight: { [weak self] in
                self?.dispatchShortcut(.bubbleNavigateRight, source: "broker") { [weak self] in
                    self?.onBubbleNavigateRight?()
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
                dispatchPreviousArrowShortcut(source: "gc")
            }
        case .rightArrow:
            if shiftDown {
                dispatchShortcut(.extendSelectionForward, source: "gc") { self.onExtendSelectionForward?() }
            } else if controlDown {
                dispatchShortcut(.nextSentence, source: "gc") { self.onNextSentence?() }
            } else {
                dispatchNextArrowShortcut(source: "gc")
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

    func hardwareKeyboardShortcutBlockReason(allowingTextInput: Bool) -> String? {
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

}
#endif
