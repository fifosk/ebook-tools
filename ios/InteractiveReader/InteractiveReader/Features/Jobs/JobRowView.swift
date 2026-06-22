import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct JobRowView: View {
    @EnvironmentObject var appState: AppState
    let job: PipelineStatusResponse
    let resumeStatus: LibraryRowView.ResumeStatus
    var usesDarkBackground: Bool = false

    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    #if os(tvOS)
    @Environment(\.isFocused) private var isFocused
    @EnvironmentObject var offlineStore: OfflineMediaStore
    #endif

    var body: some View {
        #if os(tvOS)
        landscapeLayout
        #else
        if isCompactWidth {
            compactLayout
        } else {
            landscapeLayout
        }
        #endif
    }

    // MARK: - Compact Layout (iPhone Portrait)

    private var compactLayout: some View {
        rowLayout(
            accessoryStyle: .compact,
            titleLineLimit: 2,
            titleScaleFactor: 0.9,
            descriptionLineLimit: 2,
            badgeSpacing: 6,
            titleStyle: AnyShapeStyle(.primary),
            secondaryTextStyle: AnyShapeStyle(.secondary),
            tertiaryTextStyle: AnyShapeStyle(.tertiary),
            accessorySecondaryTextColor: .secondary
        )
    }

    // MARK: - Landscape Layout (iPad / tvOS)

    private var landscapeLayout: some View {
        rowLayout(
            accessoryStyle: .landscape,
            titleLineLimit: titleLineLimit,
            titleScaleFactor: titleScaleFactor,
            descriptionLineLimit: 1,
            badgeSpacing: 8,
            titleStyle: AnyShapeStyle(titleColor),
            secondaryTextStyle: AnyShapeStyle(secondaryTextColor),
            tertiaryTextStyle: AnyShapeStyle(tertiaryTextColor),
            accessorySecondaryTextColor: secondaryTextColor
        )
    }

    private func rowLayout(
        accessoryStyle: JobRowAccessoryStyle,
        titleLineLimit: Int,
        titleScaleFactor: CGFloat,
        descriptionLineLimit: Int,
        badgeSpacing: CGFloat,
        titleStyle: AnyShapeStyle,
        secondaryTextStyle: AnyShapeStyle,
        tertiaryTextStyle: AnyShapeStyle,
        accessorySecondaryTextColor: Color
    ) -> some View {
        JobRowLayout(
            coverURL: coverURL,
            variant: jobVariant,
            coverHeight: coverHeight,
            rowSpacing: rowSpacing,
            rowPadding: rowPadding,
            title: jobTitle,
            summaryText: summaryText,
            descriptionText: descriptionText,
            languageFlags: languageFlags,
            statusIcon: statusGlyph.icon,
            statusLabel: statusGlyph.label,
            statusColor: statusColor,
            resumeStatus: resumeStatus,
            progressLabel: progressLabel,
            progressValue: progressValue,
            progressTint: progressTint,
            titleFont: titleFont,
            summaryFont: summaryFont,
            metaFont: metaFont,
            statusGlyphFont: statusGlyphFont,
            textSpacing: textSpacing,
            titleLineLimit: titleLineLimit,
            titleScaleFactor: titleScaleFactor,
            descriptionLineLimit: descriptionLineLimit,
            badgeSpacing: badgeSpacing,
            titleStyle: titleStyle,
            secondaryTextStyle: secondaryTextStyle,
            tertiaryTextStyle: tertiaryTextStyle,
            accessoryJobId: job.jobId,
            accessoryIsFinished: job.isFinishedForDisplay,
            accessoryStyle: accessoryStyle,
            accessorySecondaryTextColor: accessorySecondaryTextColor,
            isSynced: isJobSynced,
            isFocused: isRowFocused
        )
    }

    // MARK: - Layout Helpers

    private var isCompactWidth: Bool {
        #if os(iOS)
        return horizontalSizeClass == .compact
        #else
        return false
        #endif
    }

    private var isJobSynced: Bool {
        #if os(tvOS)
        offlineStore.status(for: job.jobId, kind: .job).isSynced
        #else
        false
        #endif
    }

    private var isRowFocused: Bool {
        #if os(tvOS)
        isFocused
        #else
        false
        #endif
    }

    private var titleFont: Font {
        PlatformTypography.scaledFont(.headline)
    }

    private var metaFont: Font {
        PlatformTypography.scaledFont(.caption1)
    }

    private var summaryFont: Font {
        PlatformTypography.scaledFont(.subheadline)
    }

    private var titleLineLimit: Int {
        #if os(tvOS)
        return 1
        #else
        return 2
        #endif
    }

    private var titleScaleFactor: CGFloat {
        #if os(tvOS)
        return 0.9
        #else
        return 0.95
        #endif
    }

    private var rowSpacing: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return 10
        #endif
    }

    private var textSpacing: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 3
        #endif
    }

    private var rowPadding: CGFloat {
        #if os(tvOS)
        return 6
        #else
        return 5
        #endif
    }

    // MARK: - Text Colors

    private var titleColor: Color {
        #if os(tvOS)
        PlatformColors.rowTitleColor(isFocused: isFocused)
        #else
        PlatformColors.rowTitleColor(usesDarkBackground: usesDarkBackground)
        #endif
    }

    private var secondaryTextColor: Color {
        #if os(tvOS)
        PlatformColors.rowSecondaryColor(isFocused: isFocused)
        #else
        PlatformColors.rowSecondaryColor(usesDarkBackground: usesDarkBackground)
        #endif
    }

    private var tertiaryTextColor: Color {
        #if os(tvOS)
        PlatformColors.rowTertiaryColor(isFocused: isFocused)
        #else
        PlatformColors.rowTertiaryColor(usesDarkBackground: usesDarkBackground)
        #endif
    }

    private var coverHeight: CGFloat {
        CoverMetrics.rowHeight(isTV: isTV)
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

}
