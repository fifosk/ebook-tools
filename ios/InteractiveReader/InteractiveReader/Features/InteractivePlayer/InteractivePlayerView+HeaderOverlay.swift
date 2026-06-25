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
        HStack(alignment: .top, spacing: 10 * min(infoHeaderScale, 1.6)) {
            if showHeaderContent {
                PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                if let headerInfo {
                    infoBadgeView(info: headerInfo, chunk: chunk)
                }
            }
            Spacer(minLength: 10)
            if showHeaderContent || isTV {
                headerProgressStack(
                    slideLabel: slideLabel,
                    timelineLabel: timelineLabel,
                    showHeaderContent: showHeaderContent
                )
            }
        }
        .padding(.horizontal, showHeaderContent ? headerGlassHorizontalPadding : 0)
        .padding(.vertical, showHeaderContent ? headerGlassVerticalPadding : 0)
        .background {
            if showHeaderContent {
                PlayerHeaderGlassPanelBackground(cornerRadius: headerGlassCornerRadius)
            }
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

    func infoBadgeView(info: InteractivePlayerHeaderInfo, chunk: InteractiveChunk) -> some View {
        let availableRoles = availableAudioRoles(for: chunk)
        let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)
        return VStack(alignment: .leading, spacing: isPhonePortrait ? 6 : 0) {
            HStack(alignment: .center, spacing: 10 * min(infoHeaderScale, 1.4)) {
                headerCoverArtworkView(info: info)
                VStack(alignment: .leading, spacing: 6 * min(infoHeaderScale, 1.35)) {
                    headerMetadataPillRow(info: info)
                    Text(headerTitle(for: info))
                        .font(infoTitleFont)
                        .foregroundStyle(Color.white)
                        .lineLimit(isTV ? 2 : 1)
                        .minimumScaleFactor(0.85)
                    if let subtitle = headerIdentitySubtitle(for: info) {
                        Text(subtitle)
                            .font(infoMetaFont)
                            .foregroundStyle(Color.white.opacity(0.72))
                            .lineLimit(1)
                            .minimumScaleFactor(0.85)
                    }
                    // On iPad and tvOS, show flags inline with title/author
                    // iPhone uses a separate full-width row for better spacing
                    if !isPhone {
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
            }
            .padding(.horizontal, headerIdentityHorizontalPadding)
            .padding(.vertical, headerIdentityVerticalPadding)
            .background(PlayerHeaderIdentityBannerBackground(cornerRadius: headerIdentityCornerRadius))
            // iPhone pills row is now handled in playerInfoOverlay for full-width layout
        }
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
            RoundedRectangle(cornerRadius: headerCoverCornerRadius, style: .continuous)
                .fill(Color.black.opacity(0.18))
        )
        .shadow(color: Color.black.opacity(0.22), radius: 10, x: 0, y: 6)
    }

    private func headerCoverPlaceholder(info: InteractivePlayerHeaderInfo) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: headerCoverCornerRadius, style: .continuous)
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
            RoundedRectangle(cornerRadius: headerCoverCornerRadius, style: .continuous)
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

    private func headerMetadataPill(label: String, systemImage: String) -> some View {
        HStack(spacing: 4 * min(infoPillScale, 1.4)) {
            Image(systemName: systemImage)
                .font(infoEyebrowFont)
            Text(label)
                .font(infoEyebrowFont)
                .lineLimit(1)
                .minimumScaleFactor(0.78)
        }
        .foregroundStyle(Color.white.opacity(0.82))
        .padding(.horizontal, 8 * min(infoPillScale, 1.4))
        .padding(.vertical, 3 * min(infoPillScale, 1.4))
        .background(PlayerHeaderPillBackground(isActive: true, isProminent: true))
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

    private var headerIdentityHorizontalPadding: CGFloat {
        (isTV ? 14 : 10) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityVerticalPadding: CGFloat {
        (isTV ? 10 : 8) * min(infoHeaderScale, 1.35)
    }

    private var headerIdentityCornerRadius: CGFloat {
        (isTV ? 22 : 16) * min(infoHeaderScale, 1.35)
    }

    private var headerCoverCornerRadius: CGFloat {
        (isTV ? 10 : 8) * min(infoHeaderScale, 1.35)
    }

}
