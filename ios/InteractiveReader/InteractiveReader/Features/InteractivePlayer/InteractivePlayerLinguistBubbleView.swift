import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

enum MyLinguistBubbleStatus: Equatable {
    case loading
    case ready
    case error(String)
}

struct MyLinguistBubbleState: Equatable {
    let query: String
    let status: MyLinguistBubbleStatus
    let answer: String?
    let model: String?
}

struct MyLinguistBubbleView: View {
    let bubble: MyLinguistBubbleState
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
    let onClose: () -> Void
    let isFocusEnabled: Bool
    let focusBinding: FocusState<InteractivePlayerFocusArea?>.Binding

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                #if !os(tvOS)
                Text("MyLinguist")
                    .font(.headline)
                Spacer(minLength: 8)
                #endif
                lookupLanguageMenu
                modelMenu
                fontSizeControls
                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .font(.caption.weight(.semibold))
                        .padding(6)
                        .background(.black.opacity(0.3), in: Circle())
                }
                .buttonStyle(.plain)
                #if os(tvOS)
                .focusable(isFocusEnabled)
                .allowsHitTesting(isFocusEnabled)
                .focused(focusBinding, equals: .bubble)
                #endif
            }

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
    }

    private var lookupLanguageMenu: some View {
        let entry = LanguageFlagResolver.flagEntry(for: lookupLanguage)
        return Menu {
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
        #if os(tvOS)
        .focusable(isFocusEnabled)
        .allowsHitTesting(isFocusEnabled)
        .focused(focusBinding, equals: .bubble)
        #endif
    }

    private var modelMenu: some View {
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
        #if os(tvOS)
        .focusable(isFocusEnabled)
        .allowsHitTesting(isFocusEnabled)
        .focused(focusBinding, equals: .bubble)
        #endif
    }

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

    private var fontSizeControls: some View {
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
            #if os(tvOS)
            .focusable(isFocusEnabled)
            .allowsHitTesting(isFocusEnabled)
            .focused(focusBinding, equals: .bubble)
            #endif
            Button(action: onIncreaseFont) {
                Text("A+")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!canIncreaseFont)
            #if os(tvOS)
            .focusable(isFocusEnabled)
            .allowsHitTesting(isFocusEnabled)
            .focused(focusBinding, equals: .bubble)
            #endif
        }
    }

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
