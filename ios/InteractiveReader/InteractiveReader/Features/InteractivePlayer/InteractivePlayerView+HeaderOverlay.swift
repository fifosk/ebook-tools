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
        HStack(alignment: .top, spacing: 12) {
            if showHeaderContent {
                PlayerChannelBugView(variant: variant, label: label, sizeScale: infoHeaderScale)
                if let headerInfo {
                    infoBadgeView(info: headerInfo, chunk: chunk)
                }
            }
            Spacer(minLength: 12)
            if showHeaderContent || isTV {
                headerProgressStack(
                    slideLabel: slideLabel,
                    timelineLabel: timelineLabel,
                    showHeaderContent: showHeaderContent
                )
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
            // iPhone pills row is now handled in playerInfoOverlay for full-width layout
        }
    }

    private func headerInlineControlsRow(
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
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.6))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )
            )
    }

    func audioTimelineView(label: String) -> some View {
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
            .onTapGesture(perform: handleAudioTimelineTap)
    }

}
