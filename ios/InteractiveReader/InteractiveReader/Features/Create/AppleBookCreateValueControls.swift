import SwiftUI

struct AppleBookCreateDiscreteValueControl: View {
    @Binding var value: Int
    let clampedValue: Int
    let range: ClosedRange<Int>
    let step: Int
    let title: String
    let decrementAccessibilityLabel: String
    let incrementAccessibilityLabel: String

    init(
        value: Binding<Int>,
        clampedValue: Int,
        range: ClosedRange<Int>,
        step: Int = 1,
        title: String,
        decrementAccessibilityLabel: String,
        incrementAccessibilityLabel: String
    ) {
        _value = value
        self.clampedValue = clampedValue
        self.range = range
        self.step = step
        self.title = title
        self.decrementAccessibilityLabel = decrementAccessibilityLabel
        self.incrementAccessibilityLabel = incrementAccessibilityLabel
    }

    var body: some View {
        LabeledContent(title) {
            HStack(spacing: 12) {
                Button {
                    value = max(range.lowerBound, clampedValue - step)
                } label: {
                    Image(systemName: "minus")
                }
                .disabled(clampedValue <= range.lowerBound)
                .accessibilityLabel(decrementAccessibilityLabel)

                Text("\(clampedValue)")
                    .monospacedDigit()
                    .frame(minWidth: 48)

                Button {
                    value = min(range.upperBound, clampedValue + step)
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(clampedValue >= range.upperBound)
                .accessibilityLabel(incrementAccessibilityLabel)
            }
        }
    }
}
