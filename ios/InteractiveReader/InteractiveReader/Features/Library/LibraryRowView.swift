import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct LibraryRowView: View {
    let item: LibraryItem
    let coverURL: URL?
    let resumeStatus: ResumeStatus
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
        accessoryStyle: LibraryRowAccessoryStyle,
        titleLineLimit: Int,
        titleScaleFactor: CGFloat,
        descriptionLineLimit: Int,
        badgeSpacing: CGFloat,
        titleStyle: AnyShapeStyle,
        secondaryTextStyle: AnyShapeStyle,
        tertiaryTextStyle: AnyShapeStyle,
        accessorySecondaryTextColor: Color
    ) -> some View {
        LibraryRowLayout(
            coverURL: coverURL,
            variant: itemVariant,
            coverHeight: coverHeight,
            rowSpacing: rowSpacing,
            rowPadding: rowPadding,
            title: displayTitle,
            author: displayAuthor,
            summaryText: summaryText,
            descriptionText: descriptionText,
            languageFlags: languageFlags,
            resumeStatus: resumeStatus,
            titleFont: titleFont,
            authorFont: authorFont,
            metaFont: metaFont,
            textSpacing: textSpacing,
            titleLineLimit: titleLineLimit,
            titleScaleFactor: titleScaleFactor,
            descriptionLineLimit: descriptionLineLimit,
            badgeSpacing: badgeSpacing,
            titleStyle: titleStyle,
            secondaryTextStyle: secondaryTextStyle,
            tertiaryTextStyle: tertiaryTextStyle,
            accessoryJobId: item.jobId,
            accessoryStyle: accessoryStyle,
            accessorySecondaryTextColor: accessorySecondaryTextColor,
            isSynced: isLibrarySynced,
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

    private var isLibrarySynced: Bool {
        #if os(tvOS)
        offlineStore.status(for: item.jobId, kind: .library).isSynced
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

    // MARK: - Styling

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

    private var titleFont: Font {
        PlatformTypography.scaledFont(.headline)
    }

    private var authorFont: Font {
        PlatformTypography.scaledFont(.subheadline)
    }

    private var metaFont: Font {
        PlatformTypography.scaledFont(.caption1)
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
        return 10
        #else
        return 12
        #endif
    }

    private var textSpacing: CGFloat {
        #if os(tvOS)
        return 3
        #else
        return 4
        #endif
    }

    private var rowPadding: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 6
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

}
