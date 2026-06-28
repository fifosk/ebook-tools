import Foundation

enum ApplePipelineMediaRuntimeContract {
    static let jobMediaPathTemplate = "/api/pipelines/jobs/{job_id}/media"
    static let jobMediaLivePathTemplate = "/api/pipelines/jobs/{job_id}/media/live"
    static let jobMediaChunkPathTemplate = "/api/pipelines/jobs/{job_id}/media/chunks/{chunk_id}"
    static let libraryMediaPathTemplate = "/api/library/media/{job_id}"
    static let libraryMediaFilePathTemplate = "/api/library/media/{job_id}/file/{file_path}"
    static let libraryMediaFilePrefixTemplate = "/api/library/media/{job_id}/file/"
    static let libraryMediaPathPrefix = "/api/library/media/"
    static let jobTimingPathTemplate = "/api/jobs/{job_id}/timing"
    static let subtitleTvMetadataPathTemplate = "/api/subtitles/jobs/{job_id}/metadata/tv"
    static let youtubeVideoMetadataPathTemplate = "/api/subtitles/jobs/{job_id}/metadata/youtube"
    static let chunkOrdering = "sentenceRange"

    static func jobMediaPath(_ encodedJobId: String) -> String {
        jobMediaPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func jobMediaLivePath(_ encodedJobId: String) -> String {
        jobMediaLivePathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func jobMediaChunkPath(encodedJobId: String, encodedChunkId: String) -> String {
        jobMediaChunkPathTemplate
            .replacingOccurrences(of: "{job_id}", with: encodedJobId)
            .replacingOccurrences(of: "{chunk_id}", with: encodedChunkId)
    }

    static func libraryMediaPath(_ encodedJobId: String) -> String {
        libraryMediaPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func libraryMediaFilePath(encodedJobId: String, encodedFilePath: String) -> String {
        libraryMediaFilePathTemplate
            .replacingOccurrences(of: "{job_id}", with: encodedJobId)
            .replacingOccurrences(of: "{file_path}", with: encodedFilePath)
    }

    static func libraryMediaFilePrefix(encodedJobId: String) -> String {
        libraryMediaFilePrefixTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func jobTimingPath(_ encodedJobId: String) -> String {
        jobTimingPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func subtitleTvMetadataPath(_ encodedJobId: String) -> String {
        subtitleTvMetadataPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }

    static func youtubeVideoMetadataPath(_ encodedJobId: String) -> String {
        youtubeVideoMetadataPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)
    }
}

extension APIClient {
    func fetchJobMedia(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: ApplePipelineMediaRuntimeContract.jobMediaPath(encoded))
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobMediaLive(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: ApplePipelineMediaRuntimeContract.jobMediaLivePath(encoded))
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobMediaLiveData(jobId: String) async throws -> Data {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequest(path: ApplePipelineMediaRuntimeContract.jobMediaLivePath(encoded))
    }

    func fetchJobMediaChunk(jobId: String, chunkId: String) async throws -> PipelineMediaChunk {
        let encodedJob = AppleAPIPathComponentEncoding.encode(jobId)
        let encodedChunk = AppleAPIPathComponentEncoding.encode(chunkId)
        let data = try await sendRequest(
            path: ApplePipelineMediaRuntimeContract.jobMediaChunkPath(
                encodedJobId: encodedJob,
                encodedChunkId: encodedChunk
            )
        )
        return try decode(PipelineMediaChunk.self, from: data)
    }

    func fetchLibraryMedia(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: ApplePipelineMediaRuntimeContract.libraryMediaPath(encoded))
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobMediaData(jobId: String) async throws -> Data {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequest(path: ApplePipelineMediaRuntimeContract.jobMediaPath(encoded))
    }

    func fetchLibraryMediaData(jobId: String) async throws -> Data {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequest(path: ApplePipelineMediaRuntimeContract.libraryMediaPath(encoded))
    }

    func fetchJobTimingData(jobId: String) async throws -> Data? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequestAllowingNotFound(path: ApplePipelineMediaRuntimeContract.jobTimingPath(encoded))
    }

    func fetchJobTiming(jobId: String) async throws -> JobTimingResponse? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        guard let data = try await sendRequestAllowingNotFound(
            path: ApplePipelineMediaRuntimeContract.jobTimingPath(encoded)
        ) else {
            return nil
        }
        return try decode(JobTimingResponse.self, from: data)
    }

    func fetchSubtitleTvMetadata(jobId: String) async throws -> SubtitleTvMetadataResponse? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        guard let data = try await sendRequestAllowingNotFound(
            path: ApplePipelineMediaRuntimeContract.subtitleTvMetadataPath(encoded)
        ) else {
            return nil
        }
        return try decode(SubtitleTvMetadataResponse.self, from: data)
    }

    func fetchYoutubeVideoMetadata(jobId: String) async throws -> YoutubeVideoMetadataResponse? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        guard let data = try await sendRequestAllowingNotFound(
            path: ApplePipelineMediaRuntimeContract.youtubeVideoMetadataPath(encoded)
        ) else {
            return nil
        }
        return try decode(YoutubeVideoMetadataResponse.self, from: data)
    }
}
