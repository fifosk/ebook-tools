import SwiftUI
#if os(iOS)
import UIKit
#endif

struct ShortcutHelpOverlayView: View {
    let onDismiss: () -> Void

    private let sections: [ShortcutHelpSection] = [
        ShortcutHelpSection(
            title: "Playback",
            items: [
                ShortcutHelpItem(keys: "Space", action: "Play or pause")
            ]
        ),
        ShortcutHelpSection(
            title: "Navigation",
            items: [
                ShortcutHelpItem(keys: "Left Arrow (playing)", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Right Arrow (playing)", action: "Next sentence"),
                ShortcutHelpItem(keys: "Left / Right Arrow (paused)", action: "Previous or next word"),
                ShortcutHelpItem(keys: "Shift + Left / Right Arrow (paused)", action: "Extend selection"),
                ShortcutHelpItem(keys: "Ctrl + Left Arrow", action: "Previous word"),
                ShortcutHelpItem(keys: "Ctrl + Right Arrow", action: "Next word"),
                ShortcutHelpItem(keys: "Enter", action: "Lookup word"),
                ShortcutHelpItem(keys: "Down Arrow (playing)", action: "Show menu"),
                ShortcutHelpItem(keys: "Up Arrow (playing)", action: "Hide menu"),
                ShortcutHelpItem(keys: "Up / Down Arrow (paused)", action: "Switch track")
            ]
        ),
        ShortcutHelpSection(
            title: "Touch",
            items: [
                ShortcutHelpItem(keys: "Tap word", action: "Jump to word"),
                ShortcutHelpItem(keys: "Double tap background", action: "Play or pause"),
                ShortcutHelpItem(keys: "Swipe left", action: "Next sentence"),
                ShortcutHelpItem(keys: "Swipe right", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Pinch text", action: "Resize tracks"),
                ShortcutHelpItem(keys: "Pinch bubble", action: "Resize MyLinguist"),
                ShortcutHelpItem(keys: "Pinch header (iPad)", action: "Resize header")
            ]
        ),
        ShortcutHelpSection(
            title: "Text Tracks",
            items: [
                ShortcutHelpItem(keys: "O", action: "Toggle original line"),
                ShortcutHelpItem(keys: "I", action: "Toggle transliteration line"),
                ShortcutHelpItem(keys: "P", action: "Toggle translation line")
            ]
        ),
        ShortcutHelpSection(
            title: "Audio Tracks",
            items: [
                ShortcutHelpItem(keys: "Shift + O", action: "Toggle original audio"),
                ShortcutHelpItem(keys: "Shift + P", action: "Toggle translation audio"),
                ShortcutHelpItem(keys: "Shift + I", action: "Toggle reading bed")
            ]
        ),
        ShortcutHelpSection(
            title: "Font Size",
            items: [
                ShortcutHelpItem(keys: "+ / -", action: "Track font size"),
                ShortcutHelpItem(keys: "Ctrl + +/-", action: "MyLinguist font size"),
                ShortcutHelpItem(keys: "Shift + +/-", action: "Header size")
            ]
        ),
        ShortcutHelpSection(
            title: "Help",
            items: [
                ShortcutHelpItem(keys: "H", action: "Toggle this overlay"),
                ShortcutHelpItem(keys: "Shift + H", action: "Toggle header"),
                ShortcutHelpItem(keys: "Option (hold)", action: "Show shortcuts overlay")
            ]
        )
    ]

    var body: some View {
        ZStack {
            Color.black.opacity(0.35)
                .ignoresSafeArea()
                .onTapGesture {
                    onDismiss()
                }
            VStack(alignment: .leading, spacing: 12) {
                header
                Divider()
                    .overlay(Color.white.opacity(0.12))
                ScrollView {
                    LazyVGrid(columns: gridColumns, alignment: .leading, spacing: 16) {
                        ForEach(sections) { section in
                            ShortcutHelpSectionView(section: section, keycapWidth: keycapColumnWidth)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: isPad ? 380 : 320)
            }
            .padding(20)
            .frame(maxWidth: isPad ? 660 : 520)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.2), radius: 14, x: 0, y: 8)
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Label("Keyboard Shortcuts", systemImage: "keyboard")
                .font(.headline.weight(.semibold))
            Spacer()
            Button(action: onDismiss) {
                Image(systemName: "xmark")
                    .font(.caption.weight(.semibold))
                    .padding(8)
                    .background(.black.opacity(0.15), in: Circle())
            }
            .buttonStyle(.plain)
        }
    }

    private var gridColumns: [GridItem] {
        if isPad {
            return [GridItem(.flexible(), spacing: 16), GridItem(.flexible(), spacing: 16)]
        }
        return [GridItem(.flexible())]
    }

    private var keycapColumnWidth: CGFloat {
        isPad ? 150 : 170
    }

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private struct ShortcutHelpSectionView: View {
        let section: ShortcutHelpSection
        let keycapWidth: CGFloat

        var body: some View {
            VStack(alignment: .leading, spacing: 8) {
                Text(section.title.uppercased())
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
                ForEach(section.items) { item in
                    ShortcutHelpRow(item: item, keycapWidth: keycapWidth)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private struct ShortcutHelpRow: View {
        let item: ShortcutHelpItem
        let keycapWidth: CGFloat

        var body: some View {
            HStack(alignment: .top, spacing: 12) {
                KeycapGroup(keys: item.keys)
                    .frame(width: keycapWidth, alignment: .leading)
                Text(item.action)
                    .font(.callout)
                    .foregroundStyle(.primary)
                Spacer(minLength: 0)
            }
        }
    }

    private struct KeycapGroup: View {
        let keys: String

        var body: some View {
            let (base, context) = splitContext(keys)
            HStack(spacing: 6) {
                keycapContent(base)
                if let context {
                    ContextPill(label: context)
                }
            }
        }

        @ViewBuilder
        private func keycapContent(_ value: String) -> some View {
            let alternatives = value.split(separator: "/").map { $0.trimmingCharacters(in: .whitespaces) }
            HStack(spacing: 4) {
                ForEach(Array(alternatives.enumerated()), id: \.offset) { index, alternative in
                    if index > 0 {
                        Text("/")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                    let combo = alternative.split(separator: "+").map { $0.trimmingCharacters(in: .whitespaces) }
                    HStack(spacing: 4) {
                        ForEach(Array(combo.enumerated()), id: \.offset) { comboIndex, token in
                            if comboIndex > 0 {
                                Text("+")
                                    .font(.caption2.weight(.semibold))
                                    .foregroundStyle(.secondary)
                            }
                            KeycapView(label: keyLabel(String(token)))
                        }
                    }
                }
            }
        }

        private func splitContext(_ value: String) -> (String, String?) {
            guard let openRange = value.range(of: " ("),
                  value.hasSuffix(")") else {
                return (value, nil)
            }
            let base = value[..<openRange.lowerBound]
            let contextStart = value.index(openRange.lowerBound, offsetBy: 2)
            let contextEnd = value.index(before: value.endIndex)
            let context = value[contextStart..<contextEnd]
            return (String(base), String(context))
        }

        private func keyLabel(_ raw: String) -> String {
            let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            let lower = trimmed.lowercased()
            switch lower {
            case "left arrow":
                return "←"
            case "right arrow":
                return "→"
            case "up arrow":
                return "↑"
            case "down arrow":
                return "↓"
            case "option":
                return "⌥"
            case "shift":
                return "⇧"
            case "ctrl", "control":
                return "⌃"
            case "command", "cmd":
                return "⌘"
            case "enter", "return":
                return "↩︎"
            case "backspace":
                return "⌫"
            case "delete":
                return "⌦"
            case "+/-":
                return "±"
            case "space":
                return "Space"
            default:
                return trimmed
            }
        }
    }

    private struct KeycapView: View {
        let label: String

        var body: some View {
            Text(label)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .foregroundStyle(.primary)
                .padding(.horizontal, 8)
                .padding(.vertical, 5)
                .background(
                    RoundedRectangle(cornerRadius: 6, style: .continuous)
                        .fill(Color.primary.opacity(0.12))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 6, style: .continuous)
                        .stroke(Color.primary.opacity(0.22), lineWidth: 1)
                )
        }
    }

    private struct ContextPill: View {
        let label: String

        var body: some View {
            Text(label)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(
                    Capsule()
                        .fill(Color.primary.opacity(0.08))
                )
        }
    }

    private struct ShortcutHelpSection: Identifiable {
        let id = UUID()
        let title: String
        let items: [ShortcutHelpItem]
    }

    private struct ShortcutHelpItem: Identifiable {
        let id = UUID()
        let keys: String
        let action: String
    }
}

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

    func makeUIViewController(context: Context) -> KeyCommandController {
        let controller = KeyCommandController()
        controller.onPlayPause = onPlayPause
        controller.onPrevious = onPrevious
        controller.onNext = onNext
        controller.onPreviousWord = onPreviousWord
        controller.onNextWord = onNextWord
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
        return controller
    }

    func updateUIViewController(_ uiViewController: KeyCommandController, context: Context) {
        uiViewController.onPlayPause = onPlayPause
        uiViewController.onPrevious = onPrevious
        uiViewController.onNext = onNext
        uiViewController.onPreviousWord = onPreviousWord
        uiViewController.onNextWord = onNextWord
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
    }

    final class KeyCommandController: UIViewController {
        var onPlayPause: (() -> Void)?
        var onPrevious: (() -> Void)?
        var onNext: (() -> Void)?
        var onPreviousWord: (() -> Void)?
        var onNextWord: (() -> Void)?
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
        private var isOptionKeyDown = false

        override var canBecomeFirstResponder: Bool {
            true
        }

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            becomeFirstResponder()
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
            onPlayPause?()
        }

        @objc private func handlePrevious() {
            onPrevious?()
        }

        @objc private func handleNext() {
            onNext?()
        }

        @objc private func handlePreviousWord() {
            onPreviousWord?()
        }

        @objc private func handleNextWord() {
            onNextWord?()
        }

        @objc private func handleExtendSelectionBackward() {
            onExtendSelectionBackward?()
        }

        @objc private func handleExtendSelectionForward() {
            onExtendSelectionForward?()
        }

        @objc private func handleLookup() {
            onLookup?()
        }

        @objc private func handleIncreaseFont() {
            onIncreaseFont?()
        }

        @objc private func handleDecreaseFont() {
            onDecreaseFont?()
        }

        @objc private func handleToggleOriginal() {
            onToggleOriginal?()
        }

        @objc private func handleToggleTransliteration() {
            onToggleTransliteration?()
        }

        @objc private func handleToggleTranslation() {
            onToggleTranslation?()
        }

        @objc private func handleToggleOriginalAudio() {
            onToggleOriginalAudio?()
        }

        @objc private func handleToggleTranslationAudio() {
            onToggleTranslationAudio?()
        }

        @objc private func handleToggleReadingBed() {
            onToggleReadingBed?()
        }

        @objc private func handleIncreaseLinguistFont() {
            onIncreaseLinguistFont?()
        }

        @objc private func handleDecreaseLinguistFont() {
            onDecreaseLinguistFont?()
        }

        @objc private func handleToggleHelp() {
            onToggleShortcutHelp?()
        }

        @objc private func handleToggleHeader() {
            onToggleHeader?()
        }

        @objc private func handleIncreaseHeaderScale() {
            onIncreaseHeaderScale?()
        }

        @objc private func handleDecreaseHeaderScale() {
            onDecreaseHeaderScale?()
        }

        @objc private func handleShowMenu() {
            onShowMenu?()
        }

        @objc private func handleHideMenu() {
            onHideMenu?()
        }

        override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), !isOptionKeyDown {
                isOptionKeyDown = true
                onOptionKeyDown?()
            }
            super.pressesBegan(presses, with: event)
        }

        override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesEnded(presses, with: event)
        }

        override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesCancelled(presses, with: event)
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
    }
}
#endif
