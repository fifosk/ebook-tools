import SwiftUI
#if os(tvOS)
import UIKit
#endif

struct LibraryView: View {
    @ObservedObject var viewModel: LibraryViewModel
    let useNavigationLinks: Bool
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    let onSelect: ((LibraryItem) -> Void)?
    let coverResolver: (LibraryItem) -> URL?

    @FocusState private var isSearchFocused: Bool

    var body: some View {
        VStack(spacing: 12) {
            header

            if let error = viewModel.errorMessage {
                errorRow(message: error)
                    .padding(.horizontal)
            }

            List {
                ForEach(viewModel.filteredItems) { item in
                    if useNavigationLinks {
                        NavigationLink(value: item) {
                            LibraryRowView(item: item, coverURL: coverResolver(item))
                        }
                    } else {
                        #if os(tvOS)
                        Button {
                            onSelect?(item)
                        } label: {
                            LibraryRowView(item: item, coverURL: coverResolver(item))
                        }
                        .buttonStyle(.plain)
                        #else
                        LibraryRowView(item: item, coverURL: coverResolver(item))
                            .contentShape(Rectangle())
                            .onTapGesture {
                                onSelect?(item)
                            }
                        #endif
                    }
                }
            }
            .listStyle(.plain)
            .overlay(alignment: .center) {
                listOverlay
            }
        }
        #if !os(tvOS)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Refresh", action: onRefresh)
                    .disabled(viewModel.isLoading)
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Sign Out", action: onSignOut)
            }
        }
        #endif
    }

    private func errorRow(message: String) -> some View {
        Label(message, systemImage: "exclamationmark.triangle.fill")
            .foregroundStyle(.red)
            .font(.callout)
    }

    private var listOverlay: some View {
        Group {
            if viewModel.isLoading {
                ProgressView("Loading library…")
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
            } else if viewModel.filteredItems.isEmpty {
                Text("No items found.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                TextField("Search library", text: $viewModel.query)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .focused($isSearchFocused)
                    .submitLabel(.search)
                    .onSubmit(onRefresh)
                Button(action: onRefresh) {
                    Image(systemName: "magnifyingglass")
                }
                .disabled(viewModel.isLoading)
            }
            .padding(.horizontal)

            Picker("Filter", selection: $viewModel.activeFilter) {
                ForEach(LibraryViewModel.LibraryFilter.allCases) { filter in
                    Text(filter.rawValue).tag(filter)
                }
            }
            #if os(tvOS)
            .pickerStyle(.automatic)
            #else
            .pickerStyle(.segmented)
            #endif
            .padding(.horizontal)

            #if os(tvOS)
            HStack(spacing: 16) {
                Button("Refresh", action: onRefresh)
                    .disabled(viewModel.isLoading)
                Button("Sign Out", action: onSignOut)
            }
            .padding(.horizontal)
            #endif
        }
        .padding(.top, 8)
        #if os(tvOS)
        .font(tvOSHeaderFont)
        #endif
    }

    #if os(tvOS)
    private var tvOSHeaderFont: Font {
        let size = UIFont.preferredFont(forTextStyle: .body).pointSize * 0.5
        return .system(size: size)
    }
    #endif
}
