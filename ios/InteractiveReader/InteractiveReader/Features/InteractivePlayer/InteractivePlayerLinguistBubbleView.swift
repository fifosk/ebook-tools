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

    #if os(tvOS)
    @FocusState private var focusedControl: BubbleHeaderControl?
    @State private var activePicker: BubblePicker?

    private enum BubbleHeaderControl: Hashable {
        case language
        case model
        case decreaseFont
        case increaseFont
        case close
    }

    private enum BubblePicker: Hashable {
        case language
        case model
    }
    #endif

    var body: some View {
        ZStack {
            bubbleBody
            #if os(tvOS)
            if activePicker != nil {
                pickerOverlay
            }
            #endif
        }
    }

    private var bubbleBody: some View {
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
        .focusSection()
        .onAppear {
            if focusedControl == nil {
                focusedControl = .language
            }
        }
        .onChange(of: focusedControl) { _, newValue in
            guard newValue != nil else { return }
            if focusBinding.wrappedValue != .bubble {
                focusBinding.wrappedValue = .bubble
            }
        }
        .onChange(of: isFocusEnabled) { _, enabled in
            if enabled {
                if focusedControl == nil {
                    focusedControl = .language
                }
            } else if focusedControl != nil {
                focusedControl = nil
            }
        }
        .onChange(of: activePicker) { _, newValue in
            if newValue == nil && isFocusEnabled && focusedControl == nil {
                focusedControl = .language
            }
        }
        #endif
    }

    private var headerControls: some View {
        #if os(tvOS)
        HStack(spacing: 8) {
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
            closeButton
        }
        #endif
    }

    @ViewBuilder
    private var lookupLanguageMenu: some View {
        let entry = LanguageFlagResolver.flagEntry(for: lookupLanguage)
        #if os(tvOS)
        bubbleControlItem(control: .language, isEnabled: true, action: {
            activePicker = .language
        }) {
            Text(entry.emoji)
        }
        .accessibilityLabel("Lookup language")
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
        bubbleControlItem(control: .model, isEnabled: true, action: {
            activePicker = .model
        }) {
            Text(verbatim: llmModel)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .accessibilityLabel("Lookup model")
        #else
        Menu {
            ForEach(llmModelOptions, id: \.self) { model in
                Button {
                    onLlmModelChange(model)
                } label: {
                    if model == llmModel {
                        Label(
                            title: { Text(verbatim: model) },
                            icon: { Image(systemName: "checkmark") }
                        )
                    } else {
                        Text(verbatim: model)
                    }
                }
            }
        } label: {
            Text(verbatim: llmModel)
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
        #if os(tvOS)
        HStack(spacing: 6) {
            bubbleControlItem(control: .decreaseFont, isEnabled: canDecreaseFont, action: onDecreaseFont) {
                Text("A-")
            }
            bubbleControlItem(control: .increaseFont, isEnabled: canIncreaseFont, action: onIncreaseFont) {
                Text("A+")
            }
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

    private var closeButton: some View {
        #if os(tvOS)
        bubbleControlItem(control: .close, isEnabled: true, action: onClose) {
            Image(systemName: "xmark")
        }
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

    #if os(tvOS)
    private struct BubblePickerOption: Identifiable {
        let id: String
        let title: String
        let value: String
        let isSelected: Bool
        let lineLimit: Int
    }

    private struct BubblePickerOptionRow: View {
        let option: BubblePickerOption

        var body: some View {
            HStack(spacing: 10) {
                Text(verbatim: option.title)
                    .lineLimit(option.lineLimit)
                Spacer(minLength: 12)
                if option.isSelected {
                    Image(systemName: "checkmark")
                        .foregroundStyle(.white)
                }
            }
            .font(.callout)
            .foregroundStyle(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.white.opacity(option.isSelected ? 0.25 : 0.12))
            )
        }
    }

    private struct BubblePickerOverlay: View {
        let title: String
        let options: [BubblePickerOption]
        let onSelectOption: (BubblePickerOption) -> Void
        let activePicker: Binding<BubblePicker?>
        @FocusState private var pickerFocus: String?

        var body: some View {
            ZStack {
                Color.black.opacity(0.55)
                    .ignoresSafeArea()
                VStack(spacing: 12) {
                    Text(title)
                        .font(.headline)
                        .foregroundStyle(.white)
                    ScrollView {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(options) { option in
                                Button {
                                    onSelectOption(option)
                                    activePicker.wrappedValue = nil
                                } label: {
                                    BubblePickerOptionRow(option: option)
                                }
                                .buttonStyle(.plain)
                                .focused($pickerFocus, equals: Optional(option.id))
                            }
                        }
                        .padding(.horizontal, 8)
                    }
                    Button("Close") {
                        activePicker.wrappedValue = nil
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(.black.opacity(0.4), in: Capsule())
                    .foregroundStyle(.white)
                }
                .padding(16)
                .frame(maxWidth: 520)
                .background(Color.black.opacity(0.85), in: RoundedRectangle(cornerRadius: 16))
            }
            .focusSection()
            .onExitCommand {
                activePicker.wrappedValue = nil
            }
            .onAppear {
                if pickerFocus == nil {
                    pickerFocus = options.first(where: { $0.isSelected })?.id ?? options.first?.id
                }
            }
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

    private func bubbleControlItem(
        control: BubbleHeaderControl,
        isEnabled: Bool,
        action: @escaping () -> Void,
        @ViewBuilder label: () -> some View
    ) -> some View {
        let canFocus = isEnabled && activePicker == nil
        return bubbleControlLabel(isFocused: focusedControl == control) {
            label()
        }
        .opacity(isEnabled ? 1 : 0.45)
        .contentShape(Rectangle())
        .focusable(canFocus)
        .focused($focusedControl, equals: control)
        .focused(focusBinding, equals: .bubble)
        .focusEffectDisabled()
        .onTapGesture {
            guard canFocus, focusedControl == control else { return }
            action()
        }
    }
    #endif

    #if os(tvOS)
    @ViewBuilder
    private var pickerOverlay: some View {
        if let activePicker {
            pickerOverlayContent(activePicker: activePicker)
        }
    }

    @ViewBuilder
    private func pickerOverlayContent(activePicker selection: BubblePicker) -> some View {
        let isLanguage = selection == .language
        let title = isLanguage ? "Lookup language" : "Lookup model"
        let options = pickerOptions(isLanguage: isLanguage)
        BubblePickerOverlay(
            title: title,
            options: options,
            onSelectOption: { option in
                if isLanguage {
                    onLookupLanguageChange(option.value)
                } else {
                    onLlmModelChange(option.value)
                }
            },
            activePicker: $activePicker
        )
    }

    private func pickerOptions(isLanguage: Bool) -> [BubblePickerOption] {
        if isLanguage {
            return lookupLanguageOptions.map { option in
                let entry = LanguageFlagResolver.flagEntry(for: option)
                let label = entry.label
                return BubblePickerOption(
                    id: option,
                    title: "\(entry.emoji) \(label)",
                    value: label,
                    isSelected: label == lookupLanguage,
                    lineLimit: 1
                )
            }
        }
        return llmModelOptions.map { model in
            BubblePickerOption(
                id: model,
                title: model,
                value: model,
                isSelected: model == llmModel,
                lineLimit: 2
            )
        }
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
