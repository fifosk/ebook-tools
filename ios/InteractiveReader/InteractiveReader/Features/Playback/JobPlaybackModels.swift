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

enum InteractiveAutoplayRetrySchedule {
    static let nanosecondDelays: [UInt64] = [
        350_000_000,
        900_000_000,
        1_600_000_000,
        2_500_000_000,
        4_000_000_000,
        6_000_000_000,
        8_000_000_000,
        10_000_000_000,
        12_000_000_000,
        15_000_000_000
    ]
}
