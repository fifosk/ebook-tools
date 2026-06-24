import Foundation

enum AppleCreateRuntimeContract {
    static let bookOptionsPath = "/api/books/options"
    static let bookJobsPath = "/api/books/jobs"
    static let pipelineFilesPath = "/api/pipelines/files"
    static let pipelineContentIndexPath = "/api/pipelines/files/content-index"
    static let pipelineUploadPath = "/api/pipelines/files/upload"
    static let pipelineJobsPath = "/api/pipelines"
    static let pipelineIntakeStatusPath = "/api/pipelines/intake/status"
    static let subtitleSourcesPath = "/api/subtitles/sources"
    static let subtitleDeleteSourcePath = "/api/subtitles/delete-source"
    static let subtitleModelsPath = "/api/subtitles/models"
    static let subtitleJobsPath = "/api/subtitles/jobs"
    static let youtubeLibraryPath = "/api/subtitles/youtube/library"
    static let youtubeSubtitleStreamsPath = "/api/subtitles/youtube/subtitle-streams"
    static let youtubeExtractSubtitlesPath = "/api/subtitles/youtube/extract-subtitles"
    static let subtitleTvMetadataPreviewPath = "/api/subtitles/metadata/tv/lookup"
    static let subtitleTvMetadataCacheClearPath = "/api/subtitles/metadata/tv/cache/clear"
    static let youtubeMetadataPreviewPath = "/api/subtitles/metadata/youtube/lookup"
    static let youtubeMetadataCacheClearPath = "/api/subtitles/metadata/youtube/cache/clear"
    static let youtubeDubPath = "/api/subtitles/youtube/dub"
    static let templateListPath = "/api/creation/templates"
    static let templatePathTemplate = "/api/creation/templates/{template_id}"

    static func templatePath(_ encodedTemplateId: String) -> String {
        "\(templateListPath)/\(encodedTemplateId)"
    }
}

extension APIClient {
    func fetchBookCreationOptions() async throws -> BookCreationOptionsResponse {
        let data = try await sendRequest(path: AppleCreateRuntimeContract.bookOptionsPath)
        return try decode(BookCreationOptionsResponse.self, from: data)
    }

    func fetchPipelineIntakeStatus() async throws -> PipelineIntakeStatusResponse {
        let data = try await sendRequest(path: AppleCreateRuntimeContract.pipelineIntakeStatusPath)
        return try decode(PipelineIntakeStatusResponse.self, from: data)
    }

    func fetchCreationTemplates(mode: String? = nil) async throws -> CreationTemplateListResponse {
        var path = AppleCreateRuntimeContract.templateListPath
        if let mode = mode?.trimmingCharacters(in: .whitespacesAndNewlines), !mode.isEmpty {
            var components = URLComponents()
            components.queryItems = [URLQueryItem(name: "mode", value: mode)]
            if let query = components.percentEncodedQuery, !query.isEmpty {
                path += "?\(query)"
            }
        }
        let data = try await sendRequest(path: path)
        return try decode(CreationTemplateListResponse.self, from: data)
    }

    func deleteCreationTemplate(templateId: String) async throws {
        let trimmed = templateId.trimmingCharacters(in: .whitespacesAndNewlines)
        let encoded = trimmed.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? trimmed
        _ = try await sendRequest(
            path: AppleCreateRuntimeContract.templatePath(encoded),
            method: "DELETE"
        )
    }

    func fetchPipelineFiles() async throws -> PipelineFileBrowserResponse {
        let data = try await sendRequest(path: AppleCreateRuntimeContract.pipelineFilesPath)
        return try decode(PipelineFileBrowserResponse.self, from: data)
    }

    func deletePipelineEbook(path: String) async throws {
        _ = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.pipelineFilesPath,
            method: "DELETE",
            payload: PipelineFileDeleteRequest(path: path)
        )
    }

    func fetchSubtitleLlmModels() async throws -> LLMModelListResponse {
        let data = try await sendRequest(path: AppleCreateRuntimeContract.subtitleModelsPath)
        return try decode(LLMModelListResponse.self, from: data)
    }

    func fetchBookContentIndex(inputFile: String) async throws -> BookContentIndexResponse {
        let trimmed = inputFile.trimmingCharacters(in: .whitespacesAndNewlines)
        var components = URLComponents()
        components.queryItems = [URLQueryItem(name: "input_file", value: trimmed)]
        let query = components.percentEncodedQuery ?? ""
        let data = try await sendRequest(path: "\(AppleCreateRuntimeContract.pipelineContentIndexPath)?\(query)")
        return try decode(BookContentIndexResponse.self, from: data)
    }

    func fetchSubtitleSources(directory: String? = nil) async throws -> SubtitleSourceListResponse {
        var path = AppleCreateRuntimeContract.subtitleSourcesPath
        if let directory = directory?.trimmingCharacters(in: .whitespacesAndNewlines), !directory.isEmpty {
            var components = URLComponents()
            components.queryItems = [URLQueryItem(name: "directory", value: directory)]
            if let query = components.percentEncodedQuery, !query.isEmpty {
                path += "?\(query)"
            }
        }
        let data = try await sendRequest(path: path)
        return try decode(SubtitleSourceListResponse.self, from: data)
    }

    func deleteSubtitleSource(
        subtitlePath: String,
        baseDir: String? = nil
    ) async throws -> SubtitleSourceDeleteResponse {
        let payload = SubtitleSourceDeleteRequest(
            subtitlePath: subtitlePath,
            baseDir: baseDir?.nonEmptyValue
        )
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.subtitleDeleteSourcePath,
            method: "POST",
            payload: payload
        )
        return try decode(SubtitleSourceDeleteResponse.self, from: data)
    }

    func fetchYoutubeLibrary(baseDir: String? = nil) async throws -> YoutubeNasLibraryResponse {
        var path = AppleCreateRuntimeContract.youtubeLibraryPath
        if let baseDir = baseDir?.trimmingCharacters(in: .whitespacesAndNewlines), !baseDir.isEmpty {
            var components = URLComponents()
            components.queryItems = [URLQueryItem(name: "base_dir", value: baseDir)]
            if let query = components.percentEncodedQuery, !query.isEmpty {
                path += "?\(query)"
            }
        }
        let data = try await sendRequest(path: path)
        return try decode(YoutubeNasLibraryResponse.self, from: data)
    }

    func fetchYoutubeSubtitleStreams(videoPath: String) async throws -> YoutubeInlineSubtitleListResponse {
        let trimmed = videoPath.trimmingCharacters(in: .whitespacesAndNewlines)
        var components = URLComponents()
        components.queryItems = [URLQueryItem(name: "video_path", value: trimmed)]
        let query = components.percentEncodedQuery ?? ""
        let data = try await sendRequest(path: "\(AppleCreateRuntimeContract.youtubeSubtitleStreamsPath)?\(query)")
        return try decode(YoutubeInlineSubtitleListResponse.self, from: data)
    }

    func extractYoutubeSubtitles(_ payload: YoutubeSubtitleExtractionRequestPayload) async throws -> YoutubeSubtitleExtractionResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.youtubeExtractSubtitlesPath,
            method: "POST",
            payload: payload
        )
        return try decode(YoutubeSubtitleExtractionResponse.self, from: data)
    }

    func lookupSubtitleTvMetadataPreview(
        _ payload: SubtitleTvMetadataPreviewLookupRequest
    ) async throws -> SubtitleTvMetadataPreviewResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.subtitleTvMetadataPreviewPath,
            method: "POST",
            payload: payload
        )
        return try decode(SubtitleTvMetadataPreviewResponse.self, from: data)
    }

    func lookupYoutubeMetadataPreview(
        _ payload: YoutubeVideoMetadataPreviewLookupRequest
    ) async throws -> YoutubeVideoMetadataPreviewResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.youtubeMetadataPreviewPath,
            method: "POST",
            payload: payload
        )
        return try decode(YoutubeVideoMetadataPreviewResponse.self, from: data)
    }

    func clearSubtitleTvMetadataCache(query: String) async throws -> MetadataCacheClearResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.subtitleTvMetadataCacheClearPath,
            method: "POST",
            payload: MetadataCacheClearRequest(query: query)
        )
        return try decode(MetadataCacheClearResponse.self, from: data)
    }

    func clearYoutubeMetadataCache(query: String) async throws -> MetadataCacheClearResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.youtubeMetadataCacheClearPath,
            method: "POST",
            payload: MetadataCacheClearRequest(query: query)
        )
        return try decode(MetadataCacheClearResponse.self, from: data)
    }

    func submitPipeline(_ payload: PipelineRequestPayload) async throws -> PipelineSubmissionResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.pipelineJobsPath,
            method: "POST",
            payload: payload
        )
        return try decode(PipelineSubmissionResponse.self, from: data)
    }

    func submitBookGenerationJob(_ payload: BookGenerationJobSubmission) async throws -> PipelineSubmissionResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.bookJobsPath,
            method: "POST",
            payload: payload
        )
        return try decode(PipelineSubmissionResponse.self, from: data)
    }

    func submitYoutubeDub(_ payload: YoutubeDubRequestPayload) async throws -> PipelineSubmissionResponse {
        let data = try await sendJSONRequest(
            path: AppleCreateRuntimeContract.youtubeDubPath,
            method: "POST",
            payload: payload
        )
        return try decode(PipelineSubmissionResponse.self, from: data)
    }

    func uploadPipelineEbook(fileURL: URL, filename: String? = nil) async throws -> PipelineFileEntry {
        let didAccessSecurityScope = fileURL.startAccessingSecurityScopedResource()
        defer {
            if didAccessSecurityScope {
                fileURL.stopAccessingSecurityScopedResource()
            }
        }
        let upload = try MultipartUploadFile(
            fieldName: "file",
            fileURL: fileURL,
            filename: filename,
            contentType: "application/epub+zip"
        )
        let multipart = MultipartFormDataBuilder.makeBody(fields: [:], file: upload)
        let data = try await sendRequest(
            path: AppleCreateRuntimeContract.pipelineUploadPath,
            method: "POST",
            body: multipart.body,
            contentType: multipart.contentType
        )
        return try decode(PipelineFileEntry.self, from: data)
    }

    func submitSubtitleJob(
        _ payload: SubtitleJobFormPayload,
        fileURL: URL? = nil,
        filename: String? = nil
    ) async throws -> PipelineSubmissionResponse {
        let upload: MultipartUploadFile?
        if let fileURL {
            let didAccessSecurityScope = fileURL.startAccessingSecurityScopedResource()
            defer {
                if didAccessSecurityScope {
                    fileURL.stopAccessingSecurityScopedResource()
                }
            }
            upload = try MultipartUploadFile(
                fieldName: "file",
                fileURL: fileURL,
                filename: filename,
                contentType: "application/octet-stream"
            )
        } else {
            upload = nil
        }

        let multipart = MultipartFormDataBuilder.makeBody(fields: payload.multipartFields, file: upload)
        let data = try await sendRequest(
            path: AppleCreateRuntimeContract.subtitleJobsPath,
            method: "POST",
            body: multipart.body,
            contentType: multipart.contentType
        )
        return try decode(PipelineSubmissionResponse.self, from: data)
    }
}

struct MultipartUploadFile {
    let fieldName: String
    let filename: String
    let contentType: String
    let data: Data

    init(fieldName: String, fileURL: URL, filename: String?, contentType: String) throws {
        self.fieldName = fieldName
        self.filename = filename?.nonEmptyValue ?? fileURL.lastPathComponent
        self.contentType = contentType
        data = try Data(contentsOf: fileURL)
    }
}

enum MultipartFormDataBuilder {
    static func makeBody(fields: [String: String], file: MultipartUploadFile?) -> (body: Data, contentType: String) {
        let boundary = "ebook-tools-\(UUID().uuidString)"
        var body = Data()
        for key in fields.keys.sorted() {
            appendField(name: key, value: fields[key] ?? "", boundary: boundary, to: &body)
        }
        if let file {
            appendFile(file, boundary: boundary, to: &body)
        }
        body.appendString("--\(boundary)--\r\n")
        return (body, "multipart/form-data; boundary=\(boundary)")
    }

    private static func appendField(name: String, value: String, boundary: String, to body: inout Data) {
        body.appendString("--\(boundary)\r\n")
        body.appendString("Content-Disposition: form-data; name=\"\(escaped(name))\"\r\n\r\n")
        body.appendString("\(value)\r\n")
    }

    private static func appendFile(_ file: MultipartUploadFile, boundary: String, to body: inout Data) {
        body.appendString("--\(boundary)\r\n")
        body.appendString(
            "Content-Disposition: form-data; name=\"\(escaped(file.fieldName))\"; filename=\"\(escaped(file.filename))\"\r\n"
        )
        body.appendString("Content-Type: \(file.contentType)\r\n\r\n")
        body.append(file.data)
        body.appendString("\r\n")
    }

    private static func escaped(_ value: String) -> String {
        value
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
    }
}

private extension Data {
    mutating func appendString(_ string: String) {
        append(Data(string.utf8))
    }
}
