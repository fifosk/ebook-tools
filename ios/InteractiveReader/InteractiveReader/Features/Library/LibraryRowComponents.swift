import SwiftUI

enum LibraryRowAccessoryStyle {
    case compact
    case landscape
}

struct LibraryRowLayout: View {
    let coverURL: URL?
    let variant: PlayerChannelVariant
    let coverHeight: CGFloat
    let rowSpacing: CGFloat
    let rowPadding: CGFloat
    let title: String
    let author: String
    let summaryText: String?
    let descriptionText: String?
    let languageFlags: [LanguageFlagEntry]
    let resumeStatus: LibraryRowView.ResumeStatus
    let titleFont: Font
    let authorFont: Font
    let metaFont: Font
    let textSpacing: CGFloat
    let titleLineLimit: Int
    let titleScaleFactor: CGFloat
    let descriptionLineLimit: Int
    let badgeSpacing: CGFloat
    let titleStyle: AnyShapeStyle
    let secondaryTextStyle: AnyShapeStyle
    let tertiaryTextStyle: AnyShapeStyle
    let accessoryJobId: String
    let accessoryStyle: LibraryRowAccessoryStyle
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

            LibraryRowMetadataStack(
                title: title,
                author: author,
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
                tertiaryTextStyle: tertiaryTextStyle
            )

            Spacer(minLength: spacerMinLength)

            LibraryRowAccessory(
                jobId: accessoryJobId,
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

struct LibraryRowMetadataStack: View {
    let title: String
    let author: String
    let summaryText: String?
    let descriptionText: String?
    let languageFlags: [LanguageFlagEntry]
    let resumeStatus: LibraryRowView.ResumeStatus
    let titleFont: Font
    let authorFont: Font
    let metaFont: Font
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

            Text(author)
                .font(authorFont)
                .lineLimit(1)
                .minimumScaleFactor(0.85)
                .foregroundStyle(secondaryTextStyle)

            if let summaryText {
                Text(summaryText)
                    .font(metaFont)
                    .foregroundStyle(tertiaryTextStyle)
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

                Text(resumeStatus.label)
                    .font(metaFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                    .foregroundStyle(resumeStatus.foreground)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(resumeStatus.background, in: Capsule())
            }
        }
    }
}

struct LibraryRowAccessory: View {
    let jobId: String
    let style: LibraryRowAccessoryStyle
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
            OfflineSyncBadge(jobId: jobId, kind: .library, isEligible: true)
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
        if isSynced {
            Image(systemName: "arrow.down.circle.fill")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(isFocused ? .black.opacity(0.6) : .green)
        }
        #else
        OfflineSyncBadge(jobId: jobId, kind: .library, isEligible: true)
        Image(systemName: "chevron.right")
            .foregroundStyle(secondaryTextColor)
        #endif
    }
}

extension LibraryRowView {
    struct ResumeStatus: Equatable {
        let label: String
        let foreground: Color
        let background: Color

        private static var isTV: Bool {
            #if os(tvOS)
            return true
            #else
            return false
            #endif
        }

        static func none() -> ResumeStatus {
            ResumeStatus(
                label: "None",
                foreground: isTV ? .white.opacity(0.7) : .secondary,
                background: isTV ? Color.white.opacity(0.15) : Color.secondary.opacity(0.15)
            )
        }

        static func local(label: String) -> ResumeStatus {
            ResumeStatus(
                label: label,
                foreground: isTV ? .yellow : .orange,
                background: isTV ? Color.yellow.opacity(0.25) : Color.orange.opacity(0.2)
            )
        }

        static func cloud(label: String) -> ResumeStatus {
            // Use cyan/teal on tvOS for better contrast against blue focus backgrounds
            ResumeStatus(
                label: label,
                foreground: isTV ? .cyan : .blue,
                background: isTV ? Color.cyan.opacity(0.25) : Color.blue.opacity(0.2)
            )
        }

        static func both(label: String) -> ResumeStatus {
            ResumeStatus(
                label: label,
                foreground: .green,
                background: isTV ? Color.green.opacity(0.25) : Color.green.opacity(0.2)
            )
        }

        static func newlyCompleted() -> ResumeStatus {
            ResumeStatus(
                label: "Newly completed",
                foreground: isTV ? .purple : .indigo,
                background: isTV ? Color.purple.opacity(0.25) : Color.indigo.opacity(0.18)
            )
        }

        static func needsAttention() -> ResumeStatus {
            ResumeStatus(
                label: "Needs attention",
                foreground: isTV ? .orange : .red,
                background: isTV ? Color.orange.opacity(0.25) : Color.red.opacity(0.14)
            )
        }
    }
}
