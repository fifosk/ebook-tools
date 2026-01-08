import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

enum VideoLinguistBubbleStatus: Equatable {
    case loading
    case ready
    case error(String)
}

struct VideoLinguistBubbleState: Equatable {
    let query: String
    let status: VideoLinguistBubbleStatus
    let answer: String?
    let model: String?
}

struct VideoLinguistBubbleView: View {
    let bubble: VideoLinguistBubbleState
    let fontScale: CGFloat
    let canIncreaseFont: Bool
    let canDecreaseFont: Bool
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let onLookupLanguageChange: (String) -> Void
    let llmModel: String
    let llmModelOptions: [String]
    let onLlmModelChange: (String) -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onResetFont: (() -> Void)?
    let onClose: () -> Void
    let onMagnify: ((CGFloat) -> Void)?

    #if os(iOS)
    @State private var magnifyStartScale: CGFloat?
    #endif
    #if os(tvOS)
    @FocusState private var focusedControl: BubbleHeaderControl?
    @State private var showingLanguagePicker = false
    @State private var showingModelPicker = false

    private enum BubbleHeaderControl: Hashable {
        case language
        case model
        case decreaseFont
        case increaseFont
        case close
    }
    #endif

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            headerControls

            Text(bubble.query)
                .font(queryFont)
                .lineLimit(2)
                .minimumScaleFactor(0.8)
                #if os(iOS)
                .textSelection(.enabled)
                #endif

            bubbleContent
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(bubbleBackground)
        .overlay(
            RoundedRectangle(cornerRadius: bubbleCornerRadius)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: bubbleCornerRadius))
        .frame(maxWidth: bubbleWidth, alignment: .leading)
        .frame(maxWidth: .infinity, alignment: .center)
        #if os(tvOS)
        .focusEffectDisabled()
        .onAppear {
            if focusedControl == nil {
                focusedControl = bubbleFocusOrder.first
            }
        }
        .onMoveCommand { direction in
            handleBubbleFocusMove(direction)
        }
        #endif
        #if os(iOS)
        .simultaneousGesture(bubbleMagnifyGesture, including: .gesture)
        #endif
    }

    private var headerControls: some View {
        #if os(tvOS)
        HStack(spacing: 8) {
            Text("MyLinguist")
                .font(.headline)
            Spacer(minLength: 8)
            lookupLanguageMenu
            modelMenu
            fontSizeControls
            closeButton
        }
        #else
        HStack(spacing: 8) {
            Text("MyLinguist")
                .font(.headline)
            Spacer(minLength: 8)
            lookupLanguageMenu
            modelMenu
            fontSizeControls
            if let onResetFont {
                Button(action: onResetFont) {
                    Image(systemName: "arrow.counterclockwise")
                        .font(.caption.weight(.semibold))
                        .padding(6)
                        .background(.black.opacity(0.3), in: Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Reset size")
            }
            closeButton
        }
        #endif
    }

    private var closeButton: some View {
        #if os(tvOS)
        bubbleControlButton(
            systemName: "xmark",
            control: .close,
            isEnabled: true,
            action: onClose
        )
        #else
        Button(action: onClose) {
            Image(systemName: "xmark")
                .font(.caption.weight(.semibold))
                .padding(6)
                .background(.black.opacity(0.3), in: Circle())
        }
        .buttonStyle(.plain)
        #endif
    }

    #if os(iOS)
    private var bubbleMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                guard let onMagnify else { return }
                if magnifyStartScale == nil {
                    magnifyStartScale = fontScale
                }
                let startScale = magnifyStartScale ?? fontScale
                onMagnify(startScale * value)
            }
            .onEnded { _ in
                magnifyStartScale = nil
            }
    }
    #endif

    @ViewBuilder
    private var bubbleContent: some View {
        switch bubble.status {
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .progressViewStyle(.circular)
                Text("Looking up...")
                    .font(bodyFont)
                    .foregroundStyle(.secondary)
            }
        case let .error(message):
            Text(message)
                .font(bodyFont)
                .foregroundStyle(.red)
        case .ready:
            ScrollView {
                Text(bubble.answer ?? "")
                    .font(bodyFont)
                    .foregroundStyle(.primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    #if os(iOS)
                    .textSelection(.enabled)
                    #endif
            }
            .frame(maxHeight: bubbleMaxHeight)
        }
    }

    @ViewBuilder
    private var lookupLanguageMenu: some View {
        let entry = LanguageFlagResolver.flagEntry(for: lookupLanguage)
        #if os(tvOS)
        Button {
            showingLanguagePicker = true
        } label: {
            bubbleControlLabel(isFocused: focusedControl == .language) {
                Text(entry.emoji)
            }
        }
        .buttonStyle(.plain)
        .focused($focusedControl, equals: .language)
        .focusEffectDisabled()
        .accessibilityLabel("Lookup language")
        .confirmationDialog("Lookup language", isPresented: $showingLanguagePicker, titleVisibility: .visible) {
            ForEach(lookupLanguageOptions, id: \.self) { language in
                let option = LanguageFlagResolver.flagEntry(for: language)
                Button {
                    onLookupLanguageChange(option.label)
                } label: {
                    if option.label == entry.label {
                        Label("\(option.emoji) \(option.label)", systemImage: "checkmark")
                    } else {
                        Text("\(option.emoji) \(option.label)")
                    }
                }
            }
        }
        #else
        Menu {
            ForEach(lookupLanguageOptions, id: \.self) { language in
                let option = LanguageFlagResolver.flagEntry(for: language)
                Button {
                    onLookupLanguageChange(option.label)
                } label: {
                    if option.label == entry.label {
                        Label("\(option.emoji) \(option.label)", systemImage: "checkmark")
                    } else {
                        Text("\(option.emoji) \(option.label)")
                    }
                }
            }
        } label: {
            Text(entry.emoji)
                .font(.caption)
                .padding(6)
                .background(.black.opacity(0.3), in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Lookup language")
        #endif
    }

    @ViewBuilder
    private var modelMenu: some View {
        #if os(tvOS)
        Button {
            showingModelPicker = true
        } label: {
            bubbleControlLabel(isFocused: focusedControl == .model) {
                Text(llmModel)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            }
        }
        .buttonStyle(.plain)
        .focused($focusedControl, equals: .model)
        .focusEffectDisabled()
        .accessibilityLabel("Lookup model")
        .confirmationDialog("Lookup model", isPresented: $showingModelPicker, titleVisibility: .visible) {
            ForEach(llmModelOptions, id: \.self) { model in
                Button {
                    onLlmModelChange(model)
                } label: {
                    if model == llmModel {
                        Label(model, systemImage: "checkmark")
                    } else {
                        Text(model)
                    }
                }
            }
        }
        #else
        Menu {
            ForEach(llmModelOptions, id: \.self) { model in
                Button {
                    onLlmModelChange(model)
                } label: {
                    if model == llmModel {
                        Label(model, systemImage: "checkmark")
                    } else {
                        Text(model)
                    }
                }
            }
        } label: {
            Text(llmModel)
                .font(.caption2)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(.black.opacity(0.3), in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Lookup model")
        #endif
    }

    private var fontSizeControls: some View {
        #if os(tvOS)
        HStack(spacing: 6) {
            bubbleControlButton(
                title: "A-",
                control: .decreaseFont,
                isEnabled: canDecreaseFont,
                action: onDecreaseFont
            )
            bubbleControlButton(
                title: "A+",
                control: .increaseFont,
                isEnabled: canIncreaseFont,
                action: onIncreaseFont
            )
        }
        #else
        HStack(spacing: 4) {
            Button(action: onDecreaseFont) {
                Text("A-")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!canDecreaseFont)
            Button(action: onIncreaseFont) {
                Text("A+")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!canIncreaseFont)
        }
        #endif
    }

    #if os(tvOS)
    private var bubbleFocusOrder: [BubbleHeaderControl] {
        [.language, .model, .decreaseFont, .increaseFont, .close]
    }

    private func handleBubbleFocusMove(_ direction: MoveCommandDirection) {
        guard let current = focusedControl else { return }
        guard let index = bubbleFocusOrder.firstIndex(of: current) else { return }
        switch direction {
        case .left:
            let next = max(0, index - 1)
            focusedControl = bubbleFocusOrder[next]
        case .right:
            let next = min(bubbleFocusOrder.count - 1, index + 1)
            focusedControl = bubbleFocusOrder[next]
        case .up, .down:
            break
        default:
            break
        }
    }

    private func bubbleControlLabel(isFocused: Bool, @ViewBuilder content: () -> some View) -> some View {
        content()
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .foregroundStyle(.white)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isFocused ? Color.white.opacity(0.25) : Color.black.opacity(0.35))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isFocused ? Color.white.opacity(0.8) : .clear, lineWidth: 1)
            )
    }

    private func bubbleControlButton(
        title: String? = nil,
        systemName: String? = nil,
        control: BubbleHeaderControl,
        isEnabled: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            bubbleControlLabel(isFocused: focusedControl == control) {
                if let systemName {
                    Image(systemName: systemName)
                } else if let title {
                    Text(title)
                }
            }
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
        .focused($focusedControl, equals: control)
        .focusEffectDisabled()
    }
    #endif

    private var queryFont: Font {
        scaledFont(textStyle: .title3, weight: .semibold)
    }

    private var bodyFont: Font {
        scaledFont(textStyle: .callout, weight: .regular)
    }

    private func scaledFont(textStyle: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * fontScale, weight: weight)
        #else
        return .system(size: 16 * fontScale, weight: weight)
        #endif
    }

    private var bubbleBackground: Color {
        Color.black.opacity(0.75)
    }

    private var bubbleCornerRadius: CGFloat {
        #if os(tvOS)
        return 18
        #else
        return 14
        #endif
    }

    private var bubbleMaxHeight: CGFloat {
        #if os(tvOS)
        return 220
        #else
        return 180
        #endif
    }

    private var bubbleWidth: CGFloat {
        #if os(iOS) || os(tvOS)
        return UIScreen.main.bounds.width * 0.66
        #else
        return 420
        #endif
    }
}
