import SwiftUI

enum JobRowAccessoryStyle {
    case compact
    case landscape
}

struct JobRowLayout: View {
    let coverURL: URL?
    let variant: PlayerChannelVariant
    let coverHeight: CGFloat
    let rowSpacing: CGFloat
    let rowPadding: CGFloat
    let title: String
    let summaryText: String?
    let descriptionText: String?
    let languageFlags: [LanguageFlagEntry]
    let statusIcon: String
    let statusLabel: String
    let statusColor: Color
    let resumeStatus: LibraryRowView.ResumeStatus
    let progressLabel: String?
    let progressValue: Double?
    let progressTint: Color
    let titleFont: Font
    let summaryFont: Font
    let metaFont: Font
    let statusGlyphFont: Font
    let textSpacing: CGFloat
    let titleLineLimit: Int
    let titleScaleFactor: CGFloat
    let descriptionLineLimit: Int
    let badgeSpacing: CGFloat
    let titleStyle: AnyShapeStyle
    let secondaryTextStyle: AnyShapeStyle
    let tertiaryTextStyle: AnyShapeStyle
    let accessoryJobId: String
    let accessoryIsFinished: Bool
    let accessoryStyle: JobRowAccessoryStyle
    let accessorySecondaryTextColor: Color
    let isSynced: Bool
    let isFocused: Bool

    var body: some View {
        HStack(alignment: alignment, spacing: rowSpacing) {
            UnifiedCoverView(
                url: coverURL,
                variant: variant,
                height: coverHeight
            )

            JobRowMetadataStack(
                title: title,
                summaryText: summaryText,
                descriptionText: descriptionText,
                languageFlags: languageFlags,
                statusIcon: statusIcon,
                statusLabel: statusLabel,
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
                tertiaryTextStyle: tertiaryTextStyle
            )

            Spacer(minLength: spacerMinLength)

            JobRowAccessory(
                jobId: accessoryJobId,
                isFinished: accessoryIsFinished,
                style: accessoryStyle,
                secondaryTextColor: accessorySecondaryTextColor,
                isSynced: isSynced,
                isFocused: isFocused
            )
        }
        .padding(.vertical, rowPadding)
    }

    private var alignment: VerticalAlignment {
        switch accessoryStyle {
        case .compact:
            return .top
        case .landscape:
            return .center
        }
    }

    private var spacerMinLength: CGFloat? {
        switch accessoryStyle {
        case .compact:
            return 4
        case .landscape:
            return nil
        }
    }
}

struct JobRowMetadataStack: View {
    let title: String
    let summaryText: String?
    let descriptionText: String?
    let languageFlags: [LanguageFlagEntry]
    let statusIcon: String
    let statusLabel: String
    let statusColor: Color
    let resumeStatus: LibraryRowView.ResumeStatus
    let progressLabel: String?
    let progressValue: Double?
    let progressTint: Color
    let titleFont: Font
    let summaryFont: Font
    let metaFont: Font
    let statusGlyphFont: Font
    let textSpacing: CGFloat
    let titleLineLimit: Int
    let titleScaleFactor: CGFloat
    let descriptionLineLimit: Int
    let badgeSpacing: CGFloat
    let titleStyle: AnyShapeStyle
    let secondaryTextStyle: AnyShapeStyle
    let tertiaryTextStyle: AnyShapeStyle

    var body: some View {
        VStack(alignment: .leading, spacing: textSpacing) {
            Text(title)
                .font(titleFont)
                .lineLimit(titleLineLimit)
                .minimumScaleFactor(titleScaleFactor)
                .truncationMode(.tail)
                .foregroundStyle(titleStyle)

            if let summaryText {
                Text(summaryText)
                    .font(summaryFont)
                    .foregroundStyle(secondaryTextStyle)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }

            if let descriptionText {
                Text(descriptionText)
                    .font(metaFont)
                    .foregroundStyle(tertiaryTextStyle)
                    .lineLimit(descriptionLineLimit)
                    .truncationMode(.tail)
            }

            HStack(spacing: badgeSpacing) {
                LanguageFlagPairView(flags: languageFlags)
                    .font(metaFont)

                Text(statusIcon)
                    .font(statusGlyphFont)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .foregroundStyle(statusColor)
                    .background(statusColor.opacity(0.18), in: Capsule())
                    .accessibilityLabel(statusLabel)

                Text(resumeStatus.label)
                    .font(metaFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                    .foregroundStyle(resumeStatus.foreground)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(resumeStatus.background, in: Capsule())
            }

            if let progressLabel {
                Text(progressLabel)
                    .font(metaFont)
                    .foregroundStyle(secondaryTextStyle)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
            }

            if let progressValue {
                ProgressView(value: progressValue)
                    .tint(progressTint)
            }
        }
    }
}

struct JobRowAccessory: View {
    let jobId: String
    let isFinished: Bool
    let style: JobRowAccessoryStyle
    let secondaryTextColor: Color
    let isSynced: Bool
    let isFocused: Bool

    var body: some View {
        switch style {
        case .compact:
            compactAccessory
        case .landscape:
            landscapeAccessory
        }
    }

    private var compactAccessory: some View {
        VStack {
            #if !os(tvOS)
            if isFinished {
                OfflineSyncBadge(jobId: jobId, kind: .job, isEligible: true)
            }
            #endif

            Spacer()

            Image(systemName: "chevron.right")
                .foregroundStyle(secondaryTextColor)
                .font(.caption)
        }
    }

    @ViewBuilder
    private var landscapeAccessory: some View {
        #if os(tvOS)
        if isFinished && isSynced {
            Image(systemName: "arrow.down.circle.fill")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(isFocused ? .black.opacity(0.6) : .green)
        }
        #else
        if isFinished {
            OfflineSyncBadge(jobId: jobId, kind: .job, isEligible: true)
        }

        Image(systemName: "chevron.right")
            .foregroundStyle(secondaryTextColor)
        #endif
    }
}
