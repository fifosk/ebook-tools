import SwiftUI

// MARK: - Content And Shared Controls

extension LinguistBubbleView {

    @ViewBuilder
    var bubbleContent: some View {
        switch state.status {
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .progressViewStyle(.circular)
                    .tint(.white)
                Text("Looking up...")
                    .font(bodyFont)
                    .foregroundStyle(.white.opacity(0.7))
            }
        case let .error(message):
            Text(message)
                .font(bodyFont)
                .foregroundStyle(.red)
        case .ready:
            if configuration.useCompactLayout {
                structuredOrFallbackContent
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ScrollView {
                    structuredOrFallbackContent
                        .frame(maxWidth: .infinity, alignment: .leading)
                        #if os(tvOS)
                        .padding(.bottom, 20)
                        #endif
                }
                #if os(tvOS)
                .scrollIndicators(.visible)
                .scrollBounceBehavior(.basedOnSize)
                #endif
                .frame(maxHeight: bubbleMaxHeight)
            }
        }
    }

    #if os(iOS) || os(tvOS)
    @ViewBuilder
    var structuredOrFallbackContent: some View {
        if let parsed = state.parsedResult {
            StructuredLinguistContentView(
                result: parsed,
                font: bodyFont,
                color: bubbleTextColor
            )
        } else {
            #if os(iOS)
            TappableWordText(
                text: state.answer ?? "",
                font: bodyFont,
                color: bubbleTextColor
            )
            #else
            Text(state.answer ?? "")
                .font(bodyFont)
                .foregroundStyle(bubbleTextColor)
            #endif
        }
    }
    #endif

    #if os(tvOS)
    var fontSizeControls: some View {
        HStack(spacing: 6) {
            bubbleControlItem(control: .decreaseFont, isEnabled: configuration.canDecreaseFont, action: actions.onDecreaseFont) {
                Text("-")
            }
            bubbleControlItem(control: .increaseFont, isEnabled: configuration.canIncreaseFont, action: actions.onIncreaseFont) {
                Text("+")
            }
        }
    }
    #endif

    var closeButton: some View {
        #if os(tvOS)
        bubbleControlItem(control: .close, isEnabled: true, action: actions.onClose) {
            Image(systemName: "xmark")
        }
        #else
        Button(action: actions.onClose) {
            Image(systemName: "xmark")
                .font(bubbleIconFont)
                .foregroundStyle(.white)
                .padding(bubbleControlPadding)
                .background(.black.opacity(0.3), in: Circle())
                .overlay(
                    Circle().stroke(
                        isControlKeyboardFocused(.close) ? keyboardFocusBorderColor : Color.clear,
                        lineWidth: isControlKeyboardFocused(.close) ? keyboardFocusBorderWidth : 0
                    )
                )
        }
        .buttonStyle(.plain)
        #endif
    }
}
