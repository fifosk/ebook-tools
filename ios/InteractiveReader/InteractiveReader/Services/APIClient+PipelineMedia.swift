import Foundation

extension APIClient {
    func fetchJobMedia(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: "/api/pipelines/jobs/\(encoded)/media")
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobMediaLive(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: "/api/pipelines/jobs/\(encoded)/media/live")
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobMediaLiveData(jobId: String) async throws -> Data {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequest(path: "/api/pipelines/jobs/\(encoded)/media/live")
    }

    func fetchJobMediaChunk(jobId: String, chunkId: String) async throws -> PipelineMediaChunk {
        let encodedJob = AppleAPIPathComponentEncoding.encode(jobId)
        let encodedChunk = AppleAPIPathComponentEncoding.encode(chunkId)
        let data = try await sendRequest(path: "/api/pipelines/jobs/\(encodedJob)/media/chunks/\(encodedChunk)")
        return try decode(PipelineMediaChunk.self, from: data)
    }

    func fetchLibraryMedia(jobId: String) async throws -> PipelineMediaResponse {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        let data = try await sendRequest(path: "/api/library/media/\(encoded)")
        return try decode(PipelineMediaResponse.self, from: data)
    }

    func fetchJobMediaData(jobId: String) async throws -> Data {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequest(path: "/api/pipelines/jobs/\(encoded)/media")
    }

    func fetchLibraryMediaData(jobId: String) async throws -> Data {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequest(path: "/api/library/media/\(encoded)")
    }

    func fetchJobTimingData(jobId: String) async throws -> Data? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        return try await sendRequestAllowingNotFound(path: "/api/jobs/\(encoded)/timing")
    }

    func fetchJobTiming(jobId: String) async throws -> JobTimingResponse? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        guard let data = try await sendRequestAllowingNotFound(path: "/api/jobs/\(encoded)/timing") else {
            return nil
        }
        return try decode(JobTimingResponse.self, from: data)
    }

    func fetchSubtitleTvMetadata(jobId: String) async throws -> SubtitleTvMetadataResponse? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        guard let data = try await sendRequestAllowingNotFound(path: "/api/subtitles/jobs/\(encoded)/metadata/tv") else {
            return nil
        }
        return try decode(SubtitleTvMetadataResponse.self, from: data)
    }

    func fetchYoutubeVideoMetadata(jobId: String) async throws -> YoutubeVideoMetadataResponse? {
        let encoded = AppleAPIPathComponentEncoding.encode(jobId)
        guard let data = try await sendRequestAllowingNotFound(path: "/api/subtitles/jobs/\(encoded)/metadata/youtube") else {
            return nil
        }
        return try decode(YoutubeVideoMetadataResponse.self, from: data)
    }
}
