import SwiftUI

struct AppChangelogSummaryView: View {
    let maxEntries: Int?
    let showBuildMetadata: Bool
    let usesDarkBackground: Bool

    init(
        maxEntries: Int? = nil,
        showBuildMetadata: Bool = true,
        usesDarkBackground: Bool = true
    ) {
        self.maxEntries = maxEntries
        self.showBuildMetadata = showBuildMetadata
        self.usesDarkBackground = usesDarkBackground
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ViewThatFits(in: .horizontal) {
                ChangelogTitleRow(
                    primaryStyle: primaryStyle,
                    secondaryStyle: secondaryStyle
                )
                ChangelogTitleStack(
                    primaryStyle: primaryStyle,
                    secondaryStyle: secondaryStyle
                )
            }

            if showBuildMetadata {
                Text(AppVersion.buildLabel)
                    .font(.caption)
                    .foregroundStyle(secondaryStyle)
                    .lineLimit(2)
                    .minimumScaleFactor(0.8)
                    .accessibilityIdentifier("appBuildMetadataText")
            }

            ForEach(displayEntries) { entry in
                AppChangelogEntryRow(
                    entry: entry,
                    primaryStyle: primaryStyle,
                    secondaryStyle: secondaryStyle
                )
            }
        }
        .padding(12)
        .background(backgroundStyle, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(borderStyle, lineWidth: 1)
        )
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("appChangelogSummaryView")
    }

    private var displayEntries: [AppChangelogEntry] {
        let entries = AppChangelog.days.first?.entries ?? []
        guard let maxEntries else { return entries }
        return Array(entries.prefix(maxEntries))
    }

    private var primaryStyle: Color {
        usesDarkBackground ? .white : .primary
    }

    private var secondaryStyle: Color {
        usesDarkBackground ? .white.opacity(0.72) : .secondary
    }

    private var backgroundStyle: Color {
        #if os(tvOS)
        return usesDarkBackground ? Color.white.opacity(0.07) : Color.black.opacity(0.08)
        #else
        usesDarkBackground ? Color.white.opacity(0.07) : Color(.secondarySystemBackground)
        #endif
    }

    private var borderStyle: Color {
        #if os(tvOS)
        return usesDarkBackground ? Color.white.opacity(0.12) : Color.primary.opacity(0.16)
        #else
        usesDarkBackground ? Color.white.opacity(0.12) : Color(.separator).opacity(0.4)
        #endif
    }
}

private struct ChangelogTitleRow: View {
    let primaryStyle: Color
    let secondaryStyle: Color

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            ChangelogVersionText(primaryStyle: primaryStyle)
            Spacer(minLength: 8)
            ChangelogDateText(secondaryStyle: secondaryStyle)
        }
    }
}

private struct ChangelogTitleStack: View {
    let primaryStyle: Color
    let secondaryStyle: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            ChangelogVersionText(primaryStyle: primaryStyle)
            ChangelogDateText(secondaryStyle: secondaryStyle)
        }
    }
}

private struct ChangelogVersionText: View {
    let primaryStyle: Color

    var body: some View {
        Text(AppVersion.displayLabel)
            .font(.headline)
            .monospacedDigit()
            .foregroundStyle(primaryStyle)
            .lineLimit(1)
            .minimumScaleFactor(0.9)
            .fixedSize(horizontal: true, vertical: false)
    }
}

private struct ChangelogDateText: View {
    let secondaryStyle: Color

    var body: some View {
        Text(AppChangelog.days.first?.dateLabel ?? "Latest")
            .font(.caption)
            .foregroundStyle(secondaryStyle)
            .lineLimit(1)
            .fixedSize(horizontal: true, vertical: false)
    }
}

private struct AppChangelogEntryRow: View {
    let entry: AppChangelogEntry
    let primaryStyle: Color
    let secondaryStyle: Color

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(Color.green)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(primaryStyle)
                Text(entry.detail)
                    .font(.caption)
                    .foregroundStyle(secondaryStyle)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}
