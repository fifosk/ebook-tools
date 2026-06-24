import SwiftUI

struct AppleBookCreateDiscreteValueControl: View {
    @Binding var value: Int
    let clampedValue: Int
    let range: ClosedRange<Int>
    let title: String
    let decrementAccessibilityLabel: String
    let incrementAccessibilityLabel: String

    var body: some View {
        LabeledContent(title) {
            HStack(spacing: 12) {
                Button {
                    value = max(range.lowerBound, clampedValue - 1)
                } label: {
                    Image(systemName: "minus")
                }
                .disabled(clampedValue <= range.lowerBound)
                .accessibilityLabel(decrementAccessibilityLabel)

                Text("\(clampedValue)")
                    .monospacedDigit()
                    .frame(minWidth: 48)

                Button {
                    value = min(range.upperBound, clampedValue + 1)
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(clampedValue >= range.upperBound)
                .accessibilityLabel(incrementAccessibilityLabel)
            }
        }
    }
}
