import Foundation

extension PipelineJobStatus {
    var isActive: Bool {
        switch self {
        case .pending, .running, .pausing, .paused:
            return true
        case .completed, .failed, .cancelled:
            return false
        }
    }

    var isFinished: Bool {
        !isActive
    }
}

extension PipelineStatusResponse {
    var isFinishedForDisplay: Bool {
        if status.isActive {
            return false
        }
        if status.isFinished {
            return true
        }
        if mediaCompleted == true || completedAt?.nonEmptyValue != nil {
            return true
        }
        if hasGeneratedMedia {
            return true
        }
        if let snapshot = latestEvent?.snapshot,
           let total = snapshot.total,
           total > 0,
           snapshot.completed >= total {
            return true
        }
        return false
    }

    var isActiveForDisplay: Bool {
        !isFinishedForDisplay
    }

    var displayStatus: PipelineJobStatus {
        if status.isFinished {
            return status
        }
        if isFinishedForDisplay {
            return .completed
        }
        return status
    }

    private var hasGeneratedMedia: Bool {
        guard let generatedFiles else { return false }
        return hasGeneratedMedia(in: generatedFiles)
    }

    private func hasGeneratedMedia(in payload: [String: JSONValue]) -> Bool {
        if case let .array(files) = payload["files"], files.contains(where: { $0.isObject }) {
            return true
        }
        if case let .array(chunks) = payload["chunks"] {
            for chunk in chunks {
                if case let .object(chunkObject) = chunk,
                   case let .array(chunkFiles) = chunkObject["files"],
                   chunkFiles.contains(where: { $0.isObject }) {
                    return true
                }
            }
        }
        return false
    }
}

private extension JSONValue {
    var isObject: Bool {
        if case .object = self {
            return true
        }
        return false
    }
}
