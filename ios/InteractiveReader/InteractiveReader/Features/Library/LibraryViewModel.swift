import Foundation

@MainActor
final class LibraryViewModel: ObservableObject {
    enum LibraryFilter: String, CaseIterable, Identifiable {
        case book = "Books"
        case subtitles = "Subtitles"
        case video = "Video"

        var id: String { rawValue }

        var itemType: String {
            switch self {
            case .book:
                return "book"
            case .subtitles:
                return "narrated_subtitle"
            case .video:
                return "video"
            }
        }
    }

    @Published var items: [LibraryItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var query: String = ""
    @Published var activeFilter: LibraryFilter = .book

    func load(using appState: AppState) async {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchLibraryItems(query: query.nonEmptyValue)
            items = response.items
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    var filteredItems: [LibraryItem] {
        items.filter { $0.itemType == activeFilter.itemType }
    }
}
