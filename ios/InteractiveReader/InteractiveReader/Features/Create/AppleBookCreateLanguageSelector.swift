import SwiftUI

#if !os(tvOS)
struct AppleBookCreateLanguageSelector: View {
    let title: String
    @Binding var selection: AppleBookCreateLanguage
    let options: [AppleBookCreateLanguage]
    let accessibilityIdentifier: String

    @State private var selectedLanguage: AppleBookCreateLanguage?
    @State private var searchText = ""

    private var filteredOptions: [AppleBookCreateLanguage] {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return options }
        return options.filter { language in
            language.label.localizedCaseInsensitiveContains(query)
                || language.backendValue.localizedCaseInsensitiveContains(query)
        }
    }

    var body: some View {
        Button {
            searchText = ""
            selectedLanguage = selection
        } label: {
            HStack {
                Text(title)
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text(selection.label)
                        .foregroundStyle(.secondary)
                    Text("\(options.count) available")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .accessibilityIdentifier(accessibilityIdentifier)
        .accessibilityValue("\(selection.label), \(options.count) available")
        .sheet(item: $selectedLanguage) { _ in
            NavigationStack {
                List(filteredOptions) { language in
                    Button {
                        selection = language
                        searchText = ""
                        selectedLanguage = nil
                    } label: {
                        HStack {
                            Text(language.label)
                            Spacer()
                            if language == selection {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.accent)
                            }
                        }
                    }
                    .accessibilityIdentifier("\(accessibilityIdentifier).\(language.id)")
                }
                .searchable(text: $searchText, prompt: "Search Languages")
                .navigationTitle(title)
                #if os(iOS)
                .navigationBarTitleDisplayMode(.inline)
                #endif
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Done") {
                            searchText = ""
                            selectedLanguage = nil
                        }
                    }
                }
            }
        }
    }
}
#endif
