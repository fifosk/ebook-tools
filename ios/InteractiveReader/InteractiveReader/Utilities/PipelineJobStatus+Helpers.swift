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
        if status.isFinished {
            return true
        }
        if mediaCompleted == true || completedAt?.nonEmptyValue != nil {
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
}
