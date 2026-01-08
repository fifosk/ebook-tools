import Foundation

struct JobVideoSegment: Identifiable {
    let id: String
    let videoFile: PipelineMediaFile
    let subtitleFiles: [PipelineMediaFile]
    let chunk: PipelineMediaChunk?
}

struct VideoResumeTarget {
    let segmentID: String
    let localTime: Double
}
