import SwiftUI

extension JobsView {
    #if os(tvOS)
    @ViewBuilder
    func offlineContextMenu(for job: PipelineStatusResponse) -> some View {
        let status = offlineStore.status(for: job.jobId, kind: .job)
        let isEligible = job.isFinishedForDisplay

        if status.isSynced {
            Button(role: .destructive, action: { handleRemoveOfflineCopyMenuTap(job) }) {
                Label("Remove Offline Copy", systemImage: "trash.circle")
            }
        } else if status.isSyncing {
            Button(action: handleOfflineStatusTap) {
                Label("Downloading...", systemImage: "arrow.down.circle")
            }
            .disabled(true)
        } else if isEligible {
            Button(action: { handleDownloadWithLookupCacheMenuTap(job) }) {
                Label("Download with Dictionary", systemImage: "arrow.down.circle")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
            Button(action: { handleDownloadWithoutLookupCacheMenuTap(job) }) {
                Label("Download without Dictionary", systemImage: "arrow.down.circle.dotted")
            }
            .disabled(!offlineStore.isAvailable || appState.configuration == nil)
        }
    }

    private func handleOfflineStatusTap() {}

    private func handleRemoveOfflineCopyMenuTap(_ job: PipelineStatusResponse) {
        handleRemoveOfflineCopy(job)
    }

    private func handleDownloadWithLookupCacheMenuTap(_ job: PipelineStatusResponse) {
        handleDownloadOfflineCopy(job, includeLookupCache: true)
    }

    private func handleDownloadWithoutLookupCacheMenuTap(_ job: PipelineStatusResponse) {
        handleDownloadOfflineCopy(job, includeLookupCache: false)
    }

    private func handleRemoveOfflineCopy(_ job: PipelineStatusResponse) {
        offlineStore.remove(jobId: job.jobId, kind: .job)
    }

    private func handleDownloadOfflineCopy(_ job: PipelineStatusResponse, includeLookupCache: Bool) {
        guard let configuration = appState.configuration else { return }
        offlineStore.sync(
            jobId: job.jobId,
            kind: .job,
            configuration: configuration,
            includeLookupCache: includeLookupCache
        )
    }
    #else
    @ViewBuilder
    func offlineContextMenu(for job: PipelineStatusResponse) -> some View {
        EmptyView()
    }
    #endif
}
