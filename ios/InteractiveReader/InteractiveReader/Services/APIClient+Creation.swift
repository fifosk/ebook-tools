import Foundation

extension APIClient {
    func fetchBookCreationOptions() async throws -> BookCreationOptionsResponse {
        let data = try await sendRequest(path: "/api/books/options")
        return try decode(BookCreationOptionsResponse.self, from: data)
    }

    func fetchSubtitleLlmModels() async throws -> LLMModelListResponse {
        let data = try await sendRequest(path: "/api/subtitles/models")
        return try decode(LLMModelListResponse.self, from: data)
    }

    func submitPipeline(_ payload: PipelineRequestPayload) async throws -> PipelineSubmissionResponse {
        let data = try await sendJSONRequest(path: "/api/pipelines", method: "POST", payload: payload)
        return try decode(PipelineSubmissionResponse.self, from: data)
    }

    func submitBookGenerationJob(_ payload: BookGenerationJobSubmission) async throws -> PipelineSubmissionResponse {
        let data = try await sendJSONRequest(path: "/api/books/jobs", method: "POST", payload: payload)
        return try decode(PipelineSubmissionResponse.self, from: data)
    }

    func submitYoutubeDub(_ payload: YoutubeDubRequestPayload) async throws -> PipelineSubmissionResponse {
        let data = try await sendJSONRequest(path: "/api/subtitles/youtube/dub", method: "POST", payload: payload)
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
            path: "/api/pipelines/files/upload",
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
            path: "/api/subtitles/jobs",
            method: "POST",
            body: multipart.body,
            contentType: multipart.contentType
        )
        return try decode(PipelineSubmissionResponse.self, from: data)
    }
}

private struct MultipartUploadFile {
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

private enum MultipartFormDataBuilder {
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
