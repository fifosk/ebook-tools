import SwiftUI

enum BrowseSection: String, CaseIterable, Identifiable {
    case jobs = "Jobs"
    case create = "Create"
    case library = "Library"
    case settings = "Settings"
    case search = "Search"

    var id: String { rawValue }

    var accessibilityIdentifier: String {
        "browseSection\(rawValue)Button"
    }

    var systemImage: String {
        switch self {
        case .jobs:
            return "tray.full"
        case .create:
            return "sparkles"
        case .library:
            return "books.vertical"
        case .settings:
            return "gearshape"
        case .search:
            return "magnifyingglass"
        }
    }
}

struct BrowseSectionPicker: View {
    @Binding var activeSection: BrowseSection
    let usesDarkBackground: Bool
    let colorScheme: ColorScheme
    let onRefresh: () -> Void

    var body: some View {
        Picker("Browse", selection: $activeSection) {
            ForEach(orderedSections) { section in
                Label(section.rawValue, systemImage: section.systemImage)
                    .accessibilityIdentifier(section.accessibilityIdentifier)
                    .tag(section)
            }
        }
        .browseSectionPickerStyle(
            usesDarkBackground: usesDarkBackground,
            colorScheme: colorScheme,
            onRefresh: onRefresh
        )
        .accessibilityIdentifier("browseSectionPicker")
    }

    private var orderedSections: [BrowseSection] {
        #if os(tvOS)
        [.jobs, .library, .settings, .search]
        #else
        [.jobs, .create, .library, .settings, .search]
        #endif
    }
}

private extension View {
    @ViewBuilder
    func browseSectionPickerStyle(
        usesDarkBackground: Bool,
        colorScheme: ColorScheme,
        onRefresh: @escaping () -> Void
    ) -> some View {
        #if os(tvOS)
        self
            .pickerStyle(.automatic)
            .onLongPressGesture(minimumDuration: 0.6) {
                onRefresh()
            }
            .padding(.horizontal)
        #elseif os(iOS)
        self
            .pickerStyle(.segmented)
            .colorScheme(usesDarkBackground ? .dark : colorScheme)
            .padding(.horizontal)
        #else
        self
            .pickerStyle(.segmented)
            .padding(.horizontal)
        #endif
    }
}

struct SidebarSwipeDismissLayer: View {
    let onCollapse: () -> Void
    var minimumDistance: CGFloat = 24
    var requiredTranslation: CGFloat = 70
    var maxVerticalTranslation: CGFloat = 50

    var body: some View {
        #if os(tvOS)
        Color.clear
            .accessibilityHidden(true)
        #else
        Color.clear
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: minimumDistance, coordinateSpace: .local)
                    .onEnded { value in
                        let horizontal = value.translation.width
                        let vertical = value.translation.height
                        guard abs(horizontal) > abs(vertical) else { return }
                        guard horizontal < -requiredTranslation else { return }
                        guard abs(vertical) < maxVerticalTranslation else { return }
                        onCollapse()
                    }
            )
            .accessibilityHidden(true)
        #endif
    }
}
