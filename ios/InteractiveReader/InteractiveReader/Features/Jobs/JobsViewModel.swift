import Foundation

@MainActor
final class JobsViewModel: ObservableObject {
    enum JobFilter: String, CaseIterable, Identifiable {
        case video = "Video"
        case book = "Books"
        case subtitles = "Subtitles"

        var id: String { rawValue }
    }

    @Published var jobs: [PipelineStatusResponse] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var query: String = ""
    @Published var activeFilter: JobFilter = .video

    private var refreshTask: Task<Void, Never>?
    private let refreshInterval: UInt64 = 6_000_000_000

    func load(using appState: AppState, isBackground: Bool = false) async {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return
        }
        if !isBackground {
            isLoading = true
            errorMessage = nil
        }
        defer {
            if !isBackground {
                isLoading = false
            }
        }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchPipelineJobs()
            jobs = response.jobs
        } catch {
            if !isBackground {
                errorMessage = error.localizedDescription
            }
        }
    }

    func delete(jobId: String, using appState: AppState) async -> Bool {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return false
        }
        do {
            let client = APIClient(configuration: configuration)
            try await client.deleteJob(jobId: jobId)
            jobs.removeAll { $0.jobId == jobId }
            errorMessage = nil
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func moveToLibrary(jobId: String, using appState: AppState) async -> Bool {
        guard let configuration = appState.configuration else {
            errorMessage = "Configure a valid API base URL before continuing."
            return false
        }
        do {
            let client = APIClient(configuration: configuration)
            try await client.moveJobToLibrary(jobId: jobId)
            jobs.removeAll { $0.jobId == jobId }
            errorMessage = nil
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func startAutoRefresh(using appState: AppState) {
        refreshTask?.cancel()
        refreshTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.load(using: appState, isBackground: true)
                try? await Task.sleep(nanoseconds: refreshInterval)
            }
        }
    }

    func stopAutoRefresh() {
        refreshTask?.cancel()
        refreshTask = nil
    }

    var filteredJobs: [PipelineStatusResponse] {
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        let loweredQuery = trimmedQuery.lowercased()
        return jobs
            .filter { job in
                guard jobCategory(for: job) == activeFilter else { return false }
                guard !loweredQuery.isEmpty else { return true }
                return jobSearchFields(job).contains { $0.contains(loweredQuery) }
            }
            .sorted { left, right in
                let leftDate = Self.parseDate(left.createdAt) ?? .distantPast
                let rightDate = Self.parseDate(right.createdAt) ?? .distantPast
                return leftDate > rightDate
            }
    }

    var activeJobs: [PipelineStatusResponse] {
        filteredJobs.filter { $0.isActiveForDisplay }
    }

    var finishedJobs: [PipelineStatusResponse] {
        filteredJobs.filter { $0.isFinishedForDisplay }
    }

    func jobCategory(for job: PipelineStatusResponse) -> JobFilter {
        let type = job.jobType.lowercased()
        if type.contains("video") || type.contains("youtube") || type.contains("dub") {
            return .video
        }
        if type.contains("subtitle") {
            return .subtitles
        }
        return .book
    }

    private func jobSearchFields(_ job: PipelineStatusResponse) -> [String] {
        var fields: [String] = [job.jobId.lowercased(), job.jobType.lowercased()]
        if let label = job.jobLabel?.nonEmptyValue {
            fields.append(label.lowercased())
        }
        if let title = jobTitle(from: job)?.lowercased() {
            fields.append(title)
        }
        return fields
    }

    private func jobTitle(from job: PipelineStatusResponse) -> String? {
        if let label = job.jobLabel?.nonEmptyValue {
            return label
        }
        guard let resultObject = job.result?.objectValue else { return nil }
        if let title = resultObject["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        if let book = resultObject["book_metadata"]?.objectValue,
           let title = book["title"]?.stringValue?.nonEmptyValue {
            return title
        }
        return nil
    }

    private static let dateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let dateFormatterWithFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static func parseDate(_ value: String) -> Date? {
        dateFormatterWithFractional.date(from: value) ?? dateFormatter.date(from: value)
    }
}
