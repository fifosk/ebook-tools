import SwiftUI

struct AppChangelogSummaryView: View {
    let maxEntries: Int?
    let showBuildMetadata: Bool
    let usesDarkBackground: Bool
    let maxContentHeight: CGFloat?
    #if os(tvOS)
    @FocusState private var focusedEntryID: String?
    #endif

    init(
        maxEntries: Int? = nil,
        showBuildMetadata: Bool = true,
        usesDarkBackground: Bool = true,
        maxContentHeight: CGFloat? = nil
    ) {
        self.maxEntries = maxEntries
        self.showBuildMetadata = showBuildMetadata
        self.usesDarkBackground = usesDarkBackground
        self.maxContentHeight = maxContentHeight
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

            entriesSection
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

    @ViewBuilder
    private var entriesSection: some View {
        if let maxContentHeight {
            #if os(tvOS)
            tvScrollableEntries(maxContentHeight: maxContentHeight)
            #else
            ScrollView(.vertical, showsIndicators: true) {
                entriesList
                    .padding(.trailing, 10)
            }
            .frame(maxHeight: maxContentHeight)
            #endif
        } else {
            #if os(tvOS)
            tvEntriesList(entries: displayEntries)
            #else
            entriesList
            #endif
        }
    }

    #if os(tvOS)
    private func tvScrollableEntries(maxContentHeight: CGFloat) -> some View {
        let entryWindow = tvEntryWindow(maxContentHeight: maxContentHeight)

        return VStack(alignment: .leading, spacing: 10) {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(entryWindow.visibleEntries) { entry in
                    tvEntryButton(entry)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: maxContentHeight, alignment: .topLeading)
            .focusSection()
            .onMoveCommand(perform: moveFocusedEntry)
            .onAppear(perform: focusFirstEntryIfNeeded)

            if entryWindow.showsPosition {
                HStack(spacing: 8) {
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.caption2.weight(.bold))
                    Text(entryWindow.positionLabel)
                        .font(.caption2.weight(.semibold))
                        .monospacedDigit()
                }
                .foregroundStyle(secondaryStyle)
                .frame(maxWidth: .infinity, alignment: .trailing)
                .accessibilityIdentifier("appChangelogPositionLabel")
            }
        }
        .animation(.easeInOut(duration: 0.16), value: focusedEntryID)
    }

    private func tvEntriesList(entries: [AppChangelogEntry]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(entries) { entry in
                tvEntryButton(entry)
            }
        }
        .focusSection()
        .onAppear(perform: focusFirstEntryIfNeeded)
    }

    private func tvEntryButton(_ entry: AppChangelogEntry) -> some View {
        Button(action: {}) {
            AppChangelogEntryRow(
                entry: entry,
                primaryStyle: primaryStyle,
                secondaryStyle: secondaryStyle,
                isFocused: focusedEntryID == entry.id
            )
        }
        .buttonStyle(.plain)
        .id(entry.id)
        .focused($focusedEntryID, equals: entry.id)
        .onMoveCommand(perform: moveFocusedEntry)
        .accessibilityIdentifier("appChangelogEntry.\(entry.id)")
    }

    private func tvEntryWindow() -> TVChangelogEntryWindow {
        TVChangelogEntryWindow(
            entries: displayEntries,
            focusedEntryID: focusedEntryID,
            visibleCapacity: nil
        )
    }

    private func tvEntryWindow(maxContentHeight: CGFloat) -> TVChangelogEntryWindow {
        TVChangelogEntryWindow(
            entries: displayEntries,
            focusedEntryID: focusedEntryID,
            visibleCapacity: max(2, Int(maxContentHeight / 92))
        )
    }

    private func focusFirstEntryIfNeeded() {
        guard focusedEntryID == nil else { return }
        focusedEntryID = displayEntries.first?.id
    }

    private func moveFocusedEntry(_ direction: MoveCommandDirection) {
        let offset: Int
        switch direction {
        case .up:
            offset = -1
        case .down:
            offset = 1
        default:
            return
        }

        let entries = displayEntries
        guard !entries.isEmpty else { return }
        focusedEntryID = tvEntryWindow().entryID(movingBy: offset)
    }
    #endif

    private var entriesList: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(displayEntries) { entry in
                AppChangelogEntryRow(
                    entry: entry,
                    primaryStyle: primaryStyle,
                    secondaryStyle: secondaryStyle
                )
            }
        }
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

#if os(tvOS)
private struct TVChangelogEntryWindow {
    let entries: [AppChangelogEntry]
    let focusedEntryID: String?
    let visibleCapacity: Int?

    var showsPosition: Bool {
        entries.count > visibleEntries.count
    }

    var positionLabel: String {
        guard !entries.isEmpty else { return "" }
        return "\(focusedIndex + 1)/\(entries.count)"
    }

    var visibleEntries: [AppChangelogEntry] {
        guard let visibleCapacity else { return entries }
        guard entries.count > visibleCapacity else { return entries }

        let capacity = min(max(visibleCapacity, 2), entries.count)
        let halfWindow = capacity / 2
        let proposedStart = focusedIndex - halfWindow
        let maxStart = entries.count - capacity
        let startIndex = min(max(proposedStart, 0), maxStart)
        let endIndex = min(startIndex + capacity, entries.count)
        return Array(entries[startIndex..<endIndex])
    }

    func entryID(movingBy offset: Int) -> String? {
        guard !entries.isEmpty else { return nil }
        let nextIndex = min(max(focusedIndex + offset, 0), entries.count - 1)
        return entries[nextIndex].id
    }

    private var focusedIndex: Int {
        focusedEntryID
            .flatMap { focusedID in entries.firstIndex { $0.id == focusedID } } ?? 0
    }
}
#endif

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
        Text("v\(AppChangelog.days.first?.version ?? AppVersion.release)")
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
    var isFocused = false

    @ViewBuilder
    var body: some View {
        let row = HStack(alignment: .top, spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(Color.green)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(primaryStyle)
                    #if os(tvOS)
                    .lineLimit(1)
                    #endif
                Text(entry.detail)
                    .font(.caption)
                    .foregroundStyle(secondaryStyle)
                    #if os(tvOS)
                    .lineLimit(2)
                    #else
                    .fixedSize(horizontal: false, vertical: true)
                    #endif
            }
        }

        #if os(tvOS)
        row
            .padding(8)
            .frame(maxWidth: .infinity, alignment: .leading)
            .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(isFocused ? Color.white.opacity(0.14) : Color.clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(isFocused ? Color.white.opacity(0.28) : Color.clear, lineWidth: 1)
            )
        #else
        row
        #endif
    }
}
