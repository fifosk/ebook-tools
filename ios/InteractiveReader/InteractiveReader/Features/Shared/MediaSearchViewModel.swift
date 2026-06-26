import Foundation

@MainActor
final class MediaSearchViewModel: ObservableObject {
    @Published var query: String = ""
    @Published var state: MediaSearchState = .idle
    @Published var isExpanded: Bool = false

    private var searchTask: Task<Void, Never>?
    private var debounceTask: Task<Void, Never>?
    private let debounceInterval: Duration = .milliseconds(300)

    var resultCount: Int {
        if case let .results(results) = state {
            return results.count
        }
        return 0
    }

    var isSearching: Bool {
        if case .searching = state {
            return true
        }
        return false
    }

    func search(jobId: String?, using client: APIClient) {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            state = .idle
            return
        }
        guard let normalizedJobId = jobId?.trimmingCharacters(in: .whitespacesAndNewlines),
              !normalizedJobId.isEmpty else {
            state = .error("No job ID available")
            return
        }

        searchTask?.cancel()
        state = .searching

        searchTask = Task {
            await runSearch(jobId: normalizedJobId, query: trimmed, using: client)
        }
    }

    func debouncedSearch(jobId: String?, using client: APIClient) {
        debounceTask?.cancel()
        debounceTask = Task {
            await runDebouncedSearch(jobId: jobId, using: client)
        }
    }

    func clear() {
        searchTask?.cancel()
        debounceTask?.cancel()
        query = ""
        state = .idle
    }

    func dismiss() {
        isExpanded = false
    }

    func calculateTargetSentence(from result: MediaSearchResult) -> Int? {
        guard let startSentence = result.startSentence else { return nil }
        let endSentence = result.endSentence ?? startSentence
        let span = max(endSentence - startSentence, 0)

        if let ratio = result.offsetRatio, ratio.isFinite {
            let clampedRatio = min(max(ratio, 0), 1)
            return max(startSentence + Int(round(Double(span) * clampedRatio)), 1)
        }
        return max(startSentence, 1)
    }

    func calculateSeekTime(from result: MediaSearchResult) -> Double? {
        if let time = result.approximateTimeSeconds, time.isFinite, time >= 0 {
            return time
        }
        if let cueStart = result.cueStartSeconds, cueStart.isFinite, cueStart >= 0 {
            return cueStart
        }
        return nil
    }

    private func runSearch(jobId: String, query: String, using client: APIClient) async {
        do {
            let response = try await client.searchMedia(jobId: jobId, query: query)
            guard !Task.isCancelled else { return }
            applySearchResponse(response, query: query)
        } catch is CancellationError {
            // Ignore cancellation.
        } catch {
            guard !Task.isCancelled else { return }
            state = .error(error.localizedDescription)
        }
    }

    private func applySearchResponse(_ response: MediaSearchResponse, query: String) {
        if response.results.isEmpty {
            // A non-zero count with no decoded results indicates a response-shape mismatch.
            if response.count > 0 {
                state = .error("Decode error: \(response.count) results expected but 0 decoded")
            } else {
                state = .empty(query)
            }
        } else {
            state = .results(response.results)
        }
    }

    private func runDebouncedSearch(jobId: String?, using client: APIClient) async {
        do {
            try await Task.sleep(for: debounceInterval)
            guard !Task.isCancelled else { return }
            search(jobId: jobId, using: client)
        } catch {
            // Ignore cancellation.
        }
    }
}
