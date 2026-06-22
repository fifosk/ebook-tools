import SwiftUI

struct JobsFilterPicker: View {
    @Binding var activeFilter: JobsViewModel.JobFilter
    let usesDarkListBackground: Bool
    let colorScheme: ColorScheme
    let onRefresh: () -> Void

    var body: some View {
        Picker("Filter", selection: $activeFilter) {
            ForEach(JobsViewModel.JobFilter.allCases) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .jobsFilterPickerStyle(
            usesDarkListBackground: usesDarkListBackground,
            colorScheme: colorScheme,
            onRefresh: handleFilterRefreshLongPress
        )
    }

    private func handleFilterRefreshLongPress() {
        onRefresh()
    }
}

private extension View {
    @ViewBuilder
    func jobsFilterPickerStyle(
        usesDarkListBackground: Bool,
        colorScheme: ColorScheme,
        onRefresh: @escaping () -> Void
    ) -> some View {
        #if os(tvOS)
        self
            .pickerStyle(.automatic)
            .padding(.horizontal)
            .onLongPressGesture(minimumDuration: 0.6, perform: onRefresh)
        #elseif os(iOS)
        self
            .pickerStyle(.segmented)
            .colorScheme(usesDarkListBackground ? .dark : colorScheme)
            .padding(.horizontal)
        #else
        self
            .pickerStyle(.segmented)
            .padding(.horizontal)
        #endif
    }
}
