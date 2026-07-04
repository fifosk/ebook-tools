import Foundation

struct PipelineMediaResponse: Decodable {
    let media: [String: [PipelineMediaFile]]
    let chunks: [PipelineMediaChunk]
    let complete: Bool
    let diagnostics: PipelineMediaDiagnostics

    enum CodingKeys: String, CodingKey {
        case media
        case chunks
        case complete
        case diagnostics
    }

    init(
        media: [String: [PipelineMediaFile]] = [:],
        chunks: [PipelineMediaChunk] = [],
        complete: Bool = false,
        diagnostics: PipelineMediaDiagnostics = .empty
    ) {
        self.media = media
        self.chunks = chunks
        self.complete = complete
        self.diagnostics = diagnostics
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        media = try container.decode([String: [PipelineMediaFile]].self, forKey: .media)
        chunks = try container.decode([PipelineMediaChunk].self, forKey: .chunks)
        complete = try container.decode(Bool.self, forKey: .complete)
        diagnostics = try container.decode(PipelineMediaDiagnostics.self, forKey: .diagnostics)
    }
}

struct PipelineMediaDiagnostics: Decodable, Equatable {
    let mediaFileCount: Int
    let chunkCount: Int
    let chunkFileCount: Int
    let audioFileCount: Int
    let imageFileCount: Int
    let chunksWithAudio: Int
    let chunksWithTiming: Int
    let chunksWithImages: Int
    let chunksWithoutFiles: Int
    let chunksWithoutMetadata: Int
    let filesWithoutUrl: Int
    let filesWithoutSize: Int
    let gapCount: Int

    var missingCount: Int {
        gapCount
    }

    var hasGaps: Bool {
        gapCount > 0
    }

    enum CodingKeys: String, CodingKey {
        case mediaFileCount
        case chunkCount
        case chunkFileCount
        case audioFileCount
        case imageFileCount
        case chunksWithAudio
        case chunksWithTiming
        case chunksWithImages
        case chunksWithoutFiles
        case chunksWithoutMetadata
        case filesWithoutUrl
        case filesWithoutSize
        case gapCount
    }

    init(
        mediaFileCount: Int,
        chunkCount: Int,
        chunkFileCount: Int,
        audioFileCount: Int,
        imageFileCount: Int,
        chunksWithAudio: Int,
        chunksWithTiming: Int,
        chunksWithImages: Int,
        chunksWithoutFiles: Int,
        chunksWithoutMetadata: Int,
        filesWithoutUrl: Int,
        filesWithoutSize: Int,
        gapCount: Int? = nil
    ) {
        self.mediaFileCount = mediaFileCount
        self.chunkCount = chunkCount
        self.chunkFileCount = chunkFileCount
        self.audioFileCount = audioFileCount
        self.imageFileCount = imageFileCount
        self.chunksWithAudio = chunksWithAudio
        self.chunksWithTiming = chunksWithTiming
        self.chunksWithImages = chunksWithImages
        self.chunksWithoutFiles = chunksWithoutFiles
        self.chunksWithoutMetadata = chunksWithoutMetadata
        self.filesWithoutUrl = filesWithoutUrl
        self.filesWithoutSize = filesWithoutSize
        self.gapCount = gapCount ?? PipelineMediaDiagnostics.derivedGapCount(
            chunksWithoutFiles: chunksWithoutFiles,
            chunksWithoutMetadata: chunksWithoutMetadata,
            filesWithoutUrl: filesWithoutUrl,
            filesWithoutSize: filesWithoutSize
        )
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let chunksWithoutFiles = try container.decode(Int.self, forKey: .chunksWithoutFiles)
        let chunksWithoutMetadata = try container.decode(Int.self, forKey: .chunksWithoutMetadata)
        let filesWithoutUrl = try container.decode(Int.self, forKey: .filesWithoutUrl)
        let filesWithoutSize = try container.decode(Int.self, forKey: .filesWithoutSize)
        self.init(
            mediaFileCount: try container.decode(Int.self, forKey: .mediaFileCount),
            chunkCount: try container.decode(Int.self, forKey: .chunkCount),
            chunkFileCount: try container.decode(Int.self, forKey: .chunkFileCount),
            audioFileCount: try container.decode(Int.self, forKey: .audioFileCount),
            imageFileCount: try container.decode(Int.self, forKey: .imageFileCount),
            chunksWithAudio: try container.decode(Int.self, forKey: .chunksWithAudio),
            chunksWithTiming: try container.decode(Int.self, forKey: .chunksWithTiming),
            chunksWithImages: try container.decode(Int.self, forKey: .chunksWithImages),
            chunksWithoutFiles: chunksWithoutFiles,
            chunksWithoutMetadata: chunksWithoutMetadata,
            filesWithoutUrl: filesWithoutUrl,
            filesWithoutSize: filesWithoutSize,
            gapCount: try container.decodeIfPresent(Int.self, forKey: .gapCount)
        )
    }

    private static func derivedGapCount(
        chunksWithoutFiles: Int,
        chunksWithoutMetadata: Int,
        filesWithoutUrl: Int,
        filesWithoutSize: Int
    ) -> Int {
        chunksWithoutFiles + chunksWithoutMetadata + filesWithoutUrl + filesWithoutSize
    }

    static let empty = PipelineMediaDiagnostics(
        mediaFileCount: 0,
        chunkCount: 0,
        chunkFileCount: 0,
        audioFileCount: 0,
        imageFileCount: 0,
        chunksWithAudio: 0,
        chunksWithTiming: 0,
        chunksWithImages: 0,
        chunksWithoutFiles: 0,
        chunksWithoutMetadata: 0,
        filesWithoutUrl: 0,
        filesWithoutSize: 0,
        gapCount: 0
    )
}

struct PipelineMediaFile: Decodable, Identifiable {
    let id = UUID()
    let name: String
    let url: String?
    let size: Double?
    let updatedAt: Date?
    let source: String
    let relativePath: String?
    let path: String?
    let chunkID: String?
    let rangeFragment: String?
    let startSentence: Int?
    let endSentence: Int?
    let type: String?

    // Note: Using convertFromSnakeCase decoder strategy, so CodingKeys should use
    // camelCase raw values. The decoder converts JSON snake_case to camelCase automatically.
    enum CodingKeys: String, CodingKey {
        case name
        case url
        case size
        case updatedAt
        case source
        case relativePath
        case path
        case chunkID = "chunkId"  // Swift property is chunkID but JSON has chunk_id -> chunkId
        case rangeFragment
        case startSentence
        case endSentence
        case type
    }

    init(
        name: String,
        url: String?,
        size: Double?,
        updatedAt: Date?,
        source: String,
        relativePath: String?,
        path: String?,
        chunkID: String?,
        rangeFragment: String?,
        startSentence: Int?,
        endSentence: Int?,
        type: String?
    ) {
        self.name = name
        self.url = url
        self.size = size
        self.updatedAt = updatedAt
        self.source = source
        self.relativePath = relativePath
        self.path = path
        self.chunkID = chunkID
        self.rangeFragment = rangeFragment
        self.startSentence = startSentence
        self.endSentence = endSentence
        self.type = type
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        name = try container.decode(String.self, forKey: .name)
        url = try? container.decode(String.self, forKey: .url)
        if let sizeValue = try? container.decode(Double.self, forKey: .size) {
            size = sizeValue
        } else if let sizeValue = try? container.decode(Int.self, forKey: .size) {
            size = Double(sizeValue)
        } else {
            size = nil
        }
        if let dateValue = try? container.decode(Date.self, forKey: .updatedAt) {
            updatedAt = dateValue
        } else if let dateString = try? container.decode(String.self, forKey: .updatedAt) {
            updatedAt = ISO8601DateFormatter.withFractionalSeconds.date(from: dateString)
        } else {
            updatedAt = nil
        }
        source = try container.decode(String.self, forKey: .source)
        relativePath = try? container.decode(String.self, forKey: .relativePath)
        path = try? container.decode(String.self, forKey: .path)
        chunkID = try? container.decode(String.self, forKey: .chunkID)
        rangeFragment = try? container.decode(String.self, forKey: .rangeFragment)
        startSentence = try? container.decode(Int.self, forKey: .startSentence)
        endSentence = try? container.decode(Int.self, forKey: .endSentence)
        type = try? container.decode(String.self, forKey: .type)
    }
}

struct PipelineMediaChunk: Decodable, Identifiable {
    var id: String { chunkID ?? UUID().uuidString }
    let chunkID: String?
    let rangeFragment: String?
    let startSentence: Int?
    let endSentence: Int?
    let files: [PipelineMediaFile]
    let sentences: [ChunkSentenceMetadata]
    let metadataPath: String?
    let metadataURL: String?
    let sentenceCount: Int?
    let audioTracks: [String: AudioTrackMetadata]
    let timingTracks: [String: [[String: JSONValue]]]?
    /// Timing version - "2" means pre-scaled timing from backend (no client-side scaling needed)
    let timingVersion: String?

    enum CodingKeys: String, CodingKey {
        case chunkID = "chunkId"
        case rangeFragment
        case startSentence
        case endSentence
        case files
        case sentences
        case metadataPath
        case metadataURL = "metadataUrl"
        case sentenceCount
        case audioTracks
        case timingTracks
        case timingVersion
    }

    init(
        chunkID: String?,
        rangeFragment: String?,
        startSentence: Int?,
        endSentence: Int?,
        files: [PipelineMediaFile],
        sentences: [ChunkSentenceMetadata],
        metadataPath: String?,
        metadataURL: String?,
        sentenceCount: Int?,
        audioTracks: [String: AudioTrackMetadata],
        timingTracks: [String: [[String: JSONValue]]]? = nil,
        timingVersion: String? = nil
    ) {
        self.chunkID = chunkID
        self.rangeFragment = rangeFragment
        self.startSentence = startSentence
        self.endSentence = endSentence
        self.files = files
        self.sentences = sentences
        self.metadataPath = metadataPath
        self.metadataURL = metadataURL
        self.sentenceCount = sentenceCount
        self.audioTracks = audioTracks
        self.timingTracks = timingTracks
        self.timingVersion = timingVersion
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        chunkID = try? container.decode(String.self, forKey: .chunkID)
        rangeFragment = try? container.decode(String.self, forKey: .rangeFragment)
        startSentence = try? container.decode(Int.self, forKey: .startSentence)
        endSentence = try? container.decode(Int.self, forKey: .endSentence)
        files = try container.decode([PipelineMediaFile].self, forKey: .files)
        sentences = try container.decode([ChunkSentenceMetadata].self, forKey: .sentences)
        metadataPath = try? container.decode(String.self, forKey: .metadataPath)
        metadataURL = try? container.decode(String.self, forKey: .metadataURL)
        sentenceCount = try? container.decode(Int.self, forKey: .sentenceCount)
        audioTracks = try container.decode([String: AudioTrackMetadata].self, forKey: .audioTracks)
        timingTracks = try? container.decode([String: [[String: JSONValue]]].self, forKey: .timingTracks)
        timingVersion = try? container.decode(String.self, forKey: .timingVersion)
    }
}

struct AudioTrackMetadata: Decodable {
    let path: String?
    let url: String?
    let duration: Double?
    let sampleRate: Int?

    enum CodingKeys: String, CodingKey {
        case path
        case url
        case duration
        case sampleRate = "sampleRate"
    }
}

private extension ISO8601DateFormatter {
    static let withFractionalSeconds: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
