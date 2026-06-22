#if os(iOS)
import UIKit
import UIKit.UIGestureRecognizerSubclass

extension KeyboardCommandHandler.KeyCommandController {
    class KeyCommandHostView: UITextField {
        weak var controller: KeyboardCommandHandler.KeyCommandController?
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
    final class DeferralSafeKeyCommandHostView: KeyCommandHostView {
        override var focusItemDeferralMode: UIFocusItemDeferralMode {
            .never
        }
    }
}

/// Gesture recognizer that observes touches-ended without consuming the touch.
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

extension UIResponder {
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
