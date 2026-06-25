import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

extension InteractivePlayerView {
    var infoCoverWidth: CGFloat {
        PlayerInfoMetrics.coverWidth(isTV: isTV) * infoHeaderScale
    }

    var infoCoverHeight: CGFloat {
        PlayerInfoMetrics.coverHeight(isTV: isTV) * infoHeaderScale
    }

    var infoTitleFont: Font {
        #if os(tvOS)
        return .headline
        #else
        if isPad {
            return scaledHeaderFont(style: .subheadline, weight: .semibold)
        }
        return .subheadline.weight(.semibold)
        #endif
    }

    var infoEyebrowFont: Font {
        #if os(tvOS)
        return .caption.weight(.semibold)
        #else
        if isPad {
            return scaledHeaderFont(style: .caption2, weight: .semibold)
        }
        return .caption2.weight(.semibold)
        #endif
    }

    var infoMetaFont: Font {
        #if os(tvOS)
        return .callout
        #else
        if isPad {
            return scaledHeaderFont(style: .caption1, weight: .regular)
        }
        return .caption
        #endif
    }

    var infoIndicatorFont: Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        if isPad {
            return scaledHeaderFont(style: .caption1, weight: .semibold)
        }
        return .caption.weight(.semibold)
        #endif
    }

    var infoHeaderScale: CGFloat {
        #if os(iOS)
        let base: CGFloat = isPad ? 2.0 : 1.0
        return base * headerScale
        #else
        return 1.0
        #endif
    }

    var infoPillScale: CGFloat {
        #if os(iOS)
        let base: CGFloat = isPad ? 2.0 : 1.0
        return base * headerScale
        #else
        return 1.0
        #endif
    }

    func scaledHeaderFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: baseSize * infoHeaderScale, weight: weight)
        #else
        return .system(size: 16 * infoHeaderScale, weight: weight)
        #endif
    }

    var headerScale: CGFloat {
        get { CGFloat(headerScaleValue) }
        nonmutating set { headerScaleValue = Double(newValue) }
    }

    func adjustHeaderScale(by delta: CGFloat) {
        setHeaderScale(headerScale + delta)
    }

    func setHeaderScale(_ value: CGFloat) {
        let updated = min(max(value, headerScaleMin), headerScaleMax)
        if updated != headerScale {
            headerScale = updated
        }
    }

    @ViewBuilder
    func headerMagnifyWrapper<Content: View>(_ content: Content) -> some View {
        #if os(iOS)
        if isPad {
            // Use .subviews to allow Menu and other interactive elements to work
            // while still supporting pinch-to-zoom on non-interactive areas.
            content.simultaneousGesture(headerMagnifyGesture, including: .subviews)
        } else {
            content
        }
        #else
        content
        #endif
    }

    #if os(iOS)
    private var headerMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                if headerMagnifyStartScale == nil {
                    headerMagnifyStartScale = headerScale
                }
                let startScale = headerMagnifyStartScale ?? headerScale
                setHeaderScale(startScale * value)
            }
            .onEnded { _ in
                headerMagnifyStartScale = nil
            }
    }
    #endif

    var infoHeaderReservedHeight: CGFloat {
        #if os(tvOS)
        return PlayerInfoMetrics.badgeHeight(isTV: true) + 72
        #else
        let baseHeight = PlayerInfoMetrics.badgeHeight(isTV: false) * infoHeaderScale
        let padding = isPad ? 28 * infoHeaderScale : 20
        let controlsAllowance = isPad ? 20 * infoPillScale : (isPhone ? 34 * infoPillScale : 0)
        return baseHeight + padding + controlsAllowance + headerSliderReservedHeight
        #endif
    }

    var headerSliderReservedHeight: CGFloat {
        #if os(iOS)
        guard headerInfo != nil else { return 0 }
        return 42 * infoHeaderScale
        #else
        return 0
        #endif
    }

    var transcriptTopPadding: CGFloat {
        #if os(iOS) || os(tvOS)
        // On iPhone, reduce padding when bubble is shown because the header is always hidden.
        if isPhone && linguistBubble != nil {
            return 8
        }
        // On iPad with bubble, respect the header collapsed state.
        return isHeaderCollapsed ? 8 : infoHeaderReservedHeight
        #else
        return infoHeaderReservedHeight
        #endif
    }

    var shouldShowHeaderOverlay: Bool {
        if isPhone && linguistBubble != nil {
            return false
        }
        return !isHeaderCollapsed
    }

    @ViewBuilder
    var headerToggleButton: some View {
        #if os(iOS)
        let showButton = isHeaderCollapsed || ((isPhone || isPad) && linguistBubble != nil)
        if showButton, let chunk = viewModel.selectedChunk {
            let timelineLabel = audioTimelineLabel(for: chunk)
            VStack(spacing: 0) {
                HStack(spacing: 6) {
                    Spacer(minLength: 0)
                    musicPillView
                    if let timelineLabel {
                        audioTimelineView(label: timelineLabel)
                    }
                }
                .padding(.top, 6)
                .padding(.trailing, 6)
                Spacer(minLength: 0)
            }
            .zIndex(2)
        }
        #else
        EmptyView()
        #endif
    }

    #if os(tvOS)
    /// Non-focusable toggle pill - header show/hide is handled by long press on middle button.
    var tvHeaderTogglePill: some View {
        Image(systemName: isHeaderCollapsed ? "chevron.down" : "chevron.up")
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.black.opacity(0.6), in: Capsule())
            .foregroundStyle(.white)
            .accessibilityLabel(isHeaderCollapsed ? "Header collapsed" : "Header expanded")
            .accessibilityHint("Long press middle button to toggle")
    }
    #endif

    func handleHeaderLongPress() {
        toggleHeaderCollapsed()
    }

    func handleAudioTimelineTap() {
        toggleHeaderCollapsed()
    }

    func toggleHeaderCollapsed() {
        withAnimation(.easeInOut(duration: 0.2)) {
            isHeaderCollapsed.toggle()
        }
    }
}
