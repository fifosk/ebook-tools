import SwiftUI

struct SummaryTickerPill: View {
    let text: String
    let isTV: Bool

    var body: some View {
        MarqueeText(
            text: text,
            font: tickerFont,
            speed: tickerSpeed,
            gap: tickerGap
        )
        .padding(.horizontal, 10)
        .padding(.vertical, isTV ? 8 : 4)
        .background(
            Capsule()
                .fill(Color.black.opacity(0.45))
                .overlay(
                    Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1)
                )
        )
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityLabel(text)
    }

    private var tickerFont: Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        return .caption.weight(.semibold)
        #endif
    }

    private var tickerSpeed: CGFloat {
        isTV ? 36 : 28
    }

    private var tickerGap: CGFloat {
        isTV ? 48 : 32
    }
}

struct MarqueeText: View {
    let text: String
    let font: Font
    let speed: CGFloat
    let gap: CGFloat

    @State private var textWidth: CGFloat = 0
    @State private var startTime = Date()

    var body: some View {
        GeometryReader { proxy in
            let availableWidth = proxy.size.width
            TimelineView(.animation) { timeline in
                let shouldScroll = textWidth > availableWidth
                let elapsed = timeline.date.timeIntervalSince(startTime)
                let cycle = textWidth + gap
                let rawOffset = CGFloat(elapsed) * speed
                let offset = shouldScroll && cycle > 0
                    ? -rawOffset.truncatingRemainder(dividingBy: cycle)
                    : 0
                HStack(spacing: gap) {
                    marqueeText
                    if shouldScroll {
                        marqueeText
                    }
                }
                .offset(x: offset)
                .frame(maxWidth: .infinity, alignment: .leading)
                .onChange(of: availableWidth) { _, _ in
                    startTime = Date()
                }
                .onChange(of: text) { _, _ in
                    startTime = Date()
                }
            }
        }
        .frame(height: marqueeHeight)
        .clipped()
    }

    private var marqueeText: some View {
        Text(text)
            .font(font)
            .foregroundStyle(Color.white.opacity(0.85))
            .lineLimit(1)
            .fixedSize()
            .background(WidthReader(width: $textWidth))
    }

    private var marqueeHeight: CGFloat {
        #if os(tvOS)
        return 32
        #else
        return 18
        #endif
    }
}

struct WidthPreferenceKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

struct WidthReader: View {
    @Binding var width: CGFloat

    var body: some View {
        GeometryReader { proxy in
            Color.clear
                .preference(key: WidthPreferenceKey.self, value: proxy.size.width)
        }
        .onPreferenceChange(WidthPreferenceKey.self) { value in
            width = value
        }
    }
}
