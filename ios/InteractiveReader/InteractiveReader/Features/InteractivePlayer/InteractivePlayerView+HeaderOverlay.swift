import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Header Overlay

extension InteractivePlayerView {

    func playerInfoOverlay(for chunk: InteractiveChunk) -> some View {
        let variant = resolveInfoVariant()
        let label = headerInfo?.itemTypeLabel.isEmpty == false ? headerInfo?.itemTypeLabel : "Job"
        let slideLabel = slideIndicatorLabel(for: chunk)
        let timelineLabel = audioTimelineLabel(for: chunk)
        let showHeaderContent = !isHeaderCollapsed
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)

        // Main header row with channel bug, title/author, and timeline
        let mainHeaderRow = HStack(alignment: .top, spacing: 12) {
            if showHeaderContent {
                PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                if let headerInfo {
                    infoBadgeView(info: headerInfo, chunk: chunk)
                }
            }
            Spacer(minLength: 12)
            if showHeaderContent || isTV {
                VStack(alignment: .trailing, spacing: 6) {
                    if showHeaderContent {
                        // iPhone portrait: stack progress pills vertically
                        // Others: horizontal row
                        #if os(iOS)
                        if isPhonePortrait {
                            VStack(alignment: .trailing, spacing: 3) {
                                if let slideLabel {
                                    slideIndicatorView(label: slideLabel)
                                }
                                if let timelineLabel {
                                    audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
                                }
                            }
                        } else {
                            HStack(spacing: 6) {
                                if let slideLabel {
                                    slideIndicatorView(label: slideLabel)
                                }
                                if let timelineLabel {
                                    audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
                                }
                            }
                        }
                        #else
                        // Sentence progress and playing time in one row
                        HStack(spacing: 6) {
                            if let slideLabel {
                                slideIndicatorView(label: slideLabel)
                            }
                            if let timelineLabel {
                                audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
                            }
                        }
                        #endif
                    } else {
                        // Header collapsed - show music pill and timeline in a row
                        HStack(spacing: 6) {
                            musicPillView
                            if let timelineLabel {
                                audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
                            }
                        }
                    }
                    #if os(tvOS)
                    tvHeaderTogglePill
                    #endif
                }
            }
        }

        // For iPhone, wrap in VStack to add full-width pills row below
        let headerView: AnyView = {
            #if os(iOS)
            if isPhone, showHeaderContent, let info = headerInfo, !info.languageFlags.isEmpty {
                return AnyView(
                    VStack(alignment: .leading, spacing: 8) {
                        mainHeaderRow
                        // Full-width pills row for iPhone
                        HStack(spacing: 0) {
                            PlayerLanguageFlagRow(
                                flags: info.languageFlags,
                                modelLabel: nil,
                                isTV: false,
                                sizeScale: infoPillScale,
                                activeRoles: activeRoles,
                                availableRoles: availableRoles,
                                onToggleRole: { role in
                                    toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
                                },
                                showConnector: false
                            )
                            Spacer(minLength: 8)
                            musicPillView
                            Spacer(minLength: 8)
                            speedPillView
                            Spacer(minLength: 8)
                            jumpPillView
                            Spacer(minLength: 8)
                            searchPillView
                            Spacer(minLength: 8)
                            bookmarkRibbonPillView
                        }
                    }
                )
            }
            #endif
            return AnyView(mainHeaderRow)
        }()

        let styledHeaderView = headerView
            .padding(.horizontal, isPhonePortrait ? 16 : (isPhone ? 12 : 6))
            .padding(.top, 6)
            .frame(maxWidth: .infinity, alignment: .topLeading)
            .allowsHitTesting(true)
        #if os(tvOS)
        let finalView = styledHeaderView
            .onLongPressGesture(minimumDuration: 0.6) {
                toggleHeaderCollapsed()
            }
            .zIndex(1)
        #else
        let finalView = styledHeaderView
            .zIndex(1)
        #endif
        return headerMagnifyWrapper(finalView)
    }

    func infoBadgeView(info: InteractivePlayerHeaderInfo, chunk: InteractiveChunk) -> some View {
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        return VStack(alignment: .leading, spacing: isPhonePortrait ? 6 : 0) {
            HStack(alignment: .top, spacing: 8) {
                if info.coverURL != nil || info.secondaryCoverURL != nil {
                    PlayerCoverStackView(
                        primaryURL: info.coverURL,
                        secondaryURL: info.secondaryCoverURL,
                        width: infoCoverWidth,
                        height: infoCoverHeight,
                        isTV: isTV
                    )
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text(info.title.isEmpty ? "Untitled" : info.title)
                        .font(infoTitleFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                    if !info.author.isEmpty {
                        Text(info.author)
                            .font(infoMetaFont)
                            .foregroundStyle(Color.white.opacity(0.75))
                            .lineLimit(1)
                            .minimumScaleFactor(0.85)
                    }
                    // On iPad and tvOS, show flags inline with title/author
                    // iPhone uses a separate full-width row for better spacing
                    if !isPhone, !info.languageFlags.isEmpty {
                        #if os(tvOS)
                        HStack(spacing: 8 * infoPillScale) {
                            PlayerLanguageFlagRow(
                                flags: info.languageFlags,
                                modelLabel: nil,
                                isTV: isTV,
                                sizeScale: infoPillScale,
                                activeRoles: activeRoles,
                                availableRoles: availableRoles,
                                onToggleRole: { role in
                                    toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
                                },
                                showConnector: !isPhone
                            )
                            musicPillView
                            speedPillView
                            jumpPillView
                            searchPillView
                            bookmarkRibbonPillView
                        }
                        .focusScope(headerControlsNamespace)
                        .focused($focusedArea, equals: .controls)
                        #else
                        HStack(spacing: 8 * infoPillScale) {
                            PlayerLanguageFlagRow(
                                flags: info.languageFlags,
                                modelLabel: nil,
                                isTV: isTV,
                                sizeScale: infoPillScale,
                                activeRoles: activeRoles,
                                availableRoles: availableRoles,
                                onToggleRole: { role in
                                    toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
                                },
                                showConnector: !isPhone
                            )
                            musicPillView
                            speedPillView
                            jumpPillView
                            searchPillView
                            bookmarkRibbonPillView
                        }
                        #endif
                    }
                }
            }
            // iPhone pills row is now handled in playerInfoOverlay for full-width layout
        }
    }

    func slideIndicatorView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.85))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.6))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )
            )
    }

    func audioTimelineView(label: String, onTap: (() -> Void)? = nil) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.75))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.5))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.18), lineWidth: 1)
                    )
            )
            .contentShape(Capsule())
            .onTapGesture {
                onTap?()
            }
    }

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
            // while still supporting pinch-to-zoom on non-interactive areas
            content.simultaneousGesture(headerMagnifyGesture, including: .subviews)
        } else {
            content
        }
        #else
        content
        #endif
    }

    #if os(iOS)
    var headerMagnifyGesture: some Gesture {
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
        return PlayerInfoMetrics.badgeHeight(isTV: true) + 24
        #else
        let baseHeight = PlayerInfoMetrics.badgeHeight(isTV: false) * infoHeaderScale
        let padding = isPad ? 20 * infoHeaderScale : 16
        return baseHeight + padding
        #endif
    }

    var transcriptTopPadding: CGFloat {
        #if os(iOS) || os(tvOS)
        // On iPhone, reduce padding when bubble is shown (header is always hidden)
        if isPhone && linguistBubble != nil {
            return 8
        }
        // On iPad with bubble, respect the header collapsed state
        return isHeaderCollapsed ? 8 : infoHeaderReservedHeight
        #else
        return infoHeaderReservedHeight
        #endif
    }

    var shouldShowHeaderOverlay: Bool {
        // On iPhone, always hide header when bubble is shown to maximize screen space
        // On iPad, allow header to be toggled even when bubble is shown
        if isPhone && linguistBubble != nil {
            return false
        }
        return !isHeaderCollapsed
    }

    @ViewBuilder
    var headerToggleButton: some View {
        #if os(iOS)
        // Show timeline pill when header is collapsed OR when bubble is shown (auto-minimized)
        let showButton = isHeaderCollapsed || ((isPhone || isPad) && linguistBubble != nil)
        if showButton, let chunk = viewModel.selectedChunk {
            let timelineLabel = audioTimelineLabel(for: chunk)
            // Position pills in top-right corner using VStack/HStack with Spacers
            // The Spacers don't have content shape so touches pass through
            VStack(spacing: 0) {
                HStack(spacing: 6) {
                    Spacer(minLength: 0)
                    // Music pill always visible when header is collapsed
                    musicPillView
                    // Timeline pill (tap to expand header)
                    if let timelineLabel {
                        audioTimelineView(label: timelineLabel, onTap: toggleHeaderCollapsed)
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
    /// Non-focusable toggle pill - header show/hide is handled by long press on middle button
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

    func toggleHeaderCollapsed() {
        withAnimation(.easeInOut(duration: 0.2)) {
            isHeaderCollapsed.toggle()
        }
    }
}
