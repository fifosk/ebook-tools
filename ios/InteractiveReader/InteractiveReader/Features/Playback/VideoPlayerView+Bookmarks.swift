import Foundation

extension VideoPlayerView {
    func refreshBookmarks() {
        guard let jobId = resolvedBookmarkJobId else {
            bookmarks = []
            return
        }
        bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: resolvedBookmarkUserId)
        guard let configuration = appState.configuration else { return }
        Task {
            await syncRemoteBookmarks(jobId: jobId, configuration: configuration)
        }
    }

    func syncRemoteBookmarks(jobId: String, configuration: APIClientConfiguration) async {
        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchPlaybackBookmarks(jobId: jobId)
            let entries = response.bookmarks.map { payload in
                PlaybackBookmarkEntry(
                    id: payload.id,
                    jobId: payload.jobId,
                    itemType: payload.itemType ?? resolvedBookmarkItemType,
                    kind: payload.kind,
                    createdAt: payload.createdAt,
                    label: payload.label,
                    playbackTime: payload.position,
                    sentenceNumber: payload.sentence,
                    chunkId: payload.chunkId,
                    segmentId: payload.segmentId
                )
            }
            PlaybackBookmarkStore.shared.replaceBookmarks(entries, jobId: jobId, userId: resolvedBookmarkUserId)
        } catch {
            return
        }
    }

    func addBookmark() {
        guard let jobId = resolvedBookmarkJobId else { return }
        let time = (isScrubbing ? scrubberValue : coordinator.currentTime)
        let clamped = max(0, time.isFinite ? time : 0)
        let segmentLabel = segmentOptions.first(where: { $0.id == selectedSegmentID })?.label
        var labelParts: [String] = []
        if let segmentLabel, segmentOptions.count > 1 {
            labelParts.append(segmentLabel)
        }
        labelParts.append(formatBookmarkTime(clamped))
        let label = labelParts.joined(separator: " · ")
        let entry = PlaybackBookmarkEntry(
            id: UUID().uuidString,
            jobId: jobId,
            itemType: resolvedBookmarkItemType,
            kind: .time,
            createdAt: Date().timeIntervalSince1970,
            label: label.isEmpty ? "Bookmark" : label,
            playbackTime: clamped,
            sentenceNumber: nil,
            chunkId: nil,
            segmentId: selectedSegmentID
        )
        guard let configuration = appState.configuration else {
            PlaybackBookmarkStore.shared.addBookmark(entry, userId: resolvedBookmarkUserId)
            return
        }
        Task {
            let client = APIClient(configuration: configuration)
            let payload = PlaybackBookmarkCreateRequest(
                id: entry.id,
                label: entry.label,
                kind: entry.kind,
                createdAt: entry.createdAt,
                position: entry.playbackTime,
                sentence: entry.sentenceNumber,
                mediaType: "video",
                mediaId: nil,
                baseId: nil,
                segmentId: entry.segmentId,
                chunkId: entry.chunkId,
                itemType: entry.itemType
            )
            do {
                let response = try await client.createPlaybackBookmark(jobId: jobId, payload: payload)
                let stored = PlaybackBookmarkEntry(
                    id: response.id,
                    jobId: response.jobId,
                    itemType: response.itemType ?? entry.itemType,
                    kind: response.kind,
                    createdAt: response.createdAt,
                    label: response.label,
                    playbackTime: response.position,
                    sentenceNumber: response.sentence,
                    chunkId: response.chunkId,
                    segmentId: response.segmentId
                )
                PlaybackBookmarkStore.shared.addBookmark(stored, userId: resolvedBookmarkUserId)
            } catch {
                PlaybackBookmarkStore.shared.addBookmark(entry, userId: resolvedBookmarkUserId)
            }
        }
    }

    func jumpToBookmark(_ bookmark: PlaybackBookmarkEntry) {
        guard let time = bookmark.playbackTime else { return }
        let shouldPlay = coordinator.isPlaying
        if let segmentId = bookmark.segmentId, segmentId != selectedSegmentID {
            guard let onSelectSegment else {
                applyBookmarkSeek(time: time, shouldPlay: shouldPlay)
                return
            }
            pendingBookmarkSeek = PendingVideoBookmarkSeek(
                time: time,
                shouldPlay: shouldPlay,
                segmentId: segmentId
            )
            onSelectSegment(segmentId)
            return
        }
        applyBookmarkSeek(time: time, shouldPlay: shouldPlay)
    }

    func removeBookmark(_ bookmark: PlaybackBookmarkEntry) {
        guard let jobId = resolvedBookmarkJobId else { return }
        guard let configuration = appState.configuration else {
            PlaybackBookmarkStore.shared.removeBookmark(
                id: bookmark.id,
                jobId: jobId,
                userId: resolvedBookmarkUserId
            )
            return
        }
        Task {
            let client = APIClient(configuration: configuration)
            do {
                let response = try await client.deletePlaybackBookmark(jobId: jobId, bookmarkId: bookmark.id)
                if response.deleted {
                    PlaybackBookmarkStore.shared.removeBookmark(
                        id: bookmark.id,
                        jobId: jobId,
                        userId: resolvedBookmarkUserId
                    )
                }
            } catch {
                return
            }
        }
    }

    func formatBookmarkTime(_ seconds: Double) -> String {
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
}
