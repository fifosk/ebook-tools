import SwiftUI

// MARK: - Header Overlay

extension InteractivePlayerView {

    func playerInfoOverlay(for chunk: InteractiveChunk) -> some View {
        let variant = resolveInfoVariant()
        let rawLabel = headerInfo?.itemTypeLabel.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let label = rawLabel.isEmpty ? "Job" : rawLabel
        let slideLabel = slideIndicatorLabel(for: chunk)
        let timelineLabel = audioTimelineLabel(for: chunk)
        let showHeaderContent = !isHeaderCollapsed
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)

        let styledHeaderView = playerInfoHeaderContent(
            for: chunk,
            variant: variant,
            label: label,
            slideLabel: slideLabel,
            timelineLabel: timelineLabel,
            showHeaderContent: showHeaderContent,
            availableRoles: availableRoles,
            activeRoles: activeRoles
        )
            .padding(.horizontal, isPhonePortrait ? 16 : (isPhone ? 12 : 6))
            .padding(.top, 6)
            .frame(maxWidth: .infinity, alignment: .topLeading)
            .allowsHitTesting(true)
        #if os(tvOS)
        let finalView = styledHeaderView
            .onLongPressGesture(minimumDuration: 0.6, perform: handleHeaderLongPress)
            .zIndex(1)
        #else
        let finalView = styledHeaderView
            .zIndex(1)
        #endif
        return headerMagnifyWrapper(finalView)
    }

    @ViewBuilder
    private func playerInfoHeaderContent(
        for chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String,
        slideLabel: String?,
        timelineLabel: String?,
        showHeaderContent: Bool,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        #if os(iOS)
        if isPhone, showHeaderContent {
            VStack(alignment: .leading, spacing: 8) {
                playerInfoHeaderRow(
                    for: chunk,
                    variant: variant,
                    label: label,
                    slideLabel: slideLabel,
                    timelineLabel: timelineLabel,
                    showHeaderContent: showHeaderContent
                )
                phoneHeaderControlsRow(
                    info: headerInfo,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles
                )
            }
        } else {
            playerInfoHeaderRow(
                for: chunk,
                variant: variant,
                label: label,
                slideLabel: slideLabel,
                timelineLabel: timelineLabel,
                showHeaderContent: showHeaderContent
            )
        }
        #else
        playerInfoHeaderRow(
            for: chunk,
            variant: variant,
            label: label,
            slideLabel: slideLabel,
            timelineLabel: timelineLabel,
            showHeaderContent: showHeaderContent
        )
        #endif
    }

    private func playerInfoHeaderRow(
        for chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String,
        slideLabel: String?,
        timelineLabel: String?,
        showHeaderContent: Bool
    ) -> some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: headerPrimarySpacing) {
                if showHeaderContent {
                    headerIdentityCluster(
                        info: headerInfo,
                        chunk: chunk,
                        variant: variant,
                        label: label
                    )
                }
                Spacer(minLength: headerPrimarySpacing)
                if showHeaderContent || isTV {
                    headerProgressStack(
                        slideLabel: slideLabel,
                        timelineLabel: timelineLabel,
                        showHeaderContent: showHeaderContent
                    )
                }
            }

            VStack(alignment: .leading, spacing: 8 * min(infoHeaderScale, 1.4)) {
                if showHeaderContent {
                    headerIdentityCluster(
                        info: headerInfo,
                        chunk: chunk,
                        variant: variant,
                        label: label
                    )
                }
                if showHeaderContent || isTV {
                    headerProgressStack(
                        slideLabel: slideLabel,
                        timelineLabel: timelineLabel,
                        showHeaderContent: showHeaderContent
                    )
                    .frame(maxWidth: .infinity, alignment: .trailing)
                }
            }
        }
        .padding(.horizontal, showHeaderContent ? headerGlassHorizontalPadding : 0)
        .padding(.vertical, showHeaderContent ? headerGlassVerticalPadding : 0)
        .background {
            if showHeaderContent && headerInfo == nil {
                PlayerHeaderGlassPanelBackground(cornerRadius: headerGlassCornerRadius)
            }
        }
    }

    @ViewBuilder
    private func headerIdentityCluster(
        info: InteractivePlayerHeaderInfo?,
        chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String
    ) -> some View {
        if let info {
            infoBadgeView(info: info, chunk: chunk, variant: variant, label: label)
        } else {
            PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
        }
    }

    private func headerProgressStack(
        slideLabel: String?,
        timelineLabel: String?,
        showHeaderContent: Bool
    ) -> some View {
        VStack(alignment: .trailing, spacing: 6) {
            if showHeaderContent {
                headerProgressPills(slideLabel: slideLabel, timelineLabel: timelineLabel)
            } else {
                HStack(spacing: 6) {
                    musicPillView
                    if let timelineLabel {
                        audioTimelineView(label: timelineLabel)
                    }
                }
            }
            #if os(tvOS)
            tvHeaderTogglePill
            #endif
        }
    }

    @ViewBuilder
    private func headerProgressPills(slideLabel: String?, timelineLabel: String?) -> some View {
        #if os(iOS)
        if isPhonePortrait {
            VStack(alignment: .trailing, spacing: 3) {
                if let slideLabel {
                    slideIndicatorView(label: slideLabel)
                }
                if let timelineLabel {
                    audioTimelineView(label: timelineLabel)
                }
            }
        } else {
            headerProgressPillRow(slideLabel: slideLabel, timelineLabel: timelineLabel)
        }
        #else
        headerProgressPillRow(slideLabel: slideLabel, timelineLabel: timelineLabel)
        #endif
    }

    private func headerProgressPillRow(slideLabel: String?, timelineLabel: String?) -> some View {
        HStack(spacing: 6) {
            if let slideLabel {
                slideIndicatorView(label: slideLabel)
            }
            if let timelineLabel {
                audioTimelineView(label: timelineLabel)
            }
        }
    }

    private func headerLanguageFlagRow(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>,
        showConnector: Bool
    ) -> some View {
        PlayerLanguageFlagRow(
            flags: info.languageFlags,
            modelLabel: nil,
            isTV: isTV,
            sizeScale: infoPillScale,
            activeRoles: activeRoles,
            availableRoles: availableRoles,
            onToggleRole: { role in
                handleHeaderLanguageRoleToggle(role, for: chunk, availableRoles: availableRoles)
            },
            showConnector: showConnector
        )
    }

    #if os(iOS)
    private func phoneHeaderControlsRow(
        info: InteractivePlayerHeaderInfo?,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        HStack(spacing: 0) {
            if let info, !info.languageFlags.isEmpty {
                headerLanguageFlagRow(
                    info: info,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles,
                    showConnector: false
                )
                Spacer(minLength: 8)
            }
            musicPillView
            Spacer(minLength: 8)
            speedPillView
            Spacer(minLength: 8)
            sleepTimerPillView
            Spacer(minLength: 8)
            jumpPillView
            Spacer(minLength: 8)
            searchPillView
            Spacer(minLength: 8)
            bookmarkRibbonPillView
        }
    }
    #endif

    func infoBadgeView(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        variant: PlayerChannelVariant,
        label: String
    ) -> some View {
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        return InteractivePlayerHeaderIdentityBanner(
            info: info,
            variant: variant,
            label: label,
            isTV: isTV,
            isPhone: isPhone,
            isPhonePortrait: isPhonePortrait,
            infoHeaderScale: infoHeaderScale,
            infoPillScale: infoPillScale,
            infoCoverWidth: infoCoverWidth,
            infoCoverHeight: infoCoverHeight,
            titleFont: infoTitleFont,
            metaFont: infoMetaFont,
            eyebrowFont: infoEyebrowFont,
            contentSpacing: headerIdentityContentSpacing,
            horizontalPadding: headerIdentityHorizontalPadding,
            verticalPadding: headerIdentityVerticalPadding,
            cornerRadius: headerIdentityCornerRadius,
            maxWidth: headerIdentityMaxWidth,
            coverCornerRadius: headerCoverCornerRadius
        ) {
            #if os(tvOS)
            headerInlineControlsRow(
                info: info,
                chunk: chunk,
                availableRoles: availableRoles,
                activeRoles: activeRoles
            )
            .focusScope(headerControlsNamespace)
            .focused($focusedArea, equals: .controls)
            #else
            headerInlineControlsRow(
                info: info,
                chunk: chunk,
                availableRoles: availableRoles,
                activeRoles: activeRoles
            )
            #endif
        }
    }

    @ViewBuilder
    private func headerInlineControlsRow(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        #if os(tvOS)
        headerInlineControlsContent(
            info: info,
            chunk: chunk,
            availableRoles: availableRoles,
            activeRoles: activeRoles
        )
        #else
        if isPad {
            ViewThatFits(in: .horizontal) {
                headerInlineControlsContent(
                    info: info,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles
                )
                ScrollView(.horizontal, showsIndicators: false) {
                    headerInlineControlsContent(
                        info: info,
                        chunk: chunk,
                        availableRoles: availableRoles,
                        activeRoles: activeRoles
                    )
                }
            }
        } else {
            headerInlineControlsContent(
                info: info,
                chunk: chunk,
                availableRoles: availableRoles,
                activeRoles: activeRoles
            )
        }
        #endif
    }

    private func headerInlineControlsContent(
        info: InteractivePlayerHeaderInfo,
        chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>,
        activeRoles: Set<LanguageFlagRole>
    ) -> some View {
        HStack(spacing: 8 * infoPillScale) {
            if !info.languageFlags.isEmpty {
                headerLanguageFlagRow(
                    info: info,
                    chunk: chunk,
                    availableRoles: availableRoles,
                    activeRoles: activeRoles,
                    showConnector: !isPhone
                )
            }
            musicPillView
            speedPillView
            sleepTimerPillView
            jumpPillView
            searchPillView
            bookmarkRibbonPillView
        }
    }

    private func handleHeaderLanguageRoleToggle(
        _ role: LanguageFlagRole,
        for chunk: InteractiveChunk,
        availableRoles: Set<LanguageFlagRole>
    ) {
        toggleHeaderAudioRole(role, for: chunk, availableRoles: availableRoles)
    }

    func slideIndicatorView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.85))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(PlayerHeaderPillBackground(isActive: true, isProminent: true))
    }

    func audioTimelineView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.75))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(PlayerHeaderPillBackground(isActive: false))
            .contentShape(Capsule())
            .onTapGesture(perform: handleAudioTimelineTap)
    }

    private var headerGlassHorizontalPadding: CGFloat {
        (isTV ? 14 : 10) * min(infoHeaderScale, 1.6)
    }

    private var headerGlassVerticalPadding: CGFloat {
        (isTV ? 12 : 8) * min(infoHeaderScale, 1.6)
    }

    private var headerGlassCornerRadius: CGFloat {
        (isTV ? 26 : 18) * min(infoHeaderScale, 1.35)
    }

    private var headerPrimarySpacing: CGFloat {
        (isTV ? 14 : 10) * min(infoHeaderScale, 1.45)
    }

    private var headerIdentityContentSpacing: CGFloat {
        (isTV ? 16 : 12) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityHorizontalPadding: CGFloat {
        (isTV ? 16 : 12) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityVerticalPadding: CGFloat {
        (isTV ? 12 : 10) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityCornerRadius: CGFloat {
        (isTV ? 22 : 16) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityMaxWidth: CGFloat? {
        if isTV { return 980 }
        if isPad { return 920 }
        if isPhonePortrait { return nil }
        return 620
    }

    private var headerCoverCornerRadius: CGFloat {
        (isTV ? 10 : 8) * min(infoHeaderScale, 1.35)
    }

}

private struct InteractivePlayerHeaderIdentityBanner<Controls: View>: View {
    let info: InteractivePlayerHeaderInfo
    let variant: PlayerChannelVariant
    let label: String
    let isTV: Bool
    let isPhone: Bool
    let isPhonePortrait: Bool
    let infoHeaderScale: CGFloat
    let infoPillScale: CGFloat
    let infoCoverWidth: CGFloat
    let infoCoverHeight: CGFloat
    let titleFont: Font
    let metaFont: Font
    let eyebrowFont: Font
    let contentSpacing: CGFloat
    let horizontalPadding: CGFloat
    let verticalPadding: CGFloat
    let cornerRadius: CGFloat
    let maxWidth: CGFloat?
    let coverCornerRadius: CGFloat
    let controls: Controls

    init(
        info: InteractivePlayerHeaderInfo,
        variant: PlayerChannelVariant,
        label: String,
        isTV: Bool,
        isPhone: Bool,
        isPhonePortrait: Bool,
        infoHeaderScale: CGFloat,
        infoPillScale: CGFloat,
        infoCoverWidth: CGFloat,
        infoCoverHeight: CGFloat,
        titleFont: Font,
        metaFont: Font,
        eyebrowFont: Font,
        contentSpacing: CGFloat,
        horizontalPadding: CGFloat,
        verticalPadding: CGFloat,
        cornerRadius: CGFloat,
        maxWidth: CGFloat?,
        coverCornerRadius: CGFloat,
        @ViewBuilder controls: () -> Controls
    ) {
        self.info = info
        self.variant = variant
        self.label = label
        self.isTV = isTV
        self.isPhone = isPhone
        self.isPhonePortrait = isPhonePortrait
        self.infoHeaderScale = infoHeaderScale
        self.infoPillScale = infoPillScale
        self.infoCoverWidth = infoCoverWidth
        self.infoCoverHeight = infoCoverHeight
        self.titleFont = titleFont
        self.metaFont = metaFont
        self.eyebrowFont = eyebrowFont
        self.contentSpacing = contentSpacing
        self.horizontalPadding = horizontalPadding
        self.verticalPadding = verticalPadding
        self.cornerRadius = cornerRadius
        self.maxWidth = maxWidth
        self.coverCornerRadius = coverCornerRadius
        self.controls = controls()
    }

    var body: some View {
        HStack(alignment: .center, spacing: contentSpacing) {
            PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                .layoutPriority(3)
            headerCoverArtworkView(info: info)
                .layoutPriority(2)
            VStack(alignment: .leading, spacing: 7 * min(infoHeaderScale, 1.25)) {
                VStack(alignment: .leading, spacing: 3 * min(infoHeaderScale, 1.2)) {
                    Text(headerTitle(for: info))
                        .font(titleFont)
                        .foregroundStyle(Color.white)
                        .lineLimit(isTV ? 2 : (isPhonePortrait ? 2 : 1))
                        .minimumScaleFactor(0.82)
                    if let subtitle = headerIdentitySubtitle(for: info) {
                        Text(subtitle)
                            .font(metaFont)
                            .foregroundStyle(Color.white.opacity(0.74))
                            .lineLimit(1)
                            .minimumScaleFactor(0.82)
                    }
                }
                headerMetadataPillRow(info: info)
                if !isPhone {
                    controls
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .layoutPriority(1)
        }
        .padding(.horizontal, horizontalPadding)
        .padding(.vertical, verticalPadding)
        .frame(maxWidth: maxWidth, alignment: .leading)
        .background(PlayerHeaderIdentityBannerBackground(cornerRadius: cornerRadius))
        .overlay(alignment: .topTrailing) {
            headerIdentitySheen
        }
        .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        .accessibilityIdentifier("interactiveReaderHeaderIdentityBanner")
    }

    @ViewBuilder
    private func headerCoverArtworkView(info: InteractivePlayerHeaderInfo) -> some View {
        Group {
            if info.coverURL != nil || info.secondaryCoverURL != nil {
                PlayerCoverStackView(
                    primaryURL: info.coverURL,
                    secondaryURL: info.secondaryCoverURL,
                    width: infoCoverWidth,
                    height: infoCoverHeight,
                    isTV: isTV
                )
            } else {
                headerCoverPlaceholder(info: info)
            }
        }
        .padding(2 * min(infoHeaderScale, 1.4))
        .background(
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .fill(Color.black.opacity(0.24))
        )
        .overlay(
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .strokeBorder(Color.white.opacity(0.16), lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.30), radius: 12, x: 0, y: 7)
        .accessibilityIdentifier("interactiveReaderHeaderCover")
    }

    private func headerCoverPlaceholder(info: InteractivePlayerHeaderInfo) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.18),
                            Color.white.opacity(0.06)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            VStack(spacing: 2 * min(infoHeaderScale, 1.2)) {
                Image(systemName: itemTypeSystemImage(for: info.itemTypeLabel))
                    .font(.system(size: max(13, infoCoverHeight * 0.26), weight: .semibold))
                Text(headerCoverInitial(for: info))
                    .font(.system(size: max(12, infoCoverHeight * 0.22), weight: .bold))
                    .lineLimit(1)
            }
            .foregroundStyle(Color.white.opacity(0.74))
        }
        .frame(width: infoCoverWidth, height: infoCoverHeight)
        .overlay(
            RoundedRectangle(cornerRadius: coverCornerRadius, style: .continuous)
                .stroke(Color.white.opacity(0.22), lineWidth: 1)
        )
    }

    @ViewBuilder
    private func headerMetadataPillRow(info: InteractivePlayerHeaderInfo) -> some View {
        let itemType = info.itemTypeLabel.trimmingCharacters(in: .whitespacesAndNewlines)
        let translationModel = info.translationModel?.trimmingCharacters(in: .whitespacesAndNewlines)
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 6 * min(infoPillScale, 1.35)) {
                headerMetadataPills(itemType: itemType, translationModel: translationModel)
            }
            VStack(alignment: .leading, spacing: 4 * min(infoPillScale, 1.2)) {
                headerMetadataPills(itemType: itemType, translationModel: translationModel)
            }
        }
    }

    @ViewBuilder
    private func headerMetadataPills(itemType: String, translationModel: String?) -> some View {
        if !itemType.isEmpty {
            headerMetadataPill(
                label: itemType.uppercased(),
                systemImage: itemTypeSystemImage(for: itemType)
            )
        }
        if let translationModel, !translationModel.isEmpty {
            headerMetadataPill(label: translationModel, systemImage: "sparkles")
        }
    }

    private func headerMetadataPill(label: String, systemImage: String) -> some View {
        HStack(spacing: 4 * min(infoPillScale, 1.4)) {
            Image(systemName: systemImage)
                .font(eyebrowFont)
            Text(label)
                .font(eyebrowFont)
                .lineLimit(1)
                .minimumScaleFactor(0.78)
        }
        .foregroundStyle(Color.white.opacity(0.82))
        .padding(.horizontal, 8 * min(infoPillScale, 1.4))
        .padding(.vertical, 3 * min(infoPillScale, 1.4))
        .background(PlayerHeaderPillBackground(isActive: true, isProminent: true))
    }

    private var headerIdentitySheen: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(
                LinearGradient(
                    colors: [
                        Color.white.opacity(0.12),
                        Color.white.opacity(0.02),
                        Color.clear
                    ],
                    startPoint: .topTrailing,
                    endPoint: .bottomLeading
                )
            )
            .frame(
                width: (isTV ? 260 : 160) * min(infoHeaderScale, 1.2),
                height: (isTV ? 80 : 52) * min(infoHeaderScale, 1.2)
            )
            .offset(x: (isTV ? 44 : 28) * min(infoHeaderScale, 1.2), y: -(isTV ? 24 : 16) * min(infoHeaderScale, 1.2))
            .allowsHitTesting(false)
    }

    private func itemTypeSystemImage(for itemType: String) -> String {
        let normalized = itemType.lowercased()
        if normalized.contains("subtitle") || normalized.contains("caption") {
            return "captions.bubble"
        }
        if normalized.contains("video") || normalized.contains("youtube") || normalized.contains("tv") {
            return "play.rectangle"
        }
        if normalized.contains("job") {
            return "briefcase"
        }
        return "book.closed"
    }

    private func headerTitle(for info: InteractivePlayerHeaderInfo) -> String {
        let title = info.title.trimmingCharacters(in: .whitespacesAndNewlines)
        return title.isEmpty ? "Untitled" : title
    }

    private func headerIdentitySubtitle(for info: InteractivePlayerHeaderInfo) -> String? {
        let author = info.author.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !author.isEmpty else {
            return nil
        }
        return "by \(author)"
    }

    private func headerCoverInitial(for info: InteractivePlayerHeaderInfo) -> String {
        String(headerTitle(for: info).prefix(1)).uppercased()
    }
}
