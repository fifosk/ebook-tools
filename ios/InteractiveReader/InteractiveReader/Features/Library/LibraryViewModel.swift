import Foundation

@MainActor
final class LibraryViewModel: ObservableObject {
    enum LibraryFilter: String, CaseIterable, Identifiable {
        case video = "Video"
        case book = "Books"
        case subtitles = "Subtitles"

        var id: String { rawValue }

        var itemType: String {
            switch self {
            case .video:
                return "video"
            case .book:
                return "book"
            case .subtitles:
                return "narrated_subtitle"
            }
        }
    }

    @Published var items: [LibraryItem] = []
    @Published var isLoading = false
    @Published var isUploadingSource = false
    @Published var isLookingUpIsbn = false
    @Published var isApplyingIsbn = false
    @Published var isCreatingExport = false
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

    func delete(jobId: String, using appState: AppState) async -> Bool {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return false
        }
        do {
            let client = APIClient(configuration: configuration)
            try await client.deleteLibraryItem(jobId: jobId)
            items.removeAll { $0.jobId == jobId }
            errorMessage = nil
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func uploadSource(
        for item: LibraryItem,
        fileURL: URL,
        filename: String?,
        using appState: AppState
    ) async -> Bool {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return false
        }
        isUploadingSource = true
        errorMessage = nil
        defer { isUploadingSource = false }

        do {
            let client = APIClient(configuration: configuration)
            let updated = try await client.uploadLibrarySource(
                jobId: item.jobId,
                fileURL: fileURL,
                filename: filename
            )
            if let index = items.firstIndex(where: { $0.jobId == updated.jobId }) {
                items[index] = updated
            } else {
                items.insert(updated, at: 0)
            }
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func applyIsbn(
        _ isbn: String,
        to item: LibraryItem,
        using appState: AppState
    ) async -> Bool {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return false
        }
        let trimmed = isbn.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            errorMessage = "Enter an ISBN before applying metadata."
            return false
        }

        isApplyingIsbn = true
        errorMessage = nil
        defer { isApplyingIsbn = false }

        do {
            let client = APIClient(configuration: configuration)
            let updated = try await client.applyLibraryIsbn(jobId: item.jobId, isbn: trimmed)
            if let index = items.firstIndex(where: { $0.jobId == updated.jobId }) {
                items[index] = updated
            } else {
                items.insert(updated, at: 0)
            }
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func lookupIsbnMetadata(
        _ isbn: String,
        using appState: AppState
    ) async -> [String: JSONValue]? {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return nil
        }
        let trimmed = isbn.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            errorMessage = "Enter an ISBN before previewing metadata."
            return nil
        }

        isLookingUpIsbn = true
        errorMessage = nil
        defer { isLookingUpIsbn = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.lookupLibraryIsbnMetadata(isbn: trimmed)
            return response.metadata
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func createOfflineExport(
        for item: LibraryItem,
        using appState: AppState
    ) async -> URL? {
        guard item.mediaCompleted else {
            errorMessage = "Offline player export is available after media finishes processing."
            return nil
        }
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return nil
        }

        isCreatingExport = true
        errorMessage = nil
        defer { isCreatingExport = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.createOfflineExport(sourceKind: "library", sourceId: item.jobId)
            return Self.resolveExportDownloadURL(response.downloadUrl, configuration: configuration)
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    var filteredItems: [LibraryItem] {
        items.filter { $0.itemType == activeFilter.itemType }
    }

    private static func resolveExportDownloadURL(
        _ downloadURL: String,
        configuration: APIClientConfiguration
    ) -> URL? {
        if let absoluteURL = URL(string: downloadURL), absoluteURL.scheme != nil {
            return absoluteURL
        }
        return URL(string: downloadURL, relativeTo: configuration.apiBaseURL)?.absoluteURL
    }
}
