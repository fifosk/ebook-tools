import Foundation

extension AppleBookCreateViewModel {
    func submitGeneratedBook(_ draft: AppleBookCreateDraft, using appState: AppState) async -> String? {
        await submitJob(using: appState) { client in
            let response = try await client.submitBookGenerationJob(
                AppleBookCreatePayloadFactory.makeSubmission(from: draft)
            )
            return response.jobId
        }
    }

    func submitNarrateEbook(
        _ draft: AppleNarrateEbookDraft,
        localFileURL: URL? = nil,
        localFilename: String? = nil,
        using appState: AppState
    ) async -> String? {
        await submitJob(using: appState) { client in
            let effectiveDraft: AppleNarrateEbookDraft
            if let localFileURL {
                let upload = try await client.uploadPipelineEbook(fileURL: localFileURL, filename: localFilename)
                effectiveDraft = draft.replacingInputFile(upload.path)
            } else {
                effectiveDraft = draft
            }
            let response = try await client.submitPipeline(
                AppleBookCreatePayloadFactory.makePipelineSubmission(from: effectiveDraft)
            )
            return response.jobId
        }
    }

    func submitSubtitleJob(
        _ draft: AppleSubtitleJobDraft,
        localFileURL: URL? = nil,
        localFilename: String? = nil,
        using appState: AppState
    ) async -> String? {
        await submitJob(using: appState) { client in
            let response = try await client.submitSubtitleJob(
                AppleBookCreatePayloadFactory.makeSubtitlePayload(from: draft),
                fileURL: localFileURL,
                filename: localFilename
            )
            return response.jobId
        }
    }

    func submitYoutubeDub(
        _ draft: AppleYoutubeDubDraft,
        using appState: AppState
    ) async -> String? {
        await submitJob(using: appState) { client in
            let response = try await client.submitYoutubeDub(
                AppleBookCreatePayloadFactory.makeYoutubeDubPayload(from: draft)
            )
            return response.jobId
        }
    }

    private func submitJob(
        using appState: AppState,
        operation: (APIClient) async throws -> String
    ) async -> String? {
        guard let configuration = appState.configuration else {
            errorMessage = "API configuration is unavailable."
            return nil
        }

        isSubmitting = true
        errorMessage = nil
        submittedJobId = nil
        defer { isSubmitting = false }

        do {
            let client = APIClient(configuration: configuration)
            let jobId = try await operation(client)
            submittedJobId = jobId
            return jobId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }
}
