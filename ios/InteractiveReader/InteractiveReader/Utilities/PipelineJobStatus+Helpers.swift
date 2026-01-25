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

    struct ReadyProgressSnapshot: Hashable {
        let completed: Int
        let total: Int?
    }

    var readyProgressSnapshot: ReadyProgressSnapshot? {
        if let snapshot = mediaBatchProgressSnapshot {
            return snapshot
        }
        guard let event = latestEvent else { return nil }
        guard event.isReadyStage else { return nil }
        return ReadyProgressSnapshot(
            completed: event.snapshot.completed,
            total: event.snapshot.total
        )
    }

    private var mediaBatchProgressSnapshot: ReadyProgressSnapshot? {
        guard let generatedFiles,
              let stats = generatedFiles["media_batch_stats"]?.objectValue
        else {
            return nil
        }
        guard let completed = stats["items_completed"]?.intValue else { return nil }
        let total = stats["items_total"]?.intValue
        return ReadyProgressSnapshot(completed: completed, total: total)
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

private extension ProgressEventPayload {
    var progressStage: String? {
        if let stage = metadata["stage"]?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines),
           !stage.isEmpty {
            return stage.lowercased()
        }
        if eventType == "complete" {
            return "media"
        }
        return nil
    }

    var isReadyStage: Bool {
        guard let stage = progressStage else { return true }
        return stage == "media" || stage == "playable"
    }
}
