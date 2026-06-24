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

struct AppleBookCreateDiscreteDoubleValueControl: View {
    @Binding var value: Double
    let clampedValueLabel: String
    let range: ClosedRange<Double>
    let step: Double
    let title: String
    let decrementAccessibilityLabel: String
    let incrementAccessibilityLabel: String

    var body: some View {
        LabeledContent(title) {
            HStack(spacing: 12) {
                Button {
                    value = max(range.lowerBound, value - step)
                } label: {
                    Image(systemName: "minus")
                }
                .disabled(value <= range.lowerBound)
                .accessibilityLabel(decrementAccessibilityLabel)

                Text(clampedValueLabel)
                    .monospacedDigit()
                    .frame(minWidth: 56)

                Button {
                    value = min(range.upperBound, value + step)
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(value >= range.upperBound)
                .accessibilityLabel(incrementAccessibilityLabel)
            }
        }
    }
}
